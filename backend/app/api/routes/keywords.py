"""
Keywords API — CRUD endpoints for managing target keywords (US-1.1).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_keyword_repo
from app.domain.entities.keyword import KeywordCreate, KeywordUpdate
from app.infrastructure.database.repositories import KeywordRepository

router = APIRouter(prefix="/api/keywords", tags=["Keywords"])


@router.get("")
async def list_keywords(
    skip: int = 0,
    limit: int = 100,
    repo: KeywordRepository = Depends(get_keyword_repo),
):
    """List all configured keywords."""
    keywords = await repo.find_all(skip=skip, limit=limit)
    total = await repo.count()
    return {"data": keywords, "total": total}


@router.post("", status_code=201)
async def create_keyword(
    payload: KeywordCreate,
    repo: KeywordRepository = Depends(get_keyword_repo),
):
    """Add a new target keyword."""
    result = await repo.create(payload.model_dump())
    return {"data": result, "message": "Keyword created successfully"}


@router.put("/{keyword_id}")
async def update_keyword(
    keyword_id: str,
    payload: KeywordUpdate,
    repo: KeywordRepository = Depends(get_keyword_repo),
):
    """Update an existing keyword."""
    existing = await repo.find_by_id(keyword_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")

    update_data = payload.model_dump(exclude_unset=True)
    result = await repo.update(keyword_id, update_data)
    return {"data": result, "message": "Keyword updated successfully"}


@router.delete("/{keyword_id}")
async def delete_keyword(
    keyword_id: str,
    repo: KeywordRepository = Depends(get_keyword_repo),
):
    """Delete a keyword."""
    existing = await repo.find_by_id(keyword_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Keyword not found")

    await repo.delete(keyword_id)
    return {"message": "Keyword deleted successfully"}
