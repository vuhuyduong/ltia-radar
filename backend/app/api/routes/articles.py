"""
Articles API — Endpoints for listing and searching processed articles.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_processed_data_repo, get_raw_data_repo
from app.infrastructure.database.repositories import (
    ProcessedDataRepository,
    RawDataRepository,
)

router = APIRouter(prefix="/api/articles", tags=["Articles"])


@router.get("")
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sentiment: Optional[str] = Query(None, description="POSITIVE, NEGATIVE, NEUTRAL"),
    impact_level: Optional[str] = Query(None, description="CRITICAL, HIGH, MEDIUM, LOW"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in title and summary"),
    date_from: Optional[str] = Query(None, description="ISO date string"),
    date_to: Optional[str] = Query(None, description="ISO date string"),
    repo: ProcessedDataRepository = Depends(get_processed_data_repo),
):
    """List processed articles with optional filters."""
    # Parse dates
    dt_from = datetime.fromisoformat(date_from) if date_from else None
    dt_to = datetime.fromisoformat(date_to) if date_to else None

    articles = await repo.find_all(
        skip=skip,
        limit=limit,
        sentiment=sentiment,
        impact_level=impact_level,
        category=category,
        search=search,
        date_from=dt_from,
        date_to=dt_to,
    )
    total = await repo.count()
    return {"data": articles, "total": total}


@router.get("/{article_id}")
async def get_article_detail(
    article_id: str,
    processed_repo: ProcessedDataRepository = Depends(get_processed_data_repo),
    raw_repo: RawDataRepository = Depends(get_raw_data_repo),
):
    """Get full article detail including raw data and AI analysis."""
    processed = await processed_repo.find_by_id(article_id)
    if not processed:
        raise HTTPException(status_code=404, detail="Article not found")

    # Get raw data
    raw_data = None
    if processed.get("raw_data_id"):
        raw_data = await raw_repo.find_by_id(processed["raw_data_id"])

    return {
        "processed": processed,
        "raw_data": raw_data,
    }
