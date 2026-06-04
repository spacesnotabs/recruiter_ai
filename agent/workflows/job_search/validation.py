"""Validation helpers for LLM-produced job search query JSON."""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, ValidationError

from models.job_search_params import JobFunction, RemoteType

logger = logging.getLogger(__name__)


class JobSearchQuery(BaseModel):
    """Pydantic schema for a complete LLM job search query response."""

    response: str
    complete: bool
    keywords: str
    job_function: JobFunction
    salary_min: Optional[int] = None
    remote_type: Optional[RemoteType] = None
    location: Optional[str] = None


def validate_job_search_query(raw_text: str) -> JobSearchQuery | None:
    """Return whether raw LLM text is valid complete job search query JSON.

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

