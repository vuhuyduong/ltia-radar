"""
domain_mapper — Single source of truth for media outlet domain resolution.

Previously duplicated verbatim in crawl_news.py and repositories.py (Flaw 12).
All callers must import get_friendly_domain from here.
"""

from urllib.parse import urlparse

# Ordered mapping: substring match → friendly outlet name.
# Add new outlets here; never in caller code.
_DOMAIN_MAP: tuple[tuple[str, str], ...] = (
    ("vnexpress", "VnExpress"),
    ("tuoitre", "Tuổi Trẻ"),
    ("thanhnien", "Thanh Niên"),
    ("vietnamnet", "VietnamNet"),
    ("dantri", "Dân trí"),
    ("laodong", "Lao Động"),
    ("vtv", "VTV"),
)


def get_friendly_domain(url: str) -> str:
    """
    Resolve a URL to a human-readable media outlet name.

    Resolution order:
      1. Strip 'www.' prefix from netloc.
      2. Substring-match against known outlet keys (case-insensitive).
      3. Fallback: capitalize the first subdomain segment.

    Args:
        url: Full article URL string.

    Returns:
        Friendly outlet name string, e.g. "VnExpress", "Tuổi Trẻ".
    """
    netloc = urlparse(url).netloc or "Nguồn khác"
    # str.removeprefix is Python 3.9+ — available in Python 3.12 container
    domain_lower = netloc.removeprefix("www.").lower()

    for key, name in _DOMAIN_MAP:
        if key in domain_lower:
            return name

    parts = domain_lower.split(".")
    return parts[0].capitalize() if len(parts) > 1 else domain_lower
