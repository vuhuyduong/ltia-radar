"""
ProcessedData entity — AI-analyzed article data from Gemini LLM.
Maps to MongoDB collection: processed_data
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class ImpactLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ArticleCitation(BaseModel):
    """Represents a citation/source of the same news article from different media outlet."""
    title: str
    source_url: str
    domain: str
    publish_time: Optional[datetime] = None


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
    is_relevant: bool = True
    processed_time: datetime = Field(default_factory=datetime.utcnow)
    publish_time: Optional[datetime] = None
    citations: list[ArticleCitation] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @field_validator("category", "target_scope", mode="before")
    @classmethod
    def ensure_list(cls, v: any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if isinstance(v, list):
            return v
        return []

    @model_validator(mode="after")
    def filter_citations(self) -> "ProcessedData":
        if self.citations:
            from app.domain.utils.citation_filter import filter_outlier_citations
            self.citations = filter_outlier_citations(
                citations=self.citations,
                ref_time=self.publish_time,
                primary_source_url=self.source_url,
            )
        return self

