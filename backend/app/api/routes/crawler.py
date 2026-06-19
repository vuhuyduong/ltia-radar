"""
Crawler API — Manual trigger and scheduling settings endpoints.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.api.dependencies import (
    get_crawl_use_case,
    get_raw_data_repo,
    get_crawler_settings_repo,
)
from app.application.crawl_news import CrawlNewsUseCase
from app.infrastructure.database.repositories import (
    RawDataRepository,
    CrawlerSettingsRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crawler", tags=["Crawler"])


class CrawlerTriggerPayload(BaseModel):
    trigger_type: str  # "fast" or "advanced"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@router.post("/trigger")
async def trigger_crawl(
    payload: CrawlerTriggerPayload,
    background_tasks: BackgroundTasks,
    use_case: CrawlNewsUseCase = Depends(get_crawl_use_case),
    raw_repo: RawDataRepository = Depends(get_raw_data_repo),
):
    """
    Trigger a crawl cycle.
    If fast, crawls from the latest crawled article time.
    If advanced, crawls between specific dates.
    Runs in the background so the response returns immediately.
    """
    dt_from = payload.date_from
    dt_to = payload.date_to

    if payload.trigger_type == "fast":
        # Fast trigger: find the latest crawl time
        latest_time = await raw_repo.get_latest_crawl_time()
        if latest_time:
            dt_from = latest_time
            logger.info(f"⚡ Fast trigger activated: crawling articles since {dt_from}")
        else:
            logger.info("⚡ Fast trigger activated: no previous articles found, crawling all time")

    background_tasks.add_task(_run_crawl, use_case, dt_from, dt_to)
    
    return {
        "message": "Crawl cycle triggered",
        "status": "running_in_background",
        "trigger_type": payload.trigger_type,
        "date_from": dt_from.isoformat() if dt_from else None,
        "date_to": dt_to.isoformat() if dt_to else None,
    }


async def _run_crawl(use_case: CrawlNewsUseCase, date_from: Optional[datetime], date_to: Optional[datetime]):
    """Background task wrapper for crawl execution."""
    try:
        stats = await use_case.execute(date_from=date_from, date_to=date_to)
        logger.info(f"Manual crawl completed: {stats}")
    except Exception as e:
        logger.error(f"Manual crawl failed: {e}")


@router.get("/settings")
async def get_crawler_settings(
    repo: CrawlerSettingsRepository = Depends(get_crawler_settings_repo),
):
    """Get the current automatic crawl frequency settings."""
    settings = await repo.get_settings()
    return settings


@router.post("/settings")
async def update_crawler_settings(
    payload: dict,
    repo: CrawlerSettingsRepository = Depends(get_crawler_settings_repo),
):
    """Update crawler scheduling settings and reload scheduler in real-time."""
    settings = await repo.update_settings(payload)
    
    # Reload APScheduler jobs dynamically in real-time
    from app.scheduler.jobs import setup_scheduler_jobs
    await setup_scheduler_jobs()
    
    return settings
