"""
RawData entity — Represents raw crawled article data before AI processing.
Maps to MongoDB collection: raw_data
"""

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RawData(BaseModel):
    """Raw crawled article data as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    source_url: str  # Unique index
    url_hash: str = ""  # SHA256 hash of source_url for dedup
    domain: str = ""
    title: str = ""
    author_poster: str = ""
    raw_text: str = ""
    image_links: list[str] = Field(default_factory=list)
    publish_time: Optional[datetime] = None
    crawl_time: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True}

    def compute_hash(self) -> str:
        """Generate SHA256 hash from source_url for dedup (US-2.2)."""
        self.url_hash = hashlib.sha256(self.source_url.encode()).hexdigest()
        return self.url_hash
