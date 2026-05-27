"""Fetch and extract job posting details from a public job URL.

The scraper keeps dependencies intentionally small: it uses ``httpx`` for
network requests and BeautifulSoup for HTML and JSON-LD extraction. It first
looks for schema.org ``JobPosting`` structured data, which is usually the
cleanest source, and then falls back to visible page text from likely job
description containers.
"""

from __future__ import annotations

import asyncio
import argparse
import html
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag
import httpx

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)

DESCRIPTION_ATTRIBUTE_MARKERS = (
    "job-description",
    "job_description",
    "jobdescription",
    "description",
    "posting",
    "job-detail",
    "job_detail",
    "jobcontent",
    "job-content",
)

TEXT_BLOCK_TAGS = {
    "article",
    "blockquote",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "p",
    "section",
    "tr",
}


@dataclass(frozen=True)
class JobPostingDetails:
    """Structured details extracted from a job posting URL.

    Attributes mirror common schema.org ``JobPosting`` fields. Fields are
    ``None`` when the source page does not expose that value. The
    ``raw_structured_data`` field preserves the parsed JSON-LD object used for
    extraction so callers can inspect source-specific fields without changing
    this public model.
    """

    url: str
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    description: str | None = None
    employment_type: str | None = None
    date_posted: str | None = None
    valid_through: str | None = None
    salary: str | None = None
    raw_structured_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the extracted job details as a plain dictionary."""
        return asdict(self)


class JobPostingExtractionError(RuntimeError):
    """Raised when a job posting URL cannot be fetched or parsed."""


async def fetch_job_posting(
    url: str,
    *,
    timeout_seconds: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> JobPostingDetails:
    """Fetch a job posting URL and extract job details from the response.

    The function performs one HTTP GET request. It raises
    ``JobPostingExtractionError`` for network failures, non-success HTTP status
    codes, and responses that are not usable as HTML. It does not execute
    JavaScript; callers should use a browser-backed scraper for pages that hide
    all job content behind client-side rendering.
    """
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": user_agent,
    }
    logger.info(f"Fetching job posting: {url=}, {timeout_seconds=}, {user_agent=}")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise JobPostingExtractionError(f"Could not fetch job posting URL: {error}") from error

    content_type = response.headers.get("content-type", "")
    if "html" not in content_type and response.text.lstrip()[:1] not in {"<", "{"}:
        raise JobPostingExtractionError(f"URL did not return HTML-like content: {content_type or 'unknown'}")

    return extract_job_posting_from_html(response.text, str(response.url))


def fetch_job_posting_sync(
    url: str,
    *,
    timeout_seconds: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> JobPostingDetails:
    """Synchronously fetch and extract a job posting URL.

    This wrapper is convenient for one-off scripts and command-line usage. Async
    application code should call ``fetch_job_posting`` directly to avoid nested
    event-loop issues.
    """
    logger.info(f"Fetching job posting: {url=}, {timeout_seconds=}, {user_agent=}")
    return asyncio.run(fetch_job_posting(url, timeout_seconds=timeout_seconds, user_agent=user_agent))


def extract_job_posting_from_html(html_text: str, url: str) -> JobPostingDetails:
    """Extract job posting details from an HTML document string.

    JSON-LD ``JobPosting`` data is preferred because it carries explicit field
    names. If no structured posting is present, the fallback parser returns the
    document title and the most likely visible description text block.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    title = _page_title(soup)

    structured_posting = _find_job_posting_json_ld(_json_ld_blocks(soup))
    if structured_posting:
        return _details_from_structured_posting(structured_posting, url, title)

    return JobPostingDetails(
        url=url,
        title=title,
        description=_best_description_text(soup),
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for fetching one job posting URL."""
    parser = argparse.ArgumentParser(description="Extract job description details from a job posting URL.")
    parser.add_argument("url", help="Public job posting URL to fetch.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="HTTP timeout in seconds. Defaults to 20.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the job posting scraper CLI and return a process exit code."""
    args = parse_args()
    try:
        details = fetch_job_posting_sync(args.url, timeout_seconds=args.timeout)
    except JobPostingExtractionError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(json.dumps(details.to_dict(), indent=2))
    return 0


def _details_from_structured_posting(
    posting: dict[str, Any],
    url: str,
    title_fallback: str | None,
) -> JobPostingDetails:
    """Build ``JobPostingDetails`` from parsed schema.org data."""
    return JobPostingDetails(
        url=url,
        title=_string_or_none(posting.get("title")) or title_fallback,
        company_name=_organization_name(posting.get("hiringOrganization")),
        location=_job_location(posting.get("jobLocation") or posting.get("applicantLocationRequirements")),
        description=_html_to_text(_string_or_none(posting.get("description"))),
        employment_type=_join_values(posting.get("employmentType")),
        date_posted=_string_or_none(posting.get("datePosted")),
        valid_through=_string_or_none(posting.get("validThrough")),
        salary=_salary_text(posting.get("baseSalary") or posting.get("estimatedSalary")),
        raw_structured_data=posting,
    )


def _find_job_posting_json_ld(json_ld_blocks: Iterable[str]) -> dict[str, Any] | None:
    """Return the first schema.org JobPosting object from JSON-LD blocks."""
    for block in json_ld_blocks:
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue

        for item in _walk_json_ld(parsed):
            if isinstance(item, dict) and _json_type_matches(item.get("@type"), "JobPosting"):
                return item

    return None


def _walk_json_ld(value: Any) -> Iterable[Any]:
    """Yield JSON-LD objects, including nested graph entries."""
    if isinstance(value, list):
        for item in value:
            yield from _walk_json_ld(item)
        return

    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph is not None:
            yield from _walk_json_ld(graph)


def _json_type_matches(value: Any, expected_type: str) -> bool:
    """Return whether a JSON-LD ``@type`` value contains the expected type."""
    if isinstance(value, str):
        return value.lower() == expected_type.lower()
    if isinstance(value, list):
        return any(_json_type_matches(item, expected_type) for item in value)
    return False


def _organization_name(value: Any) -> str | None:
    """Extract a human-readable organization name from schema.org data."""
    if isinstance(value, dict):
        return _string_or_none(value.get("name"))
    return _string_or_none(value)


def _job_location(value: Any) -> str | None:
    """Extract a display location from schema.org job location data."""
    if isinstance(value, list):
        return _join_values(_job_location(item) for item in value)

    if not isinstance(value, dict):
        return _string_or_none(value)

    address = value.get("address")
    if isinstance(address, dict):
        parts = [
            address.get("streetAddress"),
            address.get("addressLocality"),
            address.get("addressRegion"),
            address.get("postalCode"),
            address.get("addressCountry"),
        ]
        return _join_values(parts)

    return _string_or_none(value.get("name")) or _string_or_none(address)


def _salary_text(value: Any) -> str | None:
    """Extract a compact salary string from schema.org salary data."""
    if isinstance(value, list):
        return _join_values(_salary_text(item) for item in value)

    if not isinstance(value, dict):
        return _string_or_none(value)

    currency = _string_or_none(value.get("currency"))
    amount = value.get("value")
    if isinstance(amount, dict):
        min_value = _string_or_none(amount.get("minValue"))
        max_value = _string_or_none(amount.get("maxValue"))
        unit = _string_or_none(amount.get("unitText"))
        if min_value and max_value:
            salary = f"{min_value}-{max_value}"
        else:
            salary = min_value or max_value or _string_or_none(amount.get("value"))
        return _join_values([currency, salary, unit], separator=" ")

    return _join_values([currency, _string_or_none(amount)], separator=" ")


def _join_values(values: Any, *, separator: str = ", ") -> str | None:
    """Join non-empty scalar values into one display string."""
    if isinstance(values, str):
        return _clean_text(values)
    if values is None:
        return None

    cleaned_values = [
        cleaned
        for cleaned in (_clean_text(str(value)) for value in values if value is not None)
        if cleaned
    ]
    return separator.join(cleaned_values) if cleaned_values else None


def _string_or_none(value: Any) -> str | None:
    """Return a stripped string for scalar values or ``None`` otherwise."""
    if value is None or isinstance(value, (dict, list)):
        return None
    return _clean_text(str(value))


def _json_ld_blocks(soup: BeautifulSoup) -> list[str]:
    """Return raw JSON-LD script contents from an HTML document."""
    blocks: list[str] = []
    for script in soup.find_all("script"):
        script_type = " ".join(script.get_attribute_list("type")).lower()
        if "ld+json" not in script_type:
            continue

        block = script.string or script.get_text()
        if block and block.strip():
            blocks.append(block.strip())

    return blocks


def _page_title(soup: BeautifulSoup) -> str | None:
    """Return the best display title from a page H1 or document title."""
    heading = soup.find("h1")
    if isinstance(heading, Tag):
        heading_text = _tag_text(heading)
        if heading_text:
            return heading_text

    if soup.title:
        return _clean_text(soup.title.get_text(" ", strip=True))

    return None


def _best_description_text(soup: BeautifulSoup) -> str | None:
    """Return the longest useful text from likely job description containers."""
    candidates = [
        text
        for tag in soup.find_all(_is_likely_description_container)
        if isinstance(tag, Tag)
        for text in [_tag_text(tag)]
        if text and len(text) >= 120
    ]
    return max(candidates, key=len) if candidates else None


def _is_likely_description_container(tag: Tag) -> bool:
    """Return whether an element looks like a job description container."""
    if tag.name not in {"main", "article", "section", "div"}:
        return False

    haystack = " ".join(
        _attribute_values(tag.get(name))
        for name in ("id", "class", "data-testid", "data-test", "aria-label", "itemprop")
    ).lower()
    return any(marker in haystack for marker in DESCRIPTION_ATTRIBUTE_MARKERS)


def _attribute_values(value: Any) -> str:
    """Return one searchable string from a BeautifulSoup attribute value."""
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _html_to_text(value: str | None) -> str | None:
    """Convert an HTML fragment to readable plain text."""
    if not value:
        return None

    soup = BeautifulSoup(value, "html.parser")
    return _tag_text(soup) or _clean_text(html.unescape(value))


def _tag_text(tag: BeautifulSoup | Tag) -> str | None:
    """Return readable text from a BeautifulSoup node."""
    return _clean_text(" ".join(_visible_text_parts(tag)))


def _visible_text_parts(node: PageElement) -> Iterable[str]:
    """Yield visible text with explicit breaks around block-level elements."""
    if isinstance(node, NavigableString):
        yield str(node)
        return

    if not isinstance(node, Tag) and not isinstance(node, BeautifulSoup):
        return

    if isinstance(node, Tag):
        if node.name in {"script", "style", "noscript"}:
            return
        if node.name == "br":
            yield "\n"
            return
        if node.name in TEXT_BLOCK_TAGS:
            yield "\n"

    for child in node.children:
        yield from _visible_text_parts(child)

    if isinstance(node, Tag) and node.name in TEXT_BLOCK_TAGS:
        yield "\n"


def _clean_text(value: str | None) -> str | None:
    """Normalize whitespace in extracted text while preserving paragraph breaks."""
    if value is None:
        return None

    normalized = html.unescape(value).replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip() or None


if __name__ == "__main__":
    raise SystemExit(main())
