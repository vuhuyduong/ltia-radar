"""
RSS Crawler — Fetches articles from RSS feeds.
Implements ICrawlerBase interface.
"""

import logging
from datetime import datetime
from urllib.parse import urlparse

import feedparser
import httpx

from app.domain.entities.raw_data import RawData
from app.domain.entities.source import Source
from app.domain.interfaces.crawler_service import ICrawlerBase

logger = logging.getLogger(__name__)


class RSSCrawler(ICrawlerBase):
    """Crawls RSS feeds and extracts article data."""

    def __init__(self):
        self.timeout = 30

    async def crawl(self, source: Source, keywords: list[str]) -> list[RawData]:
        """
        Fetch and parse an RSS feed, filtering by keywords.

        Args:
            source: RSS source with URL.
            keywords: Keywords to filter relevant articles.

        Returns:
            List of RawData articles found in the feed.
        """
        articles = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    str(source.url),
                    headers={"User-Agent": "LTIA-Radar/1.0"},
                    follow_redirects=True,
                )
                response.raise_for_status()

            feed = feedparser.parse(response.text)

            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                content = ""

                # Try to get full content
                if hasattr(entry, "content") and entry.content:
                    content = entry.content[0].get("value", "")

                full_text = f"{title} {summary} {content}"

                # Filter by keywords (case-insensitive)
                if keywords and not any(
                    kw.lower() in full_text.lower() for kw in keywords
                ):
                    continue

                # Parse publish time
                publish_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        publish_time = datetime(*entry.published_parsed[:6])
                    except (ValueError, TypeError):
                        publish_time = datetime.utcnow()

                # Extract domain
                domain = urlparse(link).netloc if link else urlparse(str(source.url)).netloc

                # Extract images from content
                image_links = self._extract_images(content or summary)

                raw = RawData(
                    source_url=link,
                    domain=domain,
                    title=title,
                    author_poster=entry.get("author", ""),
                    raw_text=content or summary,
                    image_links=image_links,
                    publish_time=publish_time,
                )
                raw.compute_hash()
                articles.append(raw)

            logger.info(f"RSS crawled {source.url}: {len(articles)} relevant articles")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error crawling RSS {source.url}: {e}")
        except Exception as e:
            logger.error(f"Error crawling RSS {source.url}: {e}")

        return articles

    def _extract_images(self, html_content: str) -> list[str]:
        """Extract image URLs from HTML content."""
        from bs4 import BeautifulSoup

        images = []
        if html_content:
            try:
                soup = BeautifulSoup(html_content, "html.parser")
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    if src and src.startswith("http"):
                        images.append(src)
            except Exception:
                pass
        return images
