"""
LLM Configs API — CRUD endpoints for managing LLM configurations and API keys.
"""

from fastapi import APIRouter, Depends, HTTPException
from google import genai

from app.api.dependencies import get_llm_config_repo
from app.domain.entities.llm_config import LLMConfigCreate, LLMConfigUpdate
from app.infrastructure.database.repositories import LLMConfigRepository

router = APIRouter(prefix="/api/llm-configs", tags=["LLM Configs"])


@router.get("")
async def list_llm_configs(
    skip: int = 0,
    limit: int = 100,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """List all configured LLM models and keys."""
    configs = await repo.find_all(skip=skip, limit=limit)
    total = await repo.count()
    return {"data": configs, "total": total}


@router.post("", status_code=201)
async def create_llm_config(
    payload: LLMConfigCreate,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """Add a new LLM configuration / API key."""
    # If is_default is true, ensure we don't have multiple defaults
    result = await repo.create(payload.model_dump())
    return {"data": result, "message": "LLM configuration created successfully"}


@router.put("/{config_id}")
async def update_llm_config(
    config_id: str,
    payload: LLMConfigUpdate,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """Update an existing LLM configuration."""
    existing = await repo.find_by_id(config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Configuration not found")

    update_data = payload.model_dump(exclude_unset=True)
    result = await repo.update(config_id, update_data)
    return {"data": result, "message": "LLM configuration updated successfully"}


@router.delete("/{config_id}")
async def delete_llm_config(
    config_id: str,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """Delete an LLM configuration."""
    existing = await repo.find_by_id(config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Configuration not found")

    await repo.delete(config_id)
    return {"message": "LLM configuration deleted successfully"}


@router.post("/{config_id}/test")
async def test_llm_config(
    config_id: str,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """Test connection using the selected API key and model."""
    config = await repo.find_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    api_key = config.get("api_key")
    model_name = config.get("model_name")

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is empty")

    try:
        # Test request using the model
        client = genai.Client(api_key=api_key)
        # Simple generation call to test access
        response = client.models.generate_content(
            model=model_name,
            contents="Hello, respond with 'Success' in one word.",
        )
        response_text = response.text.strip() if response.text else ""
        return {
            "status": "success",
            "message": "Connection test passed successfully",
            "response": response_text,
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Connection test failed: {str(e)}",
        }


@router.post("/{config_id}/set-default")
async def set_default_model(
    config_id: str,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """Set the model of this configuration as the default model."""
    config = await repo.find_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    model_name = config.get("model_name")
    await repo.set_default_model(model_name)
    return {"message": f"Model '{model_name}' set as the default model"}
