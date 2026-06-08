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
