"""
HTML Crawler — Scrapes articles from web pages.
Implements ICrawlerBase interface.
"""

import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.domain.entities.raw_data import RawData
from app.domain.entities.source import Source
from app.domain.interfaces.crawler_service import ICrawlerBase

logger = logging.getLogger(__name__)


class HTMLCrawler(ICrawlerBase):
    """Crawls HTML web pages and extracts article data."""

    def __init__(self):
        self.timeout = 30
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        }

    async def crawl(self, source: Source, keywords: list[str]) -> list[RawData]:
        """
        Scrape a web page for article links, then extract article content.

        Args:
            source: Web source with URL.
            keywords: Keywords to filter relevant articles.

        Returns:
            List of RawData articles found on the page.
        """
        articles = []
        try:
            # Step 1: Fetch the index/listing page
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True,
            ) as client:
                response = await client.get(str(source.url))
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                base_url = str(source.url)
                domain = urlparse(base_url).netloc

                # Step 2: Find article links
                article_links = self._extract_article_links(soup, base_url, keywords)

                # Step 3: Fetch each article (limit to avoid overload)
                for link in article_links[:20]:  # Max 20 articles per crawl
                    try:
                        article = await self._fetch_article(client, link, domain)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error fetching article {link}: {e}")

            logger.info(f"HTML crawled {source.url}: {len(articles)} articles")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error crawling {source.url}: {e}")
        except Exception as e:
            logger.error(f"Error crawling {source.url}: {e}")

        return articles

    def _extract_article_links(
        self, soup: BeautifulSoup, base_url: str, keywords: list[str]
    ) -> list[str]:
        """Extract article links from a listing page, filtered by keywords."""
        links = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)

            # Basic heuristics: filter for article-like URLs
            if not self._is_article_url(full_url, base_url):
                continue

            # Check if link text or surrounding text contains keywords
            link_text = a_tag.get_text(strip=True)
            title_attr = a_tag.get("title", "")
            combined_text = f"{link_text} {title_attr}"

            if keywords:
                if any(kw.lower() in combined_text.lower() for kw in keywords):
                    links.add(full_url)
            else:
                links.add(full_url)

        return list(links)

    def _is_article_url(self, url: str, base_url: str) -> bool:
        """Heuristic check if a URL likely points to an article page."""
        parsed = urlparse(url)
        base_parsed = urlparse(base_url)

        # Must be same domain
        if parsed.netloc != base_parsed.netloc:
            return False

        # Filter out common non-article paths
        path = parsed.path.lower()
        skip_patterns = [
            "/tag/", "/category/", "/author/", "/page/",
            "/login", "/register", "/search", "/contact",
            "/about", "/privacy", "/terms",
            ".css", ".js", ".jpg", ".png", ".gif",
        ]
        if any(pattern in path for pattern in skip_patterns):
            return False

        # Must have meaningful path depth
        path_parts = [p for p in path.split("/") if p]
        if len(path_parts) < 1:
            return False

        return True

    async def _fetch_article(
        self, client: httpx.AsyncClient, url: str, domain: str
    ) -> RawData | None:
        """Fetch and extract content from a single article page."""
        try:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = ""
            title_tag = soup.find("h1")
            if title_tag:
                title = title_tag.get_text(strip=True)
            elif soup.title:
                title = soup.title.get_text(strip=True)

            # Extract article body text
            raw_text = self._extract_body_text(soup)
            if not raw_text or len(raw_text) < 100:
                return None  # Too short, probably not a real article

            # Extract author
            author = self._extract_author(soup)

            # Extract publish time
            publish_time = self._extract_publish_time(soup)

            # Extract images
            image_links = self._extract_images(soup)

            raw = RawData(
                source_url=url,
                domain=domain,
                title=title,
                author_poster=author,
                raw_text=raw_text,
                image_links=image_links,
                publish_time=publish_time,
            )
            raw.compute_hash()
            return raw

        except Exception as e:
            logger.warning(f"Failed to fetch article {url}: {e}")
            return None

    def _extract_body_text(self, soup: BeautifulSoup) -> str:
        """Extract main article body text."""
        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try common article containers
        article_selectors = [
            "article",
            "[class*='article-body']",
            "[class*='article-content']",
            "[class*='post-content']",
            "[class*='entry-content']",
            "[class*='content-detail']",
            "[class*='fck_detail']",
            "[class*='detail-content']",
            ".body-text",
            "#article-body",
        ]

        for selector in article_selectors:
            container = soup.select_one(selector)
            if container:
                text = container.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text

        # Fallback: extract all paragraph text
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20)
        return text

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author name from article page."""
        author_selectors = [
            "[class*='author']",
            "[rel='author']",
            "meta[name='author']",
            "[class*='byline']",
        ]
        for selector in author_selectors:
            el = soup.select_one(selector)
            if el:
                if el.name == "meta":
                    return el.get("content", "")
                return el.get_text(strip=True)
        return ""

    def _extract_publish_time(self, soup: BeautifulSoup) -> datetime | None:
        """Extract publish time from article metadata."""
        time_selectors = [
            "time[datetime]",
            "meta[property='article:published_time']",
            "meta[name='pubdate']",
            "meta[name='publish-date']",
        ]
        for selector in time_selectors:
            el = soup.select_one(selector)
            if el:
                dt_str = el.get("datetime") or el.get("content", "")
                if dt_str:
                    try:
                        # Try ISO format
                        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except ValueError:
                        pass
        return None

    def _extract_images(self, soup: BeautifulSoup) -> list[str]:
        """Extract image URLs from article."""
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src", "")
            if src and src.startswith("http") and "icon" not in src.lower() and "logo" not in src.lower():
                images.append(src)
        return images[:10]  # Limit to 10 images
