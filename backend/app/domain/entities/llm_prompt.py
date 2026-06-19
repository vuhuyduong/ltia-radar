"""
LLMPrompt entity — Represents a customizable prompt configuration for LLM analysis.
Maps to MongoDB collection: llm_prompts
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LLMPromptCreate(BaseModel):
    """Schema for creating a new LLM prompt configuration."""
    name: str = Field(..., min_length=1, max_length=200)
    system_prompt: str = Field(..., min_length=1)
    batch_system_prompt: str = Field(..., min_length=1)
    is_active: bool = False


class LLMPromptUpdate(BaseModel):
    """Schema for updating an existing LLM prompt configuration."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    system_prompt: Optional[str] = None
    batch_system_prompt: Optional[str] = None
    is_active: Optional[bool] = None


class LLMPrompt(BaseModel):
    """Full LLM Prompt entity as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    system_prompt: str
    batch_system_prompt: str
    is_active: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
