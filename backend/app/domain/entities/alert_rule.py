"""
AlertRule entity — Configurable rules for Telegram alerting.
Maps to MongoDB collection: alert_rules
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    """Schema for creating a new alert rule."""
    rule_name: str = Field(..., min_length=1, max_length=200)
    condition_query: dict = Field(
        ...,
        description="JSON condition, e.g. {'impact_level': 'CRITICAL', 'sentiment': 'NEGATIVE'}"
    )
    telegram_chat_id: str = Field(..., min_length=1)
    is_active: bool = True


class AlertRuleUpdate(BaseModel):
    """Schema for updating an existing alert rule."""
    rule_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    condition_query: Optional[dict] = None
    telegram_chat_id: Optional[str] = None
    is_active: Optional[bool] = None


class AlertRule(BaseModel):
    """Full alert rule entity as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    rule_name: str
    condition_query: dict = Field(default_factory=dict)
    telegram_chat_id: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
