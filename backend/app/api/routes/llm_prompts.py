"""
LLM Prompts API — CRUD endpoints for managing LLM system prompts.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_llm_prompt_repo
from app.domain.entities.llm_prompt import LLMPromptCreate, LLMPromptUpdate
from app.infrastructure.database.repositories import LLMPromptRepository

router = APIRouter(prefix="/api/llm-prompts", tags=["LLM Prompts"])


@router.get("")
async def list_llm_prompts(
    skip: int = 0,
    limit: int = 100,
    repo: LLMPromptRepository = Depends(get_llm_prompt_repo),
):
    """List all configured LLM prompts."""
    prompts = await repo.find_all(skip=skip, limit=limit)
    total = await repo.count()
    return {"data": prompts, "total": total}


@router.post("", status_code=201)
async def create_llm_prompt(
    payload: LLMPromptCreate,
    repo: LLMPromptRepository = Depends(get_llm_prompt_repo),
):
    """Add a new LLM prompt configuration."""
    result = await repo.create(payload.model_dump())
    return {"data": result, "message": "LLM prompt created successfully"}


@router.put("/{prompt_id}")
async def update_llm_prompt(
    prompt_id: str,
    payload: LLMPromptUpdate,
    repo: LLMPromptRepository = Depends(get_llm_prompt_repo),
):
    """Update an existing LLM prompt configuration."""
    existing = await repo.find_by_id(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    update_data = payload.model_dump(exclude_unset=True)
    result = await repo.update(prompt_id, update_data)
    return {"data": result, "message": "LLM prompt updated successfully"}


@router.delete("/{prompt_id}")
async def delete_llm_prompt(
    prompt_id: str,
    repo: LLMPromptRepository = Depends(get_llm_prompt_repo),
):
    """Delete an LLM prompt configuration."""
    existing = await repo.find_by_id(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    await repo.delete(prompt_id)
    return {"message": "LLM prompt deleted successfully"}


@router.post("/{prompt_id}/set-active")
async def set_active_prompt(
    prompt_id: str,
    repo: LLMPromptRepository = Depends(get_llm_prompt_repo),
):
    """Set this prompt configuration as the active one."""
    existing = await repo.find_by_id(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    await repo.set_active(prompt_id)
    return {"message": f"Prompt '{existing.get('name')}' set as active"}
