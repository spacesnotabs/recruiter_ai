"""Presentation helpers for Job Data Lake jobs API responses.

The API client returns the upstream JSON unchanged. This module converts that
response into human-readable table or CSV output for local inspection.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping


DEFAULT_TABLE_COLUMNS = (
    "title",
    "company",
    "locations",
    "remote",
    "salary",
    "skills",
    "posted",
    "url",
)
CSV_COLUMNS = (
    "title",
    "company",
    "domain",
    "locations",
    "countries",
    "remote",
    "job_function",
    "seniority",
    "salary_min_usd",
    "salary_max_usd",
    "salary",
    "skills",
    "employment_type",
    "posted",
    "url",
    "job_handle",
)
MAX_TABLE_CELL_WIDTH = 42


@dataclass(frozen=True)
class JobDisplayRow:
    """Normalized display fields for one Job Data Lake job record."""

    title: str
    company: str
    domain: str
    locations: str
    countries: str
    remote: str
    job_function: str
    seniority: str
    salary_min_usd: str
    salary_max_usd: str
    salary: str
    skills: str
    employment_type: str
    posted: str
    url: str
    job_handle: str

    def as_dict(self) -> dict[str, str]:
        """Return the display row as a mapping keyed by output column name."""
        return {
            "title": self.title,
            "company": self.company,
            "domain": self.domain,
            "locations": self.locations,
            "countries": self.countries,
            "remote": self.remote,
            "job_function": self.job_function,
            "seniority": self.seniority,
            "salary_min_usd": self.salary_min_usd,
            "salary_max_usd": self.salary_max_usd,
            "salary": self.salary,
            "skills": self.skills,
            "employment_type": self.employment_type,
            "posted": self.posted,
            "url": self.url,
            "job_handle": self.job_handle,
        }


def build_display_rows(response: Mapping[str, Any]) -> list[JobDisplayRow]:
    """Convert a jobs API response into normalized display rows."""
    jobs = response.get("jobs")
    if not isinstance(jobs, list):
        return []

    rows: list[JobDisplayRow] = []
    for job in jobs:
        if not isinstance(job, Mapping):
            continue

        salary_min = job.get("salary_min_usd")
        salary_max = job.get("salary_max_usd")
        rows.append(
            JobDisplayRow(
                title=_string_value(job.get("title")),
                company=_string_value(job.get("company_name")),
                domain=_string_value(job.get("domain_name")),
                locations=_join_values(job.get("locations")),
                countries=_join_values(job.get("countries")),
                remote=_string_value(job.get("remote_type")),
                job_function=_string_value(job.get("job_function")),
                seniority=_join_values(job.get("seniority")),
                salary_min_usd=_string_value(salary_min),
                salary_max_usd=_string_value(salary_max),
                salary=_format_salary_range(salary_min, salary_max),
                skills=_join_values(job.get("required_skills")),
                employment_type=_string_value(job.get("employment_type")),
                posted=_format_unix_timestamp(job.get("posted_at")),
                url=_string_value(job.get("url")),
                job_handle=_string_value(job.get("job_handle")),
            )
        )

    return rows


def format_jobs_table(response: Mapping[str, Any]) -> str:
    """Render a jobs API response as a plain-text table with a short summary."""
    rows = build_display_rows(response)
    summary = _format_response_summary(response)
    if not rows:
        return f"{summary}\n\nNo jobs found."

    table_rows = [
        {column: _truncate(row.as_dict()[column], MAX_TABLE_CELL_WIDTH) for column in DEFAULT_TABLE_COLUMNS}
        for row in rows
    ]
    widths = {
        column: max(len(column), *(len(row[column]) for row in table_rows))
        for column in DEFAULT_TABLE_COLUMNS
    }

    header = " | ".join(column.ljust(widths[column]) for column in DEFAULT_TABLE_COLUMNS)
    divider = "-+-".join("-" * widths[column] for column in DEFAULT_TABLE_COLUMNS)
    body = [
        " | ".join(row[column].ljust(widths[column]) for column in DEFAULT_TABLE_COLUMNS)
        for row in table_rows
    ]
    return "\n".join([summary, "", header, divider, *body])


def format_jobs_csv(response: Mapping[str, Any]) -> str:
    """Render a jobs API response as CSV text suitable for saving or piping."""
    rows = build_display_rows(response)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_select_columns(row.as_dict(), CSV_COLUMNS) for row in rows)
    return output.getvalue()


def _format_response_summary(response: Mapping[str, Any]) -> str:
    """Build a compact summary line for a documented jobs API response."""
    found = response.get("found")
    page = response.get("page")
    per_page = response.get("per_page")
    stats = response.get("stats") if isinstance(response.get("stats"), Mapping) else {}
    total_jobs = stats.get("total_jobs") if isinstance(stats, Mapping) else None
    new_last_24h = stats.get("new_last_24h") if isinstance(stats, Mapping) else None

    parts = [
        f"found: {_string_value(found) or '0'}",
        f"page: {_string_value(page) or '?'}",
        f"per page: {_string_value(per_page) or '?'}",
    ]
    if total_jobs is not None:
        parts.append(f"total jobs: {_string_value(total_jobs)}")
    if new_last_24h is not None:
        parts.append(f"new last 24h: {_string_value(new_last_24h)}")
    return " | ".join(parts)


def _format_unix_timestamp(value: Any) -> str:
    """Format a Unix timestamp as an ISO calendar date in UTC."""
    if value is None or value == "":
        return ""

    try:
        return datetime.fromtimestamp(int(value), tz=UTC).date().isoformat()
    except (OSError, OverflowError, TypeError, ValueError):
        return _string_value(value)


def _format_salary_range(minimum: Any, maximum: Any) -> str:
    """Format minimum and maximum USD salary values for compact display."""
    minimum_text = _string_value(minimum)
    maximum_text = _string_value(maximum)
    if minimum_text and maximum_text:
        return f"${minimum_text}-${maximum_text}"
    if minimum_text:
        return f"${minimum_text}+"
    if maximum_text:
        return f"up to ${maximum_text}"
    return ""


def _join_values(value: Any) -> str:
    """Join list-like API values into a readable comma-separated string."""
    if isinstance(value, str):
        return value
    if isinstance(value, Iterable) and not isinstance(value, Mapping):
        return ", ".join(_string_value(item) for item in value if _string_value(item))
    return _string_value(value)


def _select_columns(row: Mapping[str, str], columns: Iterable[str]) -> dict[str, str]:
    """Return only the requested columns from a normalized row mapping."""
    return {column: row.get(column, "") for column in columns}


def _string_value(value: Any) -> str:
    """Convert an API value into a stable display string."""
    if value is None:
        return ""
    return str(value)


def _truncate(value: str, max_width: int) -> str:
    """Trim long table cells while preserving enough context for scanning."""
    if len(value) <= max_width:
        return value
    if max_width <= 3:
        return value[:max_width]
    return f"{value[: max_width - 3]}..."

