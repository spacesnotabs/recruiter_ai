"""Validation helpers for LLM-produced job search query JSON."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from models.job_search_params import JobFunction, RemoteType, Seniority

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Validation outcomes used to route the job search workflow graph."""

    INVALID_JSON = "invalid_json"
    INCOMPLETE_QUERY = "incomplete_query"
    INVALID_QUERY = "invalid_query"
    VALID_QUERY = "valid_query"


class JobSearchQuery(BaseModel):
    """Pydantic schema for a complete LLM job search query response."""

    response: str
    complete: bool
    keywords: str = Field(
        description=(
            "Search terms for job titles, company names, and skills only. "
            "Do not include location, salary, seniority, remote type, job function, "
            "or posting date filters."
        )
    )
    job_function: Optional[JobFunction] = None
    salary_min: Optional[int] = None
    remote_type: Optional[RemoteType] = None
    location: Optional[str] = None
    posted_after: Optional[int] = Field(
        default=None,
        description="Unix timestamp in milliseconds; return only jobs posted after this time.",
    )
    seniority: Optional[list[Seniority]] = Field(
        default=None,
        description="One or more seniority levels accepted by the jobs API.",
    )

class JobDescription(BaseModel):
    """LLM-extracted details from a cleaned public job-posting page."""

    description: str = Field(min_length=1)
    salary: str | None = None
    location: str | None = None
    title: str | None = None

    @field_validator("description")
    @classmethod
    def description_must_contain_text(cls, value: str) -> str:
        """Reject whitespace-only descriptions while preserving valid source text."""
        if not value.strip():
            raise ValueError("description must contain non-whitespace text")
        return value

def validate_job_search_query(raw_text: str) -> JobSearchQuery | None:
    """Parse raw LLM text as complete job search query JSON.

    Args:
        raw_text: JSON text emitted by the LLM.

    Returns:
        The JobSearchQuery when the JSON matches ``JobSearchQuery``; otherwise None.
        Validation failures are logged for operator debugging.
    """
    try:
        job_search_query = JobSearchQuery.model_validate_json(raw_text)
        return job_search_query
    except ValidationError:
        logger.error("The following text was not valid: %s", raw_text)
        return None


def validate_job_description(raw_text: str) -> JobDescription | None:
    """Parse LLM text as a job-description extraction response.

    Args:
        raw_text: JSON text emitted by the description-extraction model.

    Returns:
        A validated ``JobDescription`` when the response has a non-empty
        description; otherwise ``None``.
    """
    try:
        return JobDescription.model_validate_json(raw_text)
    except ValidationError:
        logger.error("The following text was not a valid job description: %s", raw_text)
        return None
