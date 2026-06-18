"""
Source entity — Represents a news source (RSS feed or website) to crawl.
Maps to MongoDB collection: sources
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    RSS = "RSS"
    WEB = "WEB"


class SourceCreate(BaseModel):
    """Schema for creating a new source."""
    url: HttpUrl
    name: str = Field(..., min_length=1, max_length=200)
    source_type: SourceType = SourceType.WEB
    is_active: bool = True


class SourceUpdate(BaseModel):
    """Schema for updating an existing source."""
    url: Optional[HttpUrl] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    source_type: Optional[SourceType] = None
    is_active: Optional[bool] = None


class Source(BaseModel):
    """Full source entity as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    url: str
    name: str
    source_type: SourceType = SourceType.WEB
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
