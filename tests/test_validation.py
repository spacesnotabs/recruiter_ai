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
        }
    )

    job_search_query = validate_job_search_query(raw_text)

    assert isinstance(job_search_query, JobSearchQuery)
    assert job_search_query.keywords == "backend engineer"
    assert job_search_query.salary_min == 120000


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
