"""
LLM Configuration entity — Represents a configured LLM model and its API key.
Maps to MongoDB collection: llm_configs
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LLMConfigCreate(BaseModel):
    """Schema for creating a new LLM configuration / API key."""
    provider: str = Field(..., min_length=1, max_length=100) # e.g. "Google Gemini", "OpenAI"
    model_name: str = Field(..., min_length=1, max_length=100) # e.g. "gemini-3.5-flash", "gpt-4o"
    api_key: str = Field(..., min_length=1)
    is_active: bool = True
    is_default: bool = False
    description: Optional[str] = ""


class LLMConfigUpdate(BaseModel):
    """Schema for updating an existing LLM configuration / API key."""
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    description: Optional[str] = None


class LLMConfig(BaseModel):
    """Full LLM Config entity as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    provider: str
    model_name: str
    api_key: str
    is_active: bool = True
    is_default: bool = False
    description: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
