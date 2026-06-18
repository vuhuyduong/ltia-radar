"""
Sources API — CRUD endpoints for managing news sources (US-1.1).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_source_repo
from app.domain.entities.source import SourceCreate, SourceUpdate
from app.infrastructure.database.repositories import SourceRepository

router = APIRouter(prefix="/api/sources", tags=["Sources"])


@router.get("")
async def list_sources(
    skip: int = 0,
    limit: int = 100,
    repo: SourceRepository = Depends(get_source_repo),
):
    """List all configured news sources."""
    sources = await repo.find_all(skip=skip, limit=limit)
    total = await repo.count()
    return {"data": sources, "total": total}


@router.post("", status_code=201)
async def create_source(
    payload: SourceCreate,
    repo: SourceRepository = Depends(get_source_repo),
):
    """Add a new news source. URL is validated automatically (US-1.1 AC#2)."""
    data = payload.model_dump()
    data["url"] = str(data["url"])  # Convert HttpUrl to string
    result = await repo.create(data)
    return {"data": result, "message": "Source created successfully"}


@router.put("/{source_id}")
async def update_source(
    source_id: str,
    payload: SourceUpdate,
    repo: SourceRepository = Depends(get_source_repo),
):
    """Update an existing source."""
    existing = await repo.find_by_id(source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "url" in update_data and update_data["url"] is not None:
        update_data["url"] = str(update_data["url"])

    result = await repo.update(source_id, update_data)
    return {"data": result, "message": "Source updated successfully"}


@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    repo: SourceRepository = Depends(get_source_repo),
):
    """Delete a source."""
    existing = await repo.find_by_id(source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")

    await repo.delete(source_id)
    return {"message": "Source deleted successfully"}
