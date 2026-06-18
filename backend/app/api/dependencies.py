"""
DI Dependencies — Factory functions for FastAPI Depends().
Following Clean Architecture dependency injection (PRD Section 9.1).
"""

from app.application.crawl_news import CrawlNewsUseCase
from app.infrastructure.alerting.telegram import TelegramAlertService
from app.infrastructure.crawler.html_crawler import HTMLCrawler
from app.infrastructure.crawler.rss_crawler import RSSCrawler
from app.infrastructure.database.repositories import (
    AlertRuleRepository,
    KeywordRepository,
    ProcessedDataRepository,
    RawDataRepository,
    SourceRepository,
)
from app.infrastructure.llm.gemini import GeminiImplementation


# ── Repository singletons ──
def get_source_repo() -> SourceRepository:
    return SourceRepository()


def get_keyword_repo() -> KeywordRepository:
    return KeywordRepository()


def get_raw_data_repo() -> RawDataRepository:
    return RawDataRepository()


def get_processed_data_repo() -> ProcessedDataRepository:
    return ProcessedDataRepository()


def get_alert_rule_repo() -> AlertRuleRepository:
    return AlertRuleRepository()


# ── Service factories ──
def get_llm_service() -> GeminiImplementation:
    """Factory for LLM service. Switch implementation here to swap AI provider."""
    return GeminiImplementation()


def get_alert_service() -> TelegramAlertService:
    """Factory for alert service. Switch implementation here to swap notification channel."""
    return TelegramAlertService()


def get_crawl_use_case() -> CrawlNewsUseCase:
    """Factory for the main crawl orchestration use case."""
    return CrawlNewsUseCase(
        rss_crawler=RSSCrawler(),
        html_crawler=HTMLCrawler(),
        llm_service=get_llm_service(),
        alert_service=get_alert_service(),
    )
