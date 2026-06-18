"""
Keyword entity — Represents a target keyword for crawling and filtering.
Maps to MongoDB collection: keywords
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KeywordCreate(BaseModel):
    """Schema for creating a new keyword."""
    value: str = Field(..., min_length=1, max_length=200)
    is_active: bool = True


class KeywordUpdate(BaseModel):
    """Schema for updating an existing keyword."""
    value: Optional[str] = Field(default=None, min_length=1, max_length=200)
    is_active: Optional[bool] = None


class Keyword(BaseModel):
    """Full keyword entity as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    value: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
