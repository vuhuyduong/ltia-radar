"""
ProcessedData entity — AI-analyzed article data from Gemini LLM.
Maps to MongoDB collection: processed_data
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class ImpactLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class KeyEntity(BaseModel):
    """An extracted key entity (organization, person, agency)."""
    name: str
    type: str = "unknown"  # organization, person, agency, contractor


class ProcessedData(BaseModel):
    """AI-processed article data as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    raw_data_id: str  # Reference to RawData._id
    source_url: str = ""
    title: str = ""
    category: list[str] = Field(default_factory=list)
    sentiment: Sentiment = Sentiment.NEUTRAL
    target_scope: list[str] = Field(default_factory=list)
    impact_level: ImpactLevel = ImpactLevel.LOW
    key_entities: list[KeyEntity] = Field(default_factory=list)
    executive_summary: str = ""
    is_rumor: bool = False
    processed_time: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}
