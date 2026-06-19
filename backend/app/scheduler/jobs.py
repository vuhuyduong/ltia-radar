"""
Scheduler Jobs — APScheduler cronjob for periodic crawling (US-2.1).
Supports dynamic configuration matching interval, daily, fixed hours, or hourly ranges.
"""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api.dependencies import get_crawl_use_case

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")


async def scheduled_crawl():
    """
    Scheduled crawl job.
    Creates a new use case instance for each execution.
    """
    logger.info("⏰ Scheduled crawl triggered")
    try:
        use_case = get_crawl_use_case()
        stats = await use_case.execute()
        logger.info(f"⏰ Scheduled crawl completed: {stats}")
    except Exception as e:
        logger.error(f"⏰ Scheduled crawl failed: {e}")


async def setup_scheduler_jobs():
    """Load settings and configure the scheduler jobs accordingly."""
    from app.api.dependencies import get_crawler_settings_repo
    repo = get_crawler_settings_repo()
    config = await repo.get_settings()

    is_enabled = config.get("is_enabled", True)
    freq_type = config.get("frequency_type", "interval")

    logger.info(f"📅 Setting up scheduler: enabled={is_enabled}, type={freq_type}")

    # Remove existing job if any
    if scheduler.get_job("crawl_news"):
        scheduler.remove_job("crawl_news")

    if not is_enabled:
        logger.info("📅 Scheduler job is disabled")
        return

    if freq_type == "interval":
        interval_minutes = config.get("interval_minutes", 60)
        scheduler.add_job(
            scheduled_crawl,
            "interval",
            minutes=interval_minutes,
            id="crawl_news",
            name=f"Crawl News (every {interval_minutes} min)",
            replace_existing=True,
        )
        logger.info(f"📅 Scheduled crawl job as interval: every {interval_minutes} minutes")
    elif freq_type == "daily":
        scheduler.add_job(
            scheduled_crawl,
            "cron",
            hour=0,
            minute=0,
            id="crawl_news",
            name="Crawl News Daily (at 00:00)",
            replace_existing=True,
        )
        logger.info("📅 Scheduled crawl job as daily (at 00:00)")
    elif freq_type == "fixed_hours":
        fixed_hours = config.get("fixed_hours", ["07:00", "10:00", "12:00"])
        # Extract hour part for each time, ensure unique sorted integers
        hours = sorted(list(set([int(t.split(":")[0]) for t in fixed_hours if ":" in t])))
        if hours:
            hour_str = ",".join(map(str, hours))
            scheduler.add_job(
                scheduled_crawl,
                "cron",
                hour=hour_str,
                minute=0,
                id="crawl_news",
                name=f"Crawl News at hours: {hour_str}",
                replace_existing=True,
            )
            logger.info(f"📅 Scheduled crawl job at fixed hours: {hour_str}")
        else:
            logger.warning("📅 No valid fixed hours specified, skipping scheduling")
    elif freq_type == "hourly_range":
        hr_range = config.get("hourly_range", {})
        start_hour = hr_range.get("start_hour", 7)
        end_hour = hr_range.get("end_hour", 19)
        step = hr_range.get("interval_hours", 1)
        hour_str = f"{start_hour}-{end_hour}/{step}"
        scheduler.add_job(
            scheduled_crawl,
            "cron",
            hour=hour_str,
            minute=0,
            id="crawl_news",
            name=f"Crawl News hourly range: {hour_str}",
            replace_existing=True,
        )
        logger.info(f"📅 Scheduled crawl job with hourly range: {hour_str}")


async def start_scheduler():
    """Start the APScheduler and load dynamic settings."""
    await setup_scheduler_jobs()
    if not scheduler.running:
        scheduler.start()
        logger.info("📅 Scheduler started")


def stop_scheduler():
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("📅 Scheduler stopped")
