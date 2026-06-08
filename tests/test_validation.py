"""Unit tests for LLM response validation helpers."""

from __future__ import annotations

import json
import logging

import pytest

from agent.workflows.job_search.validation import JobSearchQuery, validate_job_search_query


def test_validate_job_search_query_accepts_complete_job_search_json() -> None:
    """Valid LLM job search JSON is accepted."""
    raw_text = json.dumps(
        {
            "response": "Searching for backend engineering jobs.",
            "complete": "true",
            "keywords": "backend engineer",
            "job_function": "eng",
            "salary_min": "120000",
            "remote_type": "fully_remote",
            "location": "Seattle",
            "posted_after": 1718000000000,
            "seniority": ["Senior", "Staff"],
        }
    )

    job_search_query = validate_job_search_query(raw_text)

    assert isinstance(job_search_query, JobSearchQuery)
    assert job_search_query.keywords == "backend engineer"
    assert job_search_query.salary_min == 120000
    assert job_search_query.posted_after == 1718000000000
    assert [level.value for level in job_search_query.seniority or []] == ["Senior", "Staff"]


def test_validate_job_search_query_allows_missing_job_function() -> None:
    """A complete query may omit a job function when one cannot be inferred."""
    raw_text = json.dumps(
        {
            "response": "Searching for Python roles.",
            "complete": True,
            "keywords": "Python",
        }
    )

    job_search_query = validate_job_search_query(raw_text)

    assert job_search_query is not None
    assert job_search_query.job_function is None


def test_validate_job_search_query_rejects_invalid_job_function(caplog: pytest.LogCaptureFixture) -> None:
    """Invalid enum values are rejected and logged."""
    raw_text = json.dumps(
        {
            "response": "Searching for backend engineering jobs.",
            "complete": "false",
            "keywords": "backend engineer",
            "job_function": "invalid",
            "salary_min": None,
            "remote_type": "fully_remote",
            "location": "Seattle",
        }
    )

    with caplog.at_level(logging.ERROR):
        assert validate_job_search_query(raw_text) is None

    assert "The following text was not valid" in caplog.text
