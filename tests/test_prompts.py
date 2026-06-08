"""Tests for schema-driven recruiter workflow prompts."""

from __future__ import annotations

from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from agent.workflows.job_search.validation import JobSearchQuery


def test_job_search_prompt_contains_current_pydantic_schema() -> None:
    """The extraction prompt derives its fields from the Pydantic model."""
    schema = JobSearchQuery.model_json_schema()

    for property_name in schema["properties"]:
        assert f'"{property_name}"' in JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT

    assert "job_function" not in schema["required"]


def test_job_search_prompt_keeps_filter_values_out_of_keywords() -> None:
    """Keyword instructions reserve the API text search for its indexed fields."""
    assert "job titles, company names, and skills" in JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
    assert "Do not include salary, location" in JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
    assert "put each value in its dedicated field instead" in JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
