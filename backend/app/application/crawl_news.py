"""
Crawl News Use Case — Orchestrates the full pipeline:
  Crawl → Dedup → Process (LLM) → Store → Alert

This is the core business logic for the LTIA Radar system.

Fixes applied (audit 2026-06-20):
  - Flaw 2:  Broken rate limiter replaced with _RateLimiter (asyncio.Lock + monotonic clock).
  - Flaw 3:  Source crawling parallelized with asyncio.gather.
  - Flaw 7:  Batch fallback only triggers on total RuntimeError; partial results not discarded.
  - Flaw 11: _grouped_articles no longer mutates Pydantic model; uses external grouped_map dict.
  - Flaw 12: get_domain_name() replaced by get_friendly_domain import (single source of truth).
"""

import asyncio
import logging
import time
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import urlparse

from app.config import settings
from app.domain.entities.processed_data import ProcessedData
from app.domain.entities.raw_data import RawData
from app.domain.entities.source import Source, SourceType
from app.domain.interfaces.alert_service import IAlertService
from app.domain.interfaces.crawler_service import ICrawlerBase
from app.domain.interfaces.llm_service import ILLMService
from app.domain.utils.domain_mapper import get_friendly_domain
from app.infrastructure.database.repositories import (
    AlertRuleRepository,
    KeywordRepository,
    ProcessedDataRepository,
    RawDataRepository,
    SourceRepository,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiter (Flaw 2 fix)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """
    Correct token-bucket rate limiter using asyncio.Lock for mutual exclusion.

    Key properties:
      - asyncio.Lock prevents concurrent counter mutation (eliminates race condition).
      - time.monotonic() is immune to NTP clock jumps that could reset windows prematurely.
      - Lock is released before asyncio.sleep() so other waiters can queue without deadlock.
    """

    __slots__ = ("_limit", "_count", "_window_start", "_lock")

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._count = 0
        self._window_start = time.monotonic()
        self._lock = asyncio.Lock()

    def update_limit(self, limit: int) -> None:
        """Adjust limit without resetting the current window."""
        self._limit = limit

    async def acquire(self) -> None:
        """Block until a token is available, then consume one token."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._window_start

            if elapsed >= 60.0:
                self._count = 0
                self._window_start = now
                elapsed = 0.0

            if self._count >= self._limit:
                wait = 60.0 - elapsed
                logger.info(f"⏳ Rate limit reached, waiting {wait:.1f}s...")
                # Release lock BEFORE sleeping so other waiters can make progress
                self._lock.release()
                try:
                    await asyncio.sleep(wait)
                finally:
                    await self._lock.acquire()
                self._count = 0
                self._window_start = time.monotonic()

            self._count += 1


# ---------------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------------

class CrawlNewsUseCase:
    """
    Orchestrates the full crawl → process → alert pipeline.

    Phase 1 simplification: No Redis Queue.
    Rate limiting via in-process _RateLimiter (Phase 2 will use Upstash Redis Token Bucket).
    """

    def __init__(
        self,
        rss_crawler: ICrawlerBase,
        html_crawler: ICrawlerBase,
        llm_service: ILLMService,
        alert_service: IAlertService,
    ) -> None:
        self.rss_crawler = rss_crawler
        self.html_crawler = html_crawler
        self.llm_service = llm_service
        self.alert_service = alert_service

        # Repositories
        self.source_repo = SourceRepository()
        self.keyword_repo = KeywordRepository()
        self.raw_data_repo = RawDataRepository()
        self.processed_repo = ProcessedDataRepository()
        self.alert_rule_repo = AlertRuleRepository()

        # Rate limiter — limit updated dynamically from active model config
        self._rate_limiter = _RateLimiter(settings.llm_rate_limit_per_minute)

    # ------------------------------------------------------------------
    # Main pipeline entry point
    # ------------------------------------------------------------------

    async def execute(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict:
        """
        Run a full crawl cycle.

        Returns:
            Summary dict with counts of crawled, processed, and alerted articles.
        """
        if date_from and date_from.tzinfo is not None:
            date_from = date_from.replace(tzinfo=None)
        if date_to and date_to.tzinfo is not None:
            date_to = date_to.replace(tzinfo=None)

        logger.info(f"🚀 Starting crawl cycle... (date_from={date_from}, date_to={date_to})")
        start_time = datetime.utcnow()

        # Dynamically adjust rate limit from active model RPM
        rate_limit = await self.llm_service.get_rate_limit()
        self._rate_limiter.update_limit(rate_limit)

        stats = {
            "crawled": 0,
            "new_articles": 0,
            "processed": 0,
            "alerts_sent": 0,
            "errors": 0,
        }

        try:
            # Step 1: Get active sources and keywords
            sources = await self.source_repo.find_active()
            keyword_docs = await self.keyword_repo.find_active()
            keywords = [kw["value"] for kw in keyword_docs]

            if not sources:
                logger.warning("⚠️ No active sources configured")
                return stats

            logger.info(f"📡 Crawling {len(sources)} sources with {len(keywords)} keywords")

            # Step 2: Crawl all sources in parallel (Flaw 3 fix)
            crawl_tasks = [
                self._crawl_source(src, keywords, date_from, date_to)
                for src in sources
            ]
            crawl_results = await asyncio.gather(*crawl_tasks)

            all_raw_articles: list[RawData] = []
            for filtered_articles, error_count in crawl_results:
                all_raw_articles.extend(filtered_articles)
                stats["crawled"] += len(filtered_articles)
                stats["errors"] += error_count

            logger.info(f"📥 Total crawled (filtered): {stats['crawled']} articles")

            # Step 3: Dedup and store raw data
            new_articles: list[RawData] = []
            for article in all_raw_articles:
                try:
                    if await self.raw_data_repo.exists_by_url_hash(article.url_hash):
                        continue
                    raw_doc = await self.raw_data_repo.create(
                        article.model_dump(exclude={"id"})
                    )
                    article.id = raw_doc["_id"]
                    new_articles.append(article)
                    stats["new_articles"] += 1
                except Exception as e:
                    logger.warning(f"Error storing raw data: {e}")
                    stats["errors"] += 1

            logger.info(f"🆕 New articles (after dedup): {stats['new_articles']}")

            # Step 4: Similarity-based grouping & pre-LLM deduplication
            # grouped_map: id(representative) → [grouped articles]
            # Using id() as key avoids mutating the Pydantic model (Flaw 11 fix).
            representative_articles: list[RawData] = []
            grouped_map: dict[int, list[RawData]] = {}

            logger.info("🔍 Performing similarity deduplication on new articles...")
            for article in new_articles:
                # 4.1 Check against DB (processed in the last 48 hours)
                similar_doc = await self.processed_repo.find_similar_article(
                    article.title, hours_window=48
                )
                if similar_doc:
                    citation = {
                        "title": article.title,
                        "source_url": article.source_url,
                        "domain": get_friendly_domain(article.source_url),
                        "publish_time": article.publish_time or datetime.utcnow(),
                    }
                    await self.processed_repo.add_citation(similar_doc["_id"], citation)
                    logger.info(
                        f"🔗 Grouped '{article.title}' under DB article {similar_doc['_id']}"
                    )
                    continue

                # 4.2 Check against current batch representatives
                t1 = self._normalize_title(article.title)
                found_group = False
                for rep in representative_articles:
                    t2 = self._normalize_title(rep.title)
                    if SequenceMatcher(None, t1, t2).ratio() >= 0.68:
                        grouped_map.setdefault(id(rep), []).append(article)
                        found_group = True
                        logger.info(
                            f"🔗 Grouped '{article.title}' under batch rep '{rep.title}'"
                        )
                        break

                if not found_group:
                    representative_articles.append(article)

            logger.info(
                f"🧠 Representative articles to process: {len(representative_articles)} "
                f"(out of {len(new_articles)})"
            )

            # Step 5: Process with LLM in batches
            active_rules = await self.alert_rule_repo.find_active()

            # Dynamic batching: ≤10 articles or ≤40,000 chars total per batch
            batches: list[list[RawData]] = []
            current_batch: list[RawData] = []
            current_chars = 0

            for article in representative_articles:
                content_len = len(article.raw_text or "")
                if len(current_batch) >= 10 or (current_chars + content_len > 40000 and current_batch):
                    batches.append(current_batch)
                    current_batch = []
                    current_chars = 0
                current_batch.append(article)
                current_chars += content_len
            if current_batch:
                batches.append(current_batch)

            for batch in batches:
                total_chars = sum(len(a.raw_text or "") for a in batch)
                logger.info(f"🧠 Processing batch of {len(batch)} articles ({total_chars} chars)")

                batch_data = [
                    {"id": str(a.id), "title": a.title, "raw_text": a.raw_text}
                    for a in batch
                ]

                try:
                    # extract_insights_batch guarantees len(result) == len(input) (Flaw 7 fix)
                    await self._rate_limiter.acquire()
                    insights_list = await self.llm_service.extract_insights_batch(batch_data)
                    logger.info(f"✅ Batch of {len(batch)} processed successfully")

                    for article, insights in zip(batch, insights_list):
                        try:
                            await self._store_and_alert(
                                article,
                                insights,
                                active_rules,
                                stats,
                                grouped_articles=grouped_map.get(id(article), []),
                            )
                        except Exception as store_err:
                            logger.error(f"Error storing/alerting: {store_err}")
                            stats["errors"] += 1

                except RuntimeError:
                    # Total failure across all keys — fall back to one-by-one
                    logger.warning("⚠️ Batch failed for all keys. Falling back to one-by-one...")
                    for article in batch:
                        try:
                            await self._rate_limiter.acquire()
                            insights = await self.llm_service.extract_insight(
                                raw_text=article.raw_text,
                                title=article.title,
                            )
                            await self._store_and_alert(
                                article,
                                insights,
                                active_rules,
                                stats,
                                grouped_articles=grouped_map.get(id(article), []),
                            )
                        except Exception as e:
                            logger.error(
                                f"One-by-one failed for {article.source_url}: {e}"
                            )
                            stats["errors"] += 1

        except Exception as e:
            logger.error(f"❌ Crawl cycle failed: {e}")
            stats["errors"] += 1

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"✅ Crawl cycle completed in {elapsed:.1f}s | "
            f"Crawled: {stats['crawled']}, New: {stats['new_articles']}, "
            f"Processed: {stats['processed']}, Alerts: {stats['alerts_sent']}, "
            f"Errors: {stats['errors']}"
        )
        return stats

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _crawl_source(
        self,
        source_doc: dict,
        keywords: list[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> tuple[list[RawData], int]:
        """
        Crawl a single source and return (filtered_articles, error_count).
        Designed to be run concurrently via asyncio.gather (Flaw 3 fix).
        """
        source = Source(**source_doc)
        crawler: ICrawlerBase = (
            self.rss_crawler if source.source_type == SourceType.RSS else self.html_crawler
        )
        try:
            articles = await crawler.crawl(source, keywords)
            filtered: list[RawData] = []
            for article in articles:
                pub = article.publish_time
                if pub and pub.tzinfo is not None:
                    pub = pub.replace(tzinfo=None)
                if date_from and pub and pub < date_from:
                    continue
                if date_to and pub and pub > date_to:
                    continue
                filtered.append(article)
            return filtered, 0
        except Exception as e:
            logger.error(f"Error crawling {source.url}: {e}")
            return [], 1

    async def _store_and_alert(
        self,
        article: RawData,
        insights: dict,
        active_rules: list[dict],
        stats: dict,
        grouped_articles: list[RawData] | None = None,
    ) -> None:
        """
        Store LLM insights and trigger Telegram alerts if rules match.

        grouped_articles is passed explicitly — not read from article attributes
        — to keep the Pydantic model unmodified (Flaw 11 fix).
        """
        # Build citations list from primary article + any grouped duplicates
        citations = [self._make_citation(article)]
        for ga in (grouped_articles or []):
            citations.append(self._make_citation(ga))

        processed = ProcessedData(
            raw_data_id=article.id,
            source_url=article.source_url,
            title=article.title,
            publish_time=article.publish_time,
            citations=citations,
            **insights,
        )
        processed_doc = await self.processed_repo.create(
            processed.model_dump(exclude={"id"})
        )
        processed.id = processed_doc["_id"]
        stats["processed"] += 1

        # Evaluate alert rules
        for rule_doc in active_rules:
            if self._matches_rule(processed, rule_doc):
                from app.domain.entities.alert_rule import AlertRule
                rule = AlertRule(**rule_doc)
                success = await self.alert_service.send_alert(processed, rule)
                if success:
                    stats["alerts_sent"] += 1

    @staticmethod
    def _make_citation(article: RawData) -> dict:
        """Build a citation dict from a RawData article."""
        return {
            "title": article.title,
            "source_url": article.source_url,
            "domain": get_friendly_domain(article.source_url),
            "publish_time": article.publish_time or datetime.utcnow(),
        }

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize title for SequenceMatcher comparison."""
        return title.lower().strip().replace('"', "").replace("'", "")

    def _matches_rule(self, processed: ProcessedData, rule_doc: dict) -> bool:
        """Check if processed data satisfies all conditions in an alert rule."""
        conditions = rule_doc.get("condition_query", {})
        if not conditions:
            return False

        for field, expected_value in conditions.items():
            actual_value = getattr(processed, field, None)
            if actual_value is None:
                return False

            # List fields (category, target_scope)
            if isinstance(actual_value, list):
                if isinstance(expected_value, list):
                    if not any(v in actual_value for v in expected_value):
                        return False
                else:
                    if expected_value not in actual_value:
                        return False
            else:
                # Scalar field
                if isinstance(expected_value, list):
                    normalized_expected = [
                        v.upper() if isinstance(v, str) else v for v in expected_value
                    ]
                    normalized_actual = (
                        actual_value.upper() if isinstance(actual_value, str) else actual_value
                    )
                    if normalized_actual not in normalized_expected:
                        return False
                else:
                    actual_cmp = actual_value.upper() if isinstance(actual_value, str) else actual_value
                    expected_cmp = expected_value.upper() if isinstance(expected_value, str) else expected_value
                    if actual_cmp != expected_cmp:
                        return False

        return True
