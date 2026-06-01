"""Unit tests for LLM response validation helpers."""

from __future__ import annotations

import json
import logging

import pytest

from agent.validation import validate_job_search_query


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

    assert validate_job_search_query(raw_text) is True


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
        assert validate_job_search_query(raw_text) is False

    assert "The following text was not valid" in caplog.text
