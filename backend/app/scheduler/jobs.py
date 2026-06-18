"""
Scheduler Jobs — APScheduler cronjob for periodic crawling (US-2.1).
Triggers at minute 00 of every hour.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api.dependencies import get_crawl_use_case
from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_crawl():
    """
    Scheduled crawl job — runs every hour (US-2.1 AC#1).
    Creates a new use case instance for each execution.
    """
    logger.info("⏰ Scheduled crawl triggered")
    try:
        use_case = get_crawl_use_case()
        stats = await use_case.execute()
        logger.info(f"⏰ Scheduled crawl completed: {stats}")
    except Exception as e:
        logger.error(f"⏰ Scheduled crawl failed: {e}")


def start_scheduler():
    """Start the APScheduler with the crawl cronjob."""
    interval_minutes = settings.crawler_interval_minutes

    scheduler.add_job(
        scheduled_crawl,
        "interval",
        minutes=interval_minutes,
        id="crawl_news",
        name=f"Crawl News (every {interval_minutes} min)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"📅 Scheduler started: crawl every {interval_minutes} minutes")


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("📅 Scheduler stopped")
