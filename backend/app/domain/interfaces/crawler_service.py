"""
ICrawlerBase — Abstract interface for data crawlers.
Following Clean Architecture (PRD Section 9.2).
"""

from abc import ABC, abstractmethod

from app.domain.entities.raw_data import RawData
from app.domain.entities.source import Source


class ICrawlerBase(ABC):
    """
    Base crawler interface.
    Concrete implementations (NewsCrawler, ForumCrawler, FacebookCrawler)
    live in the Infrastructure Layer.
    """

    @abstractmethod
    async def crawl(
        self, source: Source, keywords: list[str]
    ) -> list[RawData]:
        """
        Crawl a source and return list of raw article data.

        Args:
            source: The source to crawl (URL, type, etc.)
            keywords: List of keywords to filter relevant articles.

        Returns:
            List of RawData entities extracted from the source.
        """
        pass
