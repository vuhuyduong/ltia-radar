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

                # Clean HTML elements (e.g. related articles list) from RSS summaries/contents
                clean_summary = self._clean_rss_html(summary)
                clean_content = self._clean_rss_html(content)

                full_text = f"{title} {clean_summary} {clean_content}"

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

                # Extract images from content (needs raw HTML)
                image_links = self._extract_images(content or summary)

                raw = RawData(
                    source_url=link,
                    domain=domain,
                    title=title,
                    author_poster=entry.get("author", ""),
                    raw_text=clean_content or clean_summary,
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

    def _clean_rss_html(self, html_content: str) -> str:
        """Parse RSS HTML content, remove related news/lists, and return clean text."""
        if not html_content:
            return ""
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Decompose common related news list tags (ul, ol, table) in feeds
            for tag in soup.find_all(["ul", "ol", "table"]):
                tag.decompose()
                
            # Decompose divs/paragraphs with classes/styles indicating related news
            for tag in soup.find_all(True):
                if not tag.name or not hasattr(tag, "attrs") or tag.attrs is None:
                    continue
                classes = [str(c).lower() for c in tag.get("class", [])] if tag.get("class") else []
                tag_style = str(tag.get("style", "")).lower()
                
                is_unwanted = False
                for cls in classes:
                    if any(w in cls for w in ["related", "lien-quan", "recommend", "box-tin", "cung-chuyen-muc"]):
                        is_unwanted = True
                        break
                if not is_unwanted and any(w in tag_style for w in ["clear: both", "clear:both"]):
                    is_unwanted = True
                    
                if is_unwanted:
                    tag.decompose()
                    continue
                    
                # Decompose inline related paragraphs
                if tag.name == "p":
                    txt = tag.get_text(strip=True).lower()
                    if len(txt) < 300 and any(txt.startswith(prefix) for prefix in [
                        "xem thêm:", "xem thêm", "đọc thêm:", "đọc thêm", "tin liên quan:", "tin liên quan"
                    ]):
                        tag.decompose()
                        
            # Get clean text
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            # Fallback to simple HTML tag stripping if bs4 fails
            import re
            clean = re.sub(r"<[^>]*>", " ", html_content)
            return " ".join(clean.split())
