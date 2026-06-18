"""
Crawl News Use Case — Orchestrates the full pipeline:
  Crawl → Dedup → Process (LLM) → Store → Alert

This is the core business logic for the LTIA Radar system.
"""

import asyncio
import logging
from datetime import datetime

from app.config import settings
from app.domain.entities.processed_data import ProcessedData
from app.domain.entities.source import Source, SourceType
from app.domain.interfaces.alert_service import IAlertService
from app.domain.interfaces.crawler_service import ICrawlerBase
from app.domain.interfaces.llm_service import ILLMService
from app.infrastructure.database.repositories import (
    AlertRuleRepository,
    KeywordRepository,
    ProcessedDataRepository,
    RawDataRepository,
    SourceRepository,
)

logger = logging.getLogger(__name__)


class CrawlNewsUseCase:
    """
    Orchestrates the full crawl → process → alert pipeline.

    Phase 1 simplification: No Redis Queue.
    Uses asyncio.Semaphore for rate limiting (max 10 LLM calls/minute).
    """

    def __init__(
        self,
        rss_crawler: ICrawlerBase,
        html_crawler: ICrawlerBase,
        llm_service: ILLMService,
        alert_service: IAlertService,
    ):
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

        # Rate limiting: max N LLM calls per minute (PRD requirement)
        self._llm_semaphore = asyncio.Semaphore(settings.llm_rate_limit_per_minute)
        self._call_count = 0
        self._window_start = datetime.utcnow()

    async def execute(self) -> dict:
        """
        Run a full crawl cycle.

        Returns:
            Summary dict with counts of crawled, processed, and alerted articles.
        """
        logger.info("🚀 Starting crawl cycle...")
        start_time = datetime.utcnow()

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

            # Step 2: Crawl all sources
            all_raw_articles = []
            for source_doc in sources:
                source = Source(**source_doc)
                crawler = (
                    self.rss_crawler
                    if source.source_type == SourceType.RSS
                    else self.html_crawler
                )

                try:
                    articles = await crawler.crawl(source, keywords)
                    all_raw_articles.extend(articles)
                    stats["crawled"] += len(articles)
                except Exception as e:
                    logger.error(f"Error crawling {source.url}: {e}")
                    stats["errors"] += 1

            logger.info(f"📥 Total crawled: {stats['crawled']} articles")

            # Step 3: Dedup and store raw data
            new_articles = []
            for article in all_raw_articles:
                try:
                    # Check if already exists (US-2.2)
                    if await self.raw_data_repo.exists_by_url_hash(article.url_hash):
                        continue

                    # Store raw data
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

            # Step 4: Process with LLM (rate-limited)
            active_rules = await self.alert_rule_repo.find_active()

            for article in new_articles:
                try:
                    # Rate limiting: simple sliding window
                    await self._rate_limit()

                    # Call LLM
                    insights = await self.llm_service.extract_insight(
                        raw_text=article.raw_text,
                        title=article.title,
                    )

                    # Store processed data
                    processed = ProcessedData(
                        raw_data_id=article.id,
                        source_url=article.source_url,
                        title=article.title,
                        **insights,
                    )
                    processed_doc = await self.processed_repo.create(
                        processed.model_dump(exclude={"id"})
                    )
                    processed.id = processed_doc["_id"]
                    stats["processed"] += 1

                    # Step 5: Check alert rules
                    for rule_doc in active_rules:
                        if self._matches_rule(processed, rule_doc):
                            from app.domain.entities.alert_rule import AlertRule

                            rule = AlertRule(**rule_doc)
                            success = await self.alert_service.send_alert(
                                processed, rule
                            )
                            if success:
                                stats["alerts_sent"] += 1

                except Exception as e:
                    logger.error(f"Error processing article {article.source_url}: {e}")
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

    async def _rate_limit(self):
        """
        Simple rate limiter: max N calls per 60-second window.
        Phase 1 uses in-process semaphore (Phase 2 will use Upstash Redis Token Bucket).
        """
        now = datetime.utcnow()
        elapsed = (now - self._window_start).total_seconds()

        if elapsed >= 60:
            # Reset window
            self._call_count = 0
            self._window_start = now

        if self._call_count >= settings.llm_rate_limit_per_minute:
            # Wait for window to reset
            wait_time = 60 - elapsed
            logger.info(f"⏳ Rate limit reached, waiting {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)
            self._call_count = 0
            self._window_start = datetime.utcnow()

        self._call_count += 1

    def _matches_rule(self, processed: ProcessedData, rule_doc: dict) -> bool:
        """Check if processed data matches an alert rule's conditions."""
        conditions = rule_doc.get("condition_query", {})
        if not conditions:
            return False

        for field, expected_value in conditions.items():
            actual_value = getattr(processed, field, None)
            if actual_value is None:
                return False

            # Handle list fields (category, target_scope)
            if isinstance(actual_value, list):
                if isinstance(expected_value, list):
                    # Check if any expected value is in actual list
                    if not any(v in actual_value for v in expected_value):
                        return False
                else:
                    if expected_value not in actual_value:
                        return False
            else:
                # Direct comparison
                if isinstance(actual_value, str):
                    actual_value = actual_value.upper()
                if isinstance(expected_value, str):
                    expected_value = expected_value.upper()
                if actual_value != expected_value:
                    return False

        return True
