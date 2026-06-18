"""
Dashboard API — Aggregated statistics endpoints (US-1.3).
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_processed_data_repo
from app.infrastructure.database.repositories import ProcessedDataRepository

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    date_from: Optional[str] = Query(None, description="ISO date string"),
    date_to: Optional[str] = Query(None, description="ISO date string"),
    repo: ProcessedDataRepository = Depends(get_processed_data_repo),
):
    """
    Get aggregated dashboard statistics.
    Includes: total count, sentiment distribution, category distribution, timeline.
    Target render time: < 2.0 seconds (US-1.3 AC#3).
    """
    dt_from = datetime.fromisoformat(date_from) if date_from else None
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    # Parallel aggregation queries
    total = await repo.count()
    sentiment_dist = await repo.get_sentiment_distribution(dt_from, dt_to)
    category_dist = await repo.get_category_distribution(dt_from, dt_to)
    timeline = await repo.get_timeline(dt_from, dt_to)

    # Count specific metrics
    critical_count = await repo.count({"impact_level": "CRITICAL"})
    negative_count = await repo.count({"sentiment": "NEGATIVE"})
    rumor_count = await repo.count({"is_rumor": True})

    return {
        "total_articles": total,
        "critical_count": critical_count,
        "negative_count": negative_count,
        "rumor_count": rumor_count,
        "negative_percentage": round(
            (negative_count / total * 100) if total > 0 else 0, 1
        ),
        "sentiment_distribution": sentiment_dist,
        "category_distribution": category_dist,
        "timeline": timeline,
    }


@router.get("/top-risks")
async def get_top_risks(
    limit: int = Query(10, ge=1, le=50),
    repo: ProcessedDataRepository = Depends(get_processed_data_repo),
):
    """Get top N highest risk articles (US-1.3 AC#1)."""
    top_risks = await repo.get_top_risks(limit=limit)
    return {"data": top_risks}
