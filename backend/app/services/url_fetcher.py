"""
URL fetcher service.

Fetches publicly accessible URLs and extracts clean text for ingestion.
Supports:
  - Direct PDF/DOCX links   → downloaded and passed to DocumentParser
  - HTML pages              → text extracted via trafilatura
  - Plain text pages        → returned as-is

Only public URLs are supported. Authenticated pages will not work.
"""
import io
import logging
import re
from typing import Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Max download size: 50MB
MAX_BYTES = 50 * 1024 * 1024

# Headers to appear as a normal browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LexQuery/1.0; +https://lexquery.app)",
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
}


class URLFetchError(Exception):
    pass


def _detect_type_from_url(url: str) -> str:
    """Guess content type from URL path."""
    path = urlparse(url).path.lower()
    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith(".docx"):
        return "docx"
    if path.endswith(".txt"):
        return "txt"
    return "html"


def _detect_type_from_headers(content_type: str) -> str:
    """Detect content type from HTTP Content-Type header."""
    ct = content_type.lower()
    if "pdf" in ct:
        return "pdf"
    if "wordprocessingml" in ct or "msword" in ct:
        return "docx"
    if "plain" in ct:
        return "txt"
    return "html"


def _extract_title(url: str, html: str = "") -> str:
    """Extract a readable title from a URL or HTML page."""
    if html:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            title = re.sub(r"\s+", " ", title)
            if title and len(title) < 200:
                return title

    # Fall back to URL path
    path = urlparse(url).path
    name = path.rstrip("/").split("/")[-1]
    if name:
        return name.replace("-", " ").replace("_", " ").strip()
    return urlparse(url).netloc


def fetch_url(url: str) -> Tuple[bytes, str, str]:
    """
    Fetch a URL and return (content_bytes, detected_type, title).

    detected_type is one of: 'pdf', 'docx', 'txt', 'html'

    Raises URLFetchError on failure.
    """
    # Basic URL validation
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise URLFetchError("Only http:// and https:// URLs are supported.")
    if not parsed.netloc:
        raise URLFetchError("Invalid URL — no domain found.")

    logger.info(f"[url-fetch] Fetching {url}")

    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers=HEADERS) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise URLFetchError(
            f"The server returned HTTP {e.response.status_code}. "
            f"Make sure the URL is publicly accessible."
        )
    except httpx.RequestError as e:
        raise URLFetchError(f"Could not reach {url}: {e}")

    content = response.content
    if len(content) > MAX_BYTES:
        raise URLFetchError(f"Document is too large (max 50MB).")

    content_type = response.headers.get("content-type", "")

    # Detect type — headers take priority over URL path
    detected = _detect_type_from_headers(content_type)
    if detected == "html":
        detected = _detect_type_from_url(url)

    # Extract title
    title = ""
    if detected == "html":
        title = _extract_title(url, response.text)
    else:
        title = _extract_title(url)

    if not title:
        title = url

    logger.info(f"[url-fetch] ✓ {url} → type={detected}, size={len(content)} bytes, title={title[:60]}")
    return content, detected, title


def extract_text_from_html(html_bytes: bytes, url: str = "") -> str:
    """
    Extract clean article text from HTML using trafilatura.
    Falls back to basic tag stripping if trafilatura returns nothing.
    """
    try:
        import trafilatura
        text = trafilatura.extract(
            html_bytes.decode("utf-8", errors="replace"),
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            url=url,
        )
        if text and len(text.strip()) > 100:
            return text.strip()
    except Exception as e:
        logger.warning(f"[url-fetch] trafilatura failed: {e}")

    # Basic fallback — strip HTML tags
    text = html_bytes.decode("utf-8", errors="replace")
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
