"""
Crawler API — Manual trigger endpoint for crawl cycles.
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.dependencies import get_crawl_use_case
from app.application.crawl_news import CrawlNewsUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crawler", tags=["Crawler"])


@router.post("/trigger")
async def trigger_crawl(
    background_tasks: BackgroundTasks,
    use_case: CrawlNewsUseCase = Depends(get_crawl_use_case),
):
    """
    Manually trigger a crawl cycle.
    Runs in the background so the response returns immediately.
    """
    background_tasks.add_task(_run_crawl, use_case)
    return {
        "message": "Crawl cycle triggered",
        "status": "running_in_background",
    }


async def _run_crawl(use_case: CrawlNewsUseCase):
    """Background task wrapper for crawl execution."""
    try:
        stats = await use_case.execute()
        logger.info(f"Manual crawl completed: {stats}")
    except Exception as e:
        logger.error(f"Manual crawl failed: {e}")
