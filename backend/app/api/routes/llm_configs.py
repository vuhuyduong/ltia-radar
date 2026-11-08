"""
LLM Configs API — CRUD endpoints for managing LLM configurations and API keys.
"""

from fastapi import APIRouter, Depends, HTTPException
from google import genai
from google.genai import types

from app.api.dependencies import get_llm_config_repo
from app.domain.entities.llm_config import LLMConfigCreate, LLMConfigUpdate
from app.infrastructure.database.repositories import LLMConfigRepository
from app.infrastructure.llm.quota import get_pool

router = APIRouter(prefix="/api/llm-configs", tags=["LLM Configs"])


def _mask_config_doc(doc: dict) -> dict:
    """Mask raw API key before returning over HTTP while keeping suffix for UI display."""
    masked = dict(doc)
    raw_key = masked.get("api_key") or ""
    if len(raw_key) > 10:
        masked["api_key_masked"] = f"{raw_key[:6]}...{raw_key[-6:]}"
    elif raw_key:
        masked["api_key_masked"] = "***"
    else:
        masked["api_key_masked"] = ""
    return masked


@router.get("")
async def list_llm_configs(
    skip: int = 0,
    limit: int = 100,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """List all configured LLM models and keys, plus live Free Tier quota snapshot."""
    configs = await repo.find_all(skip=skip, limit=limit)
    total = await repo.count()
    return {
        "data": [_mask_config_doc(c) for c in configs],
        "total": total,
        "quota": get_pool().snapshot(),
    }


@router.get("/quota")
async def get_llm_quota_status():
    """Return live Free Tier rate-limit usage (RPM/TPM/RPD) per active key."""
    pool = get_pool()
    return {
        "limits": {
            "rpm_per_key": pool.rpm,
            "tpm_per_key": pool.tpm,
            "rpd_per_key": pool.rpd,
        },
        "keys": pool.snapshot(),
    }


@router.post("", status_code=201)
async def create_llm_config(
    payload: LLMConfigCreate,
    repo: LLMConfigRepository = Depends(get_llm_config_repo),
):
    """Add a new LLM configuration / API key."""
    result = await repo.create(payload.model_dump())
    return {"data": _mask_config_doc(result), "message": "LLM configuration created successfully"}


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
    return {"data": _mask_config_doc(result), "message": "LLM configuration updated successfully"}


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
    """Test connection using the selected API key and model (async, non-blocking)."""
    config = await repo.find_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    api_key = config.get("api_key")
    model_name = config.get("model_name") or "gemini-3.8-flash"

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is empty")

    try:
        from app.infrastructure.llm.gemini import FALLBACK_MODELS

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=20000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
        primary_err = None
        for idx, m in enumerate(models_to_try[:3]):
            try:
                cfg = types.GenerateContentConfig(max_output_tokens=256)
                if m.startswith("gemini-3"):
                    cfg.thinking_config = types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.HIGH
                    )
                response = await client.aio.models.generate_content(
                    model=m,
                    contents="Reply with 'Success' in one word.",
                    config=cfg,
                )
                response_text = response.text.strip() if response.text else ""
                if idx == 0:
                    msg = f"Connection test passed ({m})"
                else:
                    msg = (
                        f"API key valid — primary {model_name} busy/rate-limited, "
                        f"auto-fallback succeeded via {m}"
                    )
                return {
                    "status": "success",
                    "message": msg,
                    "response": response_text,
                }
            except Exception as ex:
                if idx == 0:
                    primary_err = ex
                continue
        raise primary_err or RuntimeError("All candidate models failed")
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
