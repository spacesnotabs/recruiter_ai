"""State definitions for LangGraph-backed recruiter workflows."""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated

from agent.llms.base import LLMClient
from agent.workflows.job_search.validation import JobSearchQuery, ValidationResult
from api.job_data_lake import JobDataLakeClient
from models.job import JobDataLakeResponse

from langchain.messages import AnyMessage
from typing_extensions import TypedDict


@dataclass
class JobSearchContext:
    """Context object for the job search workflow."""
    llm_client: LLMClient
    job_client: JobDataLakeClient


class JobSearchState(TypedDict):
    """Conversation state shared by the proof-of-concept LangGraph workflow."""
    messages: Annotated[list[AnyMessage], operator.add]
    job_search_query: JobSearchQuery | None
    validation_result: ValidationResult | None
    job_search_results: JobDataLakeResponse | None
    job_search_succeeded: bool 
