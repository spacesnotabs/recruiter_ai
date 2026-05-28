"""Unit tests for Job Data Lake response formatting helpers."""

from __future__ import annotations

import csv
import io

from api.job_response_formatter import (
    CSV_COLUMNS,
    JobDisplayRow,
    _format_response_summary,
    _format_salary_range,
    _format_unix_timestamp,
    _join_values,
    _select_columns,
    _string_value,
    _truncate,
    build_display_rows,
    format_jobs_csv,
    format_jobs_table,
)


def _sample_response() -> dict[str, object]:
    """Return a representative jobs API response for formatter tests."""
    return {
        "found": 1,
        "page": 1,
        "per_page": 10,
        "stats": {"total_jobs": 123, "new_last_24h": 4},
        "jobs": [
            {
                "title": "Backend Engineer",
                "company_name": "ExampleCo",
                "domain_name": "example.test",
                "locations": ["Seattle, WA", "Remote"],
                "countries": ["US"],
                "remote_type": "fully_remote",
                "job_function": "eng",
                "seniority": ["senior", "staff"],
                "salary_min_usd": 120000,
                "salary_max_usd": 150000,
                "required_skills": ["Python", "APIs"],
                "employment_type": "full_time",
                "posted_at": 1_716_249_600,
                "url": "https://example.test/jobs/1",
                "job_handle": "job-1",
            },
            "not-a-job-record",
        ],
    }


def test_job_display_row_as_dict_returns_all_output_fields() -> None:
    """Display rows expose a complete dict keyed by formatter column names."""
    row = JobDisplayRow(
        title="Title",
        company="Company",
        domain="example.test",
        locations="Seattle",
        countries="US",
        remote="hybrid",
        job_function="eng",
        seniority="senior",
        salary_min_usd="100000",
        salary_max_usd="120000",
        salary="$100000-$120000",
        skills="Python",
        employment_type="full_time",
        posted="2024-05-21",
        url="https://example.test",
        job_handle="handle",
    )

    assert row.as_dict() == {
        "title": "Title",
        "company": "Company",
        "domain": "example.test",
        "locations": "Seattle",
        "countries": "US",
        "remote": "hybrid",
        "job_function": "eng",
        "seniority": "senior",
        "salary_min_usd": "100000",
        "salary_max_usd": "120000",
        "salary": "$100000-$120000",
        "skills": "Python",
        "employment_type": "full_time",
        "posted": "2024-05-21",
        "url": "https://example.test",
        "job_handle": "handle",
    }


def test_build_display_rows_normalizes_jobs_and_skips_invalid_records() -> None:
    """API job records are normalized while non-mapping entries are ignored."""
    rows = build_display_rows(_sample_response())

    assert len(rows) == 1
    assert rows[0] == JobDisplayRow(
        title="Backend Engineer",
        company="ExampleCo",
        domain="example.test",
        locations="Seattle, WA, Remote",
        countries="US",
        remote="fully_remote",
        job_function="eng",
        seniority="senior, staff",
        salary_min_usd="120000",
        salary_max_usd="150000",
        salary="$120000-$150000",
        skills="Python, APIs",
        employment_type="full_time",
        posted="2024-05-21",
        url="https://example.test/jobs/1",
        job_handle="job-1",
    )


def test_build_display_rows_returns_empty_list_for_missing_jobs_list() -> None:
    """Malformed responses without a jobs list produce no display rows."""
    assert build_display_rows({"jobs": {"title": "Backend Engineer"}}) == []
    assert build_display_rows({}) == []


def test_format_jobs_table_includes_summary_header_and_job_data() -> None:
    """Table output includes response metadata, columns, and job fields."""
    table = format_jobs_table(_sample_response())

    assert table.startswith(
        "found: 1 | page: 1 | per page: 10 | total jobs: 123 | new last 24h: 4"
    )
    assert "title            | company" in table
    assert "Backend Engineer | ExampleCo" in table
    assert "Python, APIs" in table


