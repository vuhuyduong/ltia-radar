"""
Dashboard API — Aggregated statistics endpoints (US-1.3).
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_processed_data_repo
from app.infrastructure.database.repositories import ProcessedDataRepository

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    date_from: Optional[str] = Query(None, description="ISO date string"),
    date_to: Optional[str] = Query(None, description="ISO date string"),
    limit_articles: Optional[int] = Query(None, description="Limit to last N articles"),
    last_days: Optional[int] = Query(None, description="Limit to last N days"),
    target_scope: Optional[str] = Query(None, description="Filter by target scope/gói thầu"),
    repo: ProcessedDataRepository = Depends(get_processed_data_repo),
):
    """
    Get aggregated dashboard statistics.
    Includes: total count, sentiment distribution, category distribution, timeline.
    Target render time: < 2.0 seconds (US-1.3 AC#3).
    """
    dt_from = None
    if last_days:
        dt_from = datetime.utcnow() - timedelta(days=last_days)
    elif date_from:
        dt_from = datetime.fromisoformat(date_from)
        
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    query = {"is_relevant": {"$ne": False}}
    if target_scope:
        query["target_scope"] = {"$in": [target_scope]}
    if dt_from or dt_to:
        query["processed_time"] = {}
        if dt_from:
            query["processed_time"]["$gte"] = dt_from
        if dt_to:
            query["processed_time"]["$lte"] = dt_to

    if limit_articles:
        # Fetch the most recent N processed data articles matching the date criteria
        cursor = repo.collection.find(query, {"_id": 1}).sort("processed_time", -1).limit(limit_articles)
        ids = [doc["_id"] async for doc in cursor]
        query = {"_id": {"$in": ids}}

    # Parallel aggregation queries
    total = await repo.count(query)
    sentiment_dist = await repo.get_sentiment_distribution(query=query)
    category_dist = await repo.get_category_distribution(query=query)
    timeline = await repo.get_timeline(query=query)

    # Count specific metrics
    critical_query = dict(query)
    critical_query["impact_level"] = "CRITICAL"
    critical_count = await repo.count(critical_query)

    negative_query = dict(query)
    negative_query["sentiment"] = "NEGATIVE"
    negative_count = await repo.count(negative_query)

    rumor_query = dict(query)
    rumor_query["is_rumor"] = True
    rumor_count = await repo.count(rumor_query)

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
    date_from: Optional[str] = Query(None, description="ISO date string"),
    date_to: Optional[str] = Query(None, description="ISO date string"),
    limit_articles: Optional[int] = Query(None, description="Limit to last N articles"),
    last_days: Optional[int] = Query(None, description="Limit to last N days"),
    target_scope: Optional[str] = Query(None, description="Filter by target scope/gói thầu"),
    repo: ProcessedDataRepository = Depends(get_processed_data_repo),
):
    """Get top N highest risk articles (US-1.3 AC#1) with optional filters."""
    dt_from = None
    if last_days:
        dt_from = datetime.utcnow() - timedelta(days=last_days)
    elif date_from:
        dt_from = datetime.fromisoformat(date_from)
        
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    query = {"is_relevant": {"$ne": False}}
    if target_scope:
        query["target_scope"] = {"$in": [target_scope]}
    if dt_from or dt_to:
        query["processed_time"] = {}
        if dt_from:
            query["processed_time"]["$gte"] = dt_from
        if dt_to:
            query["processed_time"]["$lte"] = dt_to

    if limit_articles:
        cursor = repo.collection.find(query, {"_id": 1}).sort("processed_time", -1).limit(limit_articles)
        ids = [doc["_id"] async for doc in cursor]
        query = {"_id": {"$in": ids}}

    top_risks = await repo.get_top_risks(limit=limit, query=query)
    return {"data": top_risks}
