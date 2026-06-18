"""
Alert Rules API — CRUD endpoints for configuring alert rules (US-1.2).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_alert_rule_repo, get_alert_service
from app.domain.entities.alert_rule import AlertRuleCreate, AlertRuleUpdate
from app.infrastructure.alerting.telegram import TelegramAlertService
from app.infrastructure.database.repositories import AlertRuleRepository

router = APIRouter(prefix="/api/alert-rules", tags=["Alert Rules"])


@router.get("")
async def list_alert_rules(
    skip: int = 0,
    limit: int = 100,
    repo: AlertRuleRepository = Depends(get_alert_rule_repo),
):
    """List all alert rules."""
    rules = await repo.find_all(skip=skip, limit=limit)
    total = await repo.count()
    return {"data": rules, "total": total}


@router.post("", status_code=201)
async def create_alert_rule(
    payload: AlertRuleCreate,
    repo: AlertRuleRepository = Depends(get_alert_rule_repo),
):
    """Create a new alert rule with conditions and Telegram Chat ID (US-1.2 AC#2-3)."""
    result = await repo.create(payload.model_dump())
    return {"data": result, "message": "Alert rule created successfully"}


@router.put("/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    payload: AlertRuleUpdate,
    repo: AlertRuleRepository = Depends(get_alert_rule_repo),
):
    """Update an existing alert rule."""
    existing = await repo.find_by_id(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    update_data = payload.model_dump(exclude_unset=True)
    result = await repo.update(rule_id, update_data)
    return {"data": result, "message": "Alert rule updated successfully"}


@router.delete("/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    repo: AlertRuleRepository = Depends(get_alert_rule_repo),
):
    """Delete an alert rule."""
    existing = await repo.find_by_id(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    await repo.delete(rule_id)
    return {"message": "Alert rule deleted successfully"}


@router.post("/{rule_id}/test")
async def test_alert_rule(
    rule_id: str,
    repo: AlertRuleRepository = Depends(get_alert_rule_repo),
    alert_service: TelegramAlertService = Depends(get_alert_service),
):
    """Send a test alert to verify Telegram configuration (US-1.2 AC#4)."""
    rule = await repo.find_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    chat_id = rule.get("telegram_chat_id", "")
    if not chat_id:
        raise HTTPException(status_code=400, detail="No Telegram Chat ID configured")

    success = await alert_service.send_test_message(chat_id)
    if success:
        return {"message": "Test alert sent successfully"}
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send test alert. Check bot token and chat ID."
        )
