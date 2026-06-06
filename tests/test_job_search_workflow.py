"""Unit tests for job search workflow routing helpers."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from langchain.messages import AIMessage

from agent.workflows.job_search.nodes import (
    _validate_llm_json,
    run_job_search_query_node,
    validate_llm_response_node,
)
from agent.workflows.job_search.validation import ValidationResult
from agent.workflows.job_search.workflow import (
    validate_llm_response_edge,
)
from models.job import JobDataLakeJob, JobDataLakeResponse
from models.job_search_params import JobFunction, JobSearchParams, RemoteType


def test_validate_json_rejects_malformed_llm_response() -> None:
    """Malformed model text is classified before schema validation."""
    validation_result, job_search_query = _validate_llm_json("not json")

    assert validation_result is ValidationResult.INVALID_JSON
    assert job_search_query is None


def test_validate_json_routes_incomplete_query_to_user_prompt() -> None:
    """Incomplete model JSON requests more user input."""
    raw_text = json.dumps({"response": "Which role are you looking for?", "complete": False})

    validation_result, job_search_query = _validate_llm_json(raw_text)

    assert validation_result is ValidationResult.INCOMPLETE_QUERY
    assert job_search_query is None


def test_validate_json_rejects_complete_json_with_wrong_shape() -> None:
    """Complete JSON without the required query fields is invalid."""
    raw_text = json.dumps({"response": "Searching now.", "complete": True})

    validation_result, job_search_query = _validate_llm_json(raw_text)

    assert validation_result is ValidationResult.INVALID_QUERY
    assert job_search_query is None


def test_validate_llm_response_node_returns_valid_query_for_state() -> None:
    """Valid complete job search JSON is parsed into workflow state."""
    raw_text = json.dumps(
        {
            "response": "Searching for backend engineering jobs.",
            "complete": True,
            "keywords": "backend engineer",
            "job_function": "eng",
            "salary_min": 120000,
            "remote_type": "fully_remote",
            "location": "Seattle",
        }
    )

    update = validate_llm_response_node(
        {"messages": [AIMessage(content=raw_text)], "job_search_query": None, "validation_result": None}
    )

    assert update["validation_result"] is ValidationResult.VALID_QUERY
    assert update["job_search_query"].keywords == "backend engineer"


def test_validate_llm_response_edge_routes_valid_query_to_search() -> None:
    """A stored valid validation result transitions to the search node."""
    next_node = validate_llm_response_edge(
        {"messages": [], "job_search_query": None, "validation_result": ValidationResult.VALID_QUERY}
    )

    assert next_node == "run_job_search_query"


def test_run_job_search_query_node_converts_query_to_api_params() -> None:
    """The search node passes API-facing params to the injected job client."""
    calls: list[JobSearchParams] = []

    class FakeJobClient:
        async def search_jobs(self, params: JobSearchParams | None = None) -> JobDataLakeResponse:
            if params is not None:
                calls.append(params)
            return JobDataLakeResponse(
                found=1,
                page=1,
                per_page=10,
                jobs=[JobDataLakeJob(title="Backend Engineer", url="https://example.test/jobs/1")],
            )

    class FakeRuntime:
        context = SimpleNamespace(job_client=FakeJobClient())

    raw_text = json.dumps(
        {
            "response": "Searching for backend engineering jobs.",
            "complete": True,
            "keywords": "backend engineer",
            "job_function": "eng",
            "salary_min": 120000,
            "remote_type": "fully_remote",
            "location": "Seattle",
        }
    )
    _, job_search_query = _validate_llm_json(raw_text)

    result = asyncio.run(
        run_job_search_query_node(
            {"messages": [], "job_search_query": job_search_query, "validation_result": ValidationResult.VALID_QUERY},
            FakeRuntime(),  # type: ignore[arg-type]
        )
    )

    assert result == {
        "job_search_results": JobDataLakeResponse(
            found=1,
            page=1,
            per_page=10,
            jobs=[JobDataLakeJob(title="Backend Engineer", url="https://example.test/jobs/1")],
        )
    }
    assert calls == [
        JobSearchParams(
            keywords="backend engineer",
            job_function=JobFunction.ENGINEERING,
            location="Seattle",
            salary_min=120000,
            remote_type=RemoteType.FULLY_REMOTE,
        )
    ]
