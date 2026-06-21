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

    background_tasks.add_task(_run_crawl, use_case, dt_from, dt_to, f"manual_{payload.trigger_type}")
    
    return {
        "message": "Crawl cycle triggered",
        "status": "running_in_background",
        "trigger_type": payload.trigger_type,
        "date_from": dt_from.isoformat() if dt_from else None,
        "date_to": dt_to.isoformat() if dt_to else None,
    }


async def _run_crawl(use_case: CrawlNewsUseCase, date_from: Optional[datetime], date_to: Optional[datetime], trigger_type: str):
    """Background task wrapper for crawl execution."""
    try:
        stats = await use_case.execute(date_from=date_from, date_to=date_to, trigger_type=trigger_type)
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


@router.get("/logs")
async def get_crawler_logs(
    raw_repo: RawDataRepository = Depends(get_raw_data_repo),
    settings_repo: CrawlerSettingsRepository = Depends(get_crawler_settings_repo),
):
    """
    Get backend activity logs: news stats, schedule stats, and recent execution history.
    """
    db = raw_repo.collection.database
    
    # 1. News Statistics
    total_crawled = await db.raw_data.count_documents({})
    total_relevant = await db.processed_data.count_documents({"is_relevant": True})
    total_irrelevant = await db.processed_data.count_documents({"is_relevant": False})
    
    # 2. Schedule & Running Info
    settings_doc = await settings_repo.get_settings()
    is_enabled = settings_doc.get("is_enabled", True)
    frequency_type = settings_doc.get("frequency_type", "interval")
    
    freq_desc = "Không hoạt động"
    if is_enabled:
        if frequency_type == "interval":
            freq_desc = f"Mỗi {settings_doc.get('interval_minutes', 60)} phút"
        elif frequency_type == "daily":
            freq_desc = "Hàng ngày lúc 00:00"
        elif frequency_type == "fixed_hours":
            hours = ", ".join(settings_doc.get("fixed_hours", []))
            freq_desc = f"Khung giờ cố định: {hours}"
        elif frequency_type == "hourly_range":
            hr = settings_doc.get("hourly_range", {})
            freq_desc = f"Quét từ {hr.get('start_hour', 7)}h đến {hr.get('end_hour', 19)}h, chu kỳ {hr.get('interval_hours', 1)}h"
            
    # Next run and last run from database
    from app.scheduler.jobs import scheduler
    job = scheduler.get_job("crawl_news")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    
    latest_log = await db.crawl_logs.find_one(sort=[("timestamp", -1)])
    last_run = latest_log["timestamp"].isoformat() if latest_log else None
    
    # 3. Recent Runs History (Last 15 logs)
    cursor = db.crawl_logs.find().sort("timestamp", -1).limit(15)
    recent_runs = []
    async for log in cursor:
        log["_id"] = str(log["_id"])
        if isinstance(log.get("timestamp"), datetime):
            log["timestamp"] = log["timestamp"].isoformat()
        recent_runs.append(log)
        
    return {
        "news_stats": {
            "total_crawled": total_crawled,
            "total_relevant": total_relevant,
            "total_irrelevant": total_irrelevant,
        },
        "schedule_stats": {
            "is_enabled": is_enabled,
            "frequency_type": frequency_type,
            "frequency_description": freq_desc,
            "last_run": last_run,
            "next_run": next_run,
        },
        "recent_runs": recent_runs,
    }
