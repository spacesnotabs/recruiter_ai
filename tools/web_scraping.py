"""HTTP fetching and plain-text cleanup helpers for public web pages."""

from __future__ import annotations

import html
import logging
import re

from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


class HtmlFetchError(RuntimeError):
    """Raised when a URL cannot be retrieved as an HTML document."""


async def fetch_html(
    url: str,
    *,
    timeout_seconds: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> str:
    """Fetch one public URL and return its HTML text.

    Args:
        url: Public page URL to retrieve.
        timeout_seconds: Total HTTP timeout in seconds.
        user_agent: User-Agent header sent to the remote server.

    Returns:
        Response body text when the response is HTML-like.

    Raises:
        HtmlFetchError: If the request fails, returns an error status, or does
            not appear to contain HTML.
    """
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": user_agent,
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise HtmlFetchError(f"Could not fetch job posting URL: {error}") from error

    content_type = response.headers.get("content-type", "").lower()
    response_text = response.text
    if "html" not in content_type and not response_text.lstrip().startswith("<"):
        raise HtmlFetchError(
            f"URL did not return HTML-like content: {content_type or 'unknown'}"
        )

    logger.info("Fetched HTML from %s", response.url)
    return response_text


def html_to_clean_text(raw_html: str) -> str:
    """Convert raw HTML to clean text by removing tags and normalizing whitespace.

    The function deliberately removes common page chrome and executable content
    before the text is supplied to an LLM. It does not attempt to identify a
    job-description container; that interpretation belongs to the enrichment
    workflow.
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove noisy/non-content elements
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "meta",
            "link",
            "header",
            "footer",
            "nav",
            "form",
        ]
    ):
        tag.decompose()

    # Optional: remove common junk by class/id
    junk_patterns = re.compile(
        r"(cookie|banner|modal|popup|advert|ads|tracking|analytics|footer|header|nav)",
        re.I,
    )

    for tag in soup.find_all(attrs={"class": junk_patterns}):
        tag.decompose()

    for tag in soup.find_all(attrs={"id": junk_patterns}):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = html.unescape(text)

    # Normalize whitespace
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    text = "\n".join(lines)

    # Collapse excessive blank-ish spacing
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text
