#!/usr/bin/env python3
"""
Local Backfill Script — LTIA Radar
====================================
Crawl all active RSS/WEB sources from date_from to date_to, classify articles
with Gemini LLM, then write results directly into MongoDB (raw_data + processed_data).

Use this script to backfill historical data (e.g. from 2026-01-01 to today)
without relying on the Railway backend, which has a stricter resource budget.

Usage examples:
  # Backfill from Jan 1 2026 to today using env vars
  python scripts/local_backfill.py

  # Backfill with explicit dates and Atlas URI
  python scripts/local_backfill.py \\
    --date-from 2026-01-01 \\
    --date-to 2026-06-20 \\
    --mongodb-uri "mongodb+srv://..." \\
    --gemini-key "AIza..."

  # Dry-run (no DB writes)
  python scripts/local_backfill.py --dry-run

Requirements:
  Run from within the Docker backend container OR with all backend deps installed:
    docker compose exec backend python scripts/local_backfill.py ...

  OR set PYTHONPATH so that 'app.*' imports resolve:
    cd backend && PYTHONPATH=. python scripts/local_backfill.py ...
"""
from __future__ import annotations


import argparse
import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# ── Allow running from repo root or backend/ dir ──────────────────────────────
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)   # .../backend
sys.path.insert(0, _backend_dir)
# Also allow running from within the Docker container where /workspace = backend/
sys.path.insert(0, "/workspace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("local_backfill")

# Silence noisy sub-loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)


# ── Lazy imports (after sys.path is set) ──────────────────────────────────────

def _lazy_imports():
    """Import app modules after sys.path is configured."""
    global AsyncIOMotorClient, settings
    global RSSCrawler, HTMLCrawler, GeminiImplementation
    global RawData, ProcessedData, ArticleCitation
    global Source, SourceType
    global get_friendly_domain

    from motor.motor_asyncio import AsyncIOMotorClient
    from app.config import settings as _settings
    settings = _settings

    from app.infrastructure.crawler.rss_crawler import RSSCrawler
    from app.infrastructure.crawler.html_crawler import HTMLCrawler
    from app.infrastructure.llm.gemini import GeminiImplementation

    from app.domain.entities.raw_data import RawData
    from app.domain.entities.processed_data import ProcessedData, ArticleCitation
    from app.domain.entities.source import Source, SourceType
    from app.domain.utils.domain_mapper import get_friendly_domain


# ── Helper: rate limiter (copy from crawl_news.py) ───────────────────────────

class _RateLimiter:
    """Simple token-bucket rate limiter (per-minute window)."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._count = 0
        self._window_start = time.monotonic()

    def update_limit(self, limit: int) -> None:
        self._limit = max(1, limit)

    async def acquire(self) -> None:
        now = time.monotonic()
        elapsed = now - self._window_start

        if elapsed >= 60.0:
            self._count = 0
            self._window_start = now
            elapsed = 0.0

        if self._count >= self._limit:
            wait = 60.0 - elapsed
            logger.info(f"⏳ Rate limit ({self._limit} RPM) reached — sleeping {wait:.1f}s")
            await asyncio.sleep(wait)
            self._count = 0
            self._window_start = time.monotonic()

        self._count += 1


# ── Main backfill logic ───────────────────────────────────────────────────────

class LocalBackfill:
    def __init__(
        self,
        mongodb_uri: str,
        db_name: str,
        gemini_api_key: str | None,
        date_from: datetime,
        date_to: datetime,
        batch_size: int,
        dry_run: bool,
    ) -> None:
        self.mongodb_uri = mongodb_uri
        self.db_name = db_name
        self.gemini_api_key = gemini_api_key
        self.date_from = date_from
        self.date_to = date_to
        self.batch_size = batch_size
        self.dry_run = dry_run

        self.rss_crawler = RSSCrawler()
        self.html_crawler = HTMLCrawler()
        self.llm = GeminiImplementation()
        self._rate_limiter = _RateLimiter(limit=10)

        self.stats = {
            "sources_crawled": 0,
            "articles_crawled": 0,
            "articles_new": 0,
            "articles_processed": 0,
            "articles_relevant": 0,
            "errors": 0,
            "skipped_duplicate": 0,
        }

    # ── DB helpers ────────────────────────────────────────────────────────────

    async def _get_db(self):
        client = AsyncIOMotorClient(self.mongodb_uri, serverSelectionTimeoutMS=10_000)
        return client, client[self.db_name]

    async def _url_hash_exists(self, db, url_hash: str) -> bool:
        doc = await db.raw_data.find_one({"url_hash": url_hash}, {"_id": 1})
        return doc is not None

    async def _find_similar_processed(self, db, title: str, hours: int = 48) -> dict | None:
        """Find a recently-processed article with a similar title (for grouping)."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        candidates = await db.processed_data.find(
            {"processed_time": {"$gte": cutoff}},
            {"_id": 1, "title": 1},
        ).to_list(length=500)

        t1 = title.lower().strip()
        for c in candidates:
            t2 = c.get("title", "").lower().strip()
            if SequenceMatcher(None, t1, t2).ratio() >= 0.68:
                return c
        return None

    # ── Source fetching ───────────────────────────────────────────────────────

    async def _fetch_sources(self, db) -> list[dict]:
        docs = await db.sources.find({"is_active": True}).to_list(length=None)
        # Convert ObjectId _id to str so Source entity can validate it
        for d in docs:
            if "_id" in d:
                d["_id"] = str(d["_id"])
        return docs


    async def _fetch_keywords(self, db) -> list[str]:
        docs = await db.keywords.find({"is_active": True}).to_list(length=None)
        return [d["value"] for d in docs]

    # ── Crawl one source ──────────────────────────────────────────────────────

    async def _crawl_source(
        self, source_doc: dict, keywords: list[str]
    ) -> list[RawData]:
        source = Source(**source_doc)
        crawler = self.rss_crawler if source.source_type == SourceType.RSS else self.html_crawler
        try:
            articles = await crawler.crawl(source, keywords)
        except Exception as e:
            logger.error(f"Error crawling {source.url}: {e}")
            self.stats["errors"] += 1
            return []

        # Filter by date range
        filtered = []
        for a in articles:
            pub = a.publish_time
            if pub and pub.tzinfo is not None:
                pub = pub.replace(tzinfo=None)
            if self.date_from and pub and pub < self.date_from:
                continue
            if self.date_to and pub and pub > self.date_to:
                continue
            filtered.append(a)

        return filtered

    # ── Process a batch with LLM ──────────────────────────────────────────────

    async def _process_batch(self, batch: list[RawData]) -> list[dict]:
        await self._rate_limiter.acquire()
        batch_data = [
            {"id": str(i), "title": a.title, "raw_text": a.raw_text}
            for i, a in enumerate(batch)
        ]
        try:
            return await self.llm.extract_insights_batch(batch_data)
        except RuntimeError as e:
            logger.warning(f"Batch failed: {e} — falling back to one-by-one")
            results = []
            for a in batch:
                try:
                    await self._rate_limiter.acquire()
                    r = await self.llm.extract_insight(a.raw_text, a.title)
                    results.append(r)
                except Exception as ex:
                    logger.error(f"Single LLM call failed for '{a.title}': {ex}")
                    results.append(self.llm._default_response(a.title))
                    self.stats["errors"] += 1
            return results

    # ── Store raw + processed data ────────────────────────────────────────────

    async def _store_article(
        self, db, article: RawData, insights: dict
    ) -> None:
        if self.dry_run:
            logger.info(
                f"[DRY-RUN] Would store: '{article.title[:60]}' | "
                f"relevant={insights.get('is_relevant')} | "
                f"impact={insights.get('impact_level')}"
            )
            self.stats["articles_processed"] += 1
            if insights.get("is_relevant"):
                self.stats["articles_relevant"] += 1
            return

        # 1. Insert into raw_data
        raw_doc = article.model_dump(exclude={"id"})
        result = await db.raw_data.insert_one(raw_doc)
        raw_id = str(result.inserted_id)

        # 2. Insert into processed_data
        citation = {
            "title": article.title,
            "source_url": article.source_url,
            "domain": get_friendly_domain(article.source_url),
            "publish_time": article.publish_time or datetime.utcnow(),
        }

        processed = ProcessedData(
            raw_data_id=raw_id,
            source_url=article.source_url,
            title=article.title,
            publish_time=article.publish_time,
            citations=[citation],
            **insights,
        )
        await db.processed_data.insert_one(
            processed.model_dump(exclude={"id"})
        )

        self.stats["articles_processed"] += 1
        if insights.get("is_relevant"):
            self.stats["articles_relevant"] += 1

    # ── Main execution ────────────────────────────────────────────────────────

    async def run(self) -> dict:
        logger.info("=" * 60)
        logger.info("LTIA Radar — Local Backfill")
        logger.info(f"  Date range : {self.date_from.date()} → {self.date_to.date()}")
        logger.info(f"  MongoDB    : {self.mongodb_uri[:40]}...")
        logger.info(f"  DB name    : {self.db_name}")
        logger.info(f"  Batch size : {self.batch_size}")
        logger.info(f"  Dry-run    : {self.dry_run}")
        logger.info("=" * 60)

        # Override Gemini API key if provided via CLI
        if self.gemini_api_key:
            os.environ["GEMINI_API_KEY"] = self.gemini_api_key

        # Ensure LLM config is loaded (forces DB fetch)
        client, db = await self._get_db()

        try:
            # Verify connection
            await db.command("ping")
            logger.info("✅ MongoDB connected")
        except Exception as e:
            logger.error(f"❌ Cannot connect to MongoDB: {e}")
            raise

        # Inject CLI Gemini key directly into LLM service cache
        if self.gemini_api_key:
            self.llm._cached_keys = [self.gemini_api_key]
            self.llm._cached_model = "gemini-2.5-flash-preview-05-20"  # Adjust as needed

        # Adjust rate limit based on model
        try:
            rate = await self.llm.get_rate_limit()
            self._rate_limiter.update_limit(rate)
            logger.info(f"⚡ LLM rate limit: {rate} RPM")
        except Exception:
            logger.warning("Could not fetch LLM rate limit, using default 10 RPM")

        sources = await self._fetch_sources(db)
        keywords = await self._fetch_keywords(db)
        logger.info(f"📡 {len(sources)} active sources | {len(keywords)} keywords")

        start_time = datetime.utcnow()

        # Phase 1: Crawl all sources (sequentially to avoid overloading)
        logger.info("\n── Phase 1: Crawling sources ──")
        all_articles: list[RawData] = []

        for i, src in enumerate(sources, 1):
            logger.info(f"[{i:02d}/{len(sources):02d}] Crawling: {src.get('name', src.get('url', '?'))}")
            try:
                articles = await self._crawl_source(src, keywords)
                all_articles.extend(articles)
                self.stats["sources_crawled"] += 1
                self.stats["articles_crawled"] += len(articles)
                logger.info(f"         → {len(articles)} articles in date range")
            except Exception as e:
                logger.error(f"         → Error: {e}")
                self.stats["errors"] += 1

        logger.info(f"\n📥 Total crawled: {self.stats['articles_crawled']} articles")

        # Phase 2: Dedup against DB
        logger.info("\n── Phase 2: Deduplication ──")
        new_articles: list[RawData] = []

        for article in all_articles:
            exists = await self._url_hash_exists(db, article.url_hash)
            if exists:
                self.stats["skipped_duplicate"] += 1
                continue
            new_articles.append(article)
            self.stats["articles_new"] += 1

        logger.info(f"🆕 New articles (after dedup): {len(new_articles)} "
                    f"(skipped {self.stats['skipped_duplicate']} duplicates)")

        # Phase 3: Similarity grouping (to avoid processing same story multiple times)
        logger.info("\n── Phase 3: Similarity grouping ──")
        representative_articles: list[RawData] = []
        grouped_map: dict[int, list[RawData]] = {}

        for article in new_articles:
            t1 = article.title.lower().strip()

            # Check DB for similar recent processed article
            similar_db = await self._find_similar_processed(db, article.title)
            if similar_db:
                logger.debug(f"🔗 Grouped with DB article: '{article.title[:50]}'")
                # Add citation to existing processed article (if not dry-run)
                if not self.dry_run:
                    citation = {
                        "title": article.title,
                        "source_url": article.source_url,
                        "domain": get_friendly_domain(article.source_url),
                        "publish_time": article.publish_time or datetime.utcnow(),
                    }
                    await db.processed_data.update_one(
                        {"_id": similar_db["_id"]},
                        {"$addToSet": {"citations": citation}},
                    )
                continue

            # Check against current batch representatives
            found_group = False
            for rep in representative_articles:
                t2 = rep.title.lower().strip()
                if SequenceMatcher(None, t1, t2).ratio() >= 0.68:
                    grouped_map.setdefault(id(rep), []).append(article)
                    found_group = True
                    break

            if not found_group:
                representative_articles.append(article)

        logger.info(f"🧠 Representative articles to process: {len(representative_articles)}")

        if not representative_articles:
            logger.info("✅ Nothing to process. All articles already in DB.")
            client.close()
            return self._summary(start_time)

        # Phase 4: LLM classification in batches
        logger.info(f"\n── Phase 4: LLM classification (batch size={self.batch_size}) ──")

        # Build batches
        batches: list[list[RawData]] = []
        current_batch: list[RawData] = []
        current_chars = 0

        for article in representative_articles:
            content_len = len(article.raw_text or "")
            if (
                len(current_batch) >= 80
                or (current_chars + content_len > 320_000 and current_batch)
            ):
                batches.append(current_batch)
                current_batch = []
                current_chars = 0
            current_batch.append(article)
            current_chars += content_len
        if current_batch:
            batches.append(current_batch)

        logger.info(f"📦 {len(batches)} batches to process")

        for batch_num, batch in enumerate(batches, 1):
            logger.info(f"\n[Batch {batch_num}/{len(batches)}] {len(batch)} articles")
            try:
                insights_list = await self._process_batch(batch)

                for article, insights in zip(batch, insights_list):
                    try:
                        await self._store_article(db, article, insights)
                        status = "RELEVANT" if insights.get("is_relevant") else "irrelevant"
                        impact = insights.get("impact_level", "?")
                        logger.info(
                            f"  ✓ [{status}|{impact}] {article.title[:60]}"
                        )
                    except Exception as e:
                        logger.error(f"  ✗ Store failed for '{article.title[:50]}': {e}")
                        self.stats["errors"] += 1

            except Exception as e:
                logger.error(f"  ✗ Batch {batch_num} completely failed: {e}")
                self.stats["errors"] += len(batch)

        client.close()
        return self._summary(start_time)

    def _summary(self, start_time: datetime) -> dict:
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info("\n" + "=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"  Elapsed          : {elapsed:.0f}s ({elapsed/60:.1f}min)")
        logger.info(f"  Sources crawled  : {self.stats['sources_crawled']}")
        logger.info(f"  Articles crawled : {self.stats['articles_crawled']}")
        logger.info(f"  Duplicates skipped: {self.stats['skipped_duplicate']}")
        logger.info(f"  New articles     : {self.stats['articles_new']}")
        logger.info(f"  Processed (LLM)  : {self.stats['articles_processed']}")
        logger.info(f"  Relevant         : {self.stats['articles_relevant']}")
        logger.info(f"  Errors           : {self.stats['errors']}")
        logger.info("=" * 60)
        return self.stats


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LTIA Radar — Local Backfill Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--date-from",
        default="2026-01-01",
        help="Start date (inclusive), format YYYY-MM-DD (default: 2026-01-01)",
    )
    parser.add_argument(
        "--date-to",
        default=datetime.utcnow().strftime("%Y-%m-%d"),
        help="End date (inclusive), format YYYY-MM-DD (default: today UTC)",
    )
    parser.add_argument(
        "--mongodb-uri",
        default=None,
        help=(
            "MongoDB connection URI. "
            "Falls back to MONGODB_ATLAS_URI env var, then MONGODB_URI env var."
        ),
    )
    parser.add_argument(
        "--db-name",
        default=None,
        help="MongoDB database name. Falls back to MONGODB_DATABASE env var (default: ltia_radar)",
    )
    parser.add_argument(
        "--gemini-key",
        default=None,
        help="Gemini API key. Falls back to GEMINI_API_KEY env var.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=80,
        help="Number of articles per LLM batch (default: 80)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Crawl and classify but do NOT write to MongoDB.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Lazy-import app modules after path is set
    _lazy_imports()

    # Resolve MongoDB URI (priority: CLI > MONGODB_ATLAS_URI env > MONGODB_URI env)
    mongodb_uri = (
        args.mongodb_uri
        or os.environ.get("MONGODB_ATLAS_URI")
        or os.environ.get("MONGODB_URI")
        or getattr(settings, "mongodb_uri", None)
    )
    if not mongodb_uri:
        logger.error("❌ No MongoDB URI provided. Use --mongodb-uri or set MONGODB_ATLAS_URI env var.")
        sys.exit(1)

    # Resolve DB name
    db_name = (
        args.db_name
        or os.environ.get("MONGODB_DATABASE")
        or getattr(settings, "mongodb_database", "ltia_radar")
    )

    # Resolve Gemini key
    gemini_key = (
        args.gemini_key
        or os.environ.get("GEMINI_API_KEY")
        or getattr(settings, "gemini_api_key", None)
    )
    if not gemini_key:
        logger.warning("⚠️ No Gemini API key found. LLM calls will return default responses.")

    # Parse dates
    try:
        date_from = datetime.strptime(args.date_from, "%Y-%m-%d")
        date_to = datetime.strptime(args.date_to, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
    except ValueError as e:
        logger.error(f"❌ Invalid date format: {e}")
        sys.exit(1)

    backfill = LocalBackfill(
        mongodb_uri=mongodb_uri,
        db_name=db_name,
        gemini_api_key=gemini_key,
        date_from=date_from,
        date_to=date_to,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    await backfill.run()


if __name__ == "__main__":
    asyncio.run(main())
