"""
General Settings & PIN Authentication API
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.dependencies import get_general_settings_repo
from app.infrastructure.database.repositories import GeneralSettingsRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["General Settings"])


class VerifyPinPayload(BaseModel):
    pin: str
    type: str  # "user" or "admin"


@router.get("/general")
async def get_general_settings(
    include_pins: bool = Query(False, description="Only true when fetched from verified admin UI"),
    repo: GeneralSettingsRepository = Depends(get_general_settings_repo),
):
    """Fetch general application settings. Never leak PIN codes on public calls."""
    if include_pins:
        return await repo.get_settings()
    return await repo.get_public_settings()


@router.post("/general")
async def update_general_settings(
    payload: dict,
    repo: GeneralSettingsRepository = Depends(get_general_settings_repo),
):
    """Update general settings."""
    settings = await repo.update_settings(payload)
    return settings


@router.post("/verify-pin")
async def verify_pin(
    payload: VerifyPinPayload,
    repo: GeneralSettingsRepository = Depends(get_general_settings_repo),
):
    """Verify access PIN for user or admin gates."""
    config = await repo.get_settings()

    # Verify Admin PIN
    if payload.type == "admin":
        expected_admin_pin = config.get("admin_pin_code", "LT2026")
        if payload.pin == expected_admin_pin:
            return {"success": True}
        return {"success": False, "message": "Mã PIN Admin không chính xác."}

    # Verify User (homepage) PIN
    if not config.get("pin_enabled", True):
        return {"success": True}

    expected_pin = config.get("pin_code", "2026")
    if payload.pin == expected_pin:
        return {"success": True}

    return {"success": False, "message": "Mã PIN truy cập không chính xác."}