def test_format_jobs_table_reports_no_jobs_when_rows_are_empty() -> None:
    """Empty table output keeps the summary and adds a no-results message."""
    table = format_jobs_table({"found": 0, "page": 1, "per_page": 10, "jobs": []})

    assert table == "found: 0 | page: 1 | per page: 10\n\nNo jobs found."


def test_format_jobs_csv_writes_header_and_normalized_rows() -> None:
    """CSV output uses the documented column order and normalized values."""
    csv_text = format_jobs_csv(_sample_response())
    reader = csv.DictReader(io.StringIO(csv_text))

    assert csv_text.splitlines()[0] == ",".join(CSV_COLUMNS)
    assert reader.fieldnames == list(CSV_COLUMNS)
    assert list(reader) == [
        {
            "title": "Backend Engineer",
            "company": "ExampleCo",
            "domain": "example.test",
            "locations": "Seattle, WA, Remote",
            "countries": "US",
            "remote": "fully_remote",
            "job_function": "eng",
            "seniority": "senior, staff",
            "salary_min_usd": "120000",
            "salary_max_usd": "150000",
            "salary": "$120000-$150000",
            "skills": "Python, APIs",
            "employment_type": "full_time",
            "posted": "2024-05-21",
            "url": "https://example.test/jobs/1",
            "job_handle": "job-1",
        }
    ]


def test_format_response_summary_uses_fallbacks_and_optional_stats() -> None:
    """Summary fields fall back cleanly when metadata is absent or malformed."""
    assert _format_response_summary({"stats": "invalid"}) == "found: 0 | page: ? | per page: ?"
    assert _format_response_summary({"found": 2, "page": 3, "per_page": 25}) == (
        "found: 2 | page: 3 | per page: 25"
    )


def test_format_unix_timestamp_returns_utc_date_or_original_text() -> None:
    """Timestamps become UTC dates while invalid values remain readable."""
    assert _format_unix_timestamp(1_716_249_600) == "2024-05-21"
    assert _format_unix_timestamp(None) == ""
    assert _format_unix_timestamp("") == ""
    assert _format_unix_timestamp("not-a-timestamp") == "not-a-timestamp"


def test_format_salary_range_handles_minimum_and_maximum_combinations() -> None:
    """Salary ranges cover full, lower-bound, upper-bound, and empty inputs."""
    assert _format_salary_range(100000, 120000) == "$100000-$120000"
    assert _format_salary_range(100000, None) == "$100000+"
    assert _format_salary_range(None, 120000) == "up to $120000"
    assert _format_salary_range(None, None) == ""


def test_join_values_formats_strings_iterables_and_scalar_values() -> None:
    """List-like values are joined without splitting plain strings."""
    assert _join_values("Remote") == "Remote"
    assert _join_values(["Python", None, "APIs", ""]) == "Python, APIs"
    assert _join_values({"unexpected": "mapping"}) == "{'unexpected': 'mapping'}"
    assert _join_values(7) == "7"


def test_select_columns_filters_row_mapping_in_requested_order() -> None:
    """Column selection returns requested keys and blanks for missing keys."""
    row = {"title": "Backend Engineer", "company": "ExampleCo"}

    assert _select_columns(row, ["company", "missing", "title"]) == {
        "company": "ExampleCo",
        "missing": "",
        "title": "Backend Engineer",
    }


def test_string_value_converts_none_to_blank_and_other_values_to_text() -> None:
    """Display string conversion is stable for missing and scalar values."""
    assert _string_value(None) == ""
    assert _string_value(42) == "42"
    assert _string_value(False) == "False"


def test_truncate_preserves_short_values_and_shortens_long_values() -> None:
    """Long table values are shortened with ellipses when width allows it."""
    assert _truncate("short", 10) == "short"
    assert _truncate("abcdef", 6) == "abcdef"
    assert _truncate("abcdef", 5) == "ab..."
    assert _truncate("abcdef", 3) == "abc"
