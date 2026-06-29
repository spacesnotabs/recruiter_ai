"""Unit tests for job search workflow routing helpers."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from langchain.messages import AIMessage, HumanMessage
import pytest

from agent.workflows.job_search.nodes import (
    _job_file_identifier,
    _validate_llm_json,
    error_handler_node,
    handle_job_search_results_node,
    llm_returned_invalid_json_node,
    run_job_search_query_node,
    validate_llm_response_node,
)
from agent.workflows.job_search.validation import ValidationResult
from agent.workflows.job_search.workflow import (
    NUM_VALIDATION_RETRIES,
    validate_llm_response_edge,
)
from models.job import JobDataLakeJob, JobDataLakeResponse
from models.job_search_params import JobFunction, JobSearchParams, RemoteType, Seniority


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
            "posted_after": 1718000000000,
            "seniority": ["Senior", "Staff"],
        }
    )

    update = validate_llm_response_node(
        {"messages": [AIMessage(content=raw_text)], "job_search_query": None, "validation_result": None}
    )

    assert update["validation_result"] is ValidationResult.VALID_QUERY
    assert update["job_search_query"].keywords == "backend engineer"


def test_validate_llm_response_node_accepts_json_fence() -> None:
    """A complete Markdown JSON fence is removed before validation."""
    raw_text = """```json
{"response": "Searching for Python jobs.", "complete": true, "keywords": "Python"}
```"""

    update = validate_llm_response_node(
        {"messages": [AIMessage(content=raw_text)], "job_search_query": None, "validation_result": None}
    )

    assert update["validation_result"] is ValidationResult.VALID_QUERY
    assert update["job_search_query"].keywords == "Python"


def test_validate_llm_response_edge_routes_valid_query_to_search() -> None:
    """A stored valid validation result transitions to the search node."""
    next_node = validate_llm_response_edge(
        {"messages": [], "job_search_query": None, "validation_result": ValidationResult.VALID_QUERY}
    )

    assert next_node == "run_job_search_query"


def test_invalid_json_node_records_error_and_increments_retry_count() -> None:
    """An invalid response records its failure and prepares one model retry."""
    update = llm_returned_invalid_json_node(
        {
            "messages": [],
            "response_validation_retry_count": 1,
        }
    )

    assert update["errors"] == ["Error: LLM returned invalid JSON"]
    assert update["response_validation_retry_count"] == 2
    assert update["messages"] == [
        HumanMessage(content="The JSON you returned was invalid. Please try again.")
    ]


@pytest.mark.parametrize(
    ("retry_count", "expected_node"),
    [
        (NUM_VALIDATION_RETRIES - 1, "llm_returned_invalid_json"),
        (NUM_VALIDATION_RETRIES, "error_handler"),
    ],
)
def test_invalid_json_routing_honors_retry_limit(
    retry_count: int,
    expected_node: str,
) -> None:
    """Invalid JSON retries below the limit and stops once it is reached."""
    next_node = validate_llm_response_edge(
        {
            "messages": [],
            "job_search_query": None,
            "validation_result": ValidationResult.INVALID_JSON,
            "response_validation_retry_count": retry_count,
        }
    )

    assert next_node == expected_node


def test_error_handler_reports_failure_to_user_and_log(
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The terminal error node emits a generic user message and logs details."""
    errors = [
        "Error: LLM returned invalid JSON",
        "Error: LLM returned invalid JSON",
    ]

    error_handler_node({"errors": errors})

    assert capsys.readouterr().out == (
        "AI: An error occurred during workflow execution. Please try again.\n"
    )
    assert "Error details: " + ",".join(errors) in caplog.text


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
            "posted_after": 1718000000000,
            "seniority": ["Senior", "Staff"],
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
            posted_after=1718000000000,
            seniority=(Seniority.SENIOR, Seniority.STAFF),
        )
    ]


def test_handle_job_search_results_saves_pending_records_without_fetching_pages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """The search workflow saves API records without touching job URLs."""
    jobs = [
        JobDataLakeJob(
            title="Backend Engineer",
            company_name="Example",
            url="https://example.test/jobs/1",
            job_handle="example/backend:1",
        ),
        JobDataLakeJob(
            title="Platform Engineer",
            company_name="Example",
            url="https://example.test/jobs/2",
        ),
    ]

    monkeypatch.setattr("agent.workflows.job_search.nodes.JOB_DATA_DIRECTORY", tmp_path)
    state = {
        "messages": [],
        "job_search_query": None,
        "validation_result": ValidationResult.VALID_QUERY,
        "job_search_results": JobDataLakeResponse(
            found=2,
            page=1,
            per_page=10,
            jobs=jobs,
        ),
        "job_search_succeeded": True,
    }

    asyncio.run(handle_job_search_results_node(state))

    first_record = json.loads((tmp_path / "job_example_backend_1.json").read_text(encoding="utf-8"))
    second_filename = f"job_{_job_file_identifier(jobs[1])}.json"
    second_record = json.loads((tmp_path / second_filename).read_text(encoding="utf-8"))
    assert first_record["job"]["title"] == "Backend Engineer"
    assert second_record["job"]["title"] == "Platform Engineer"
    assert first_record["scrape"] == {
        "status": "pending",
        "error": None,
        "details": None,
        "input_truncated": False,
    }


def test_handle_job_search_results_requires_results() -> None:
    """The persistence node rejects workflow state without search results."""
    state = {
        "messages": [],
        "job_search_query": None,
        "validation_result": ValidationResult.VALID_QUERY,
        "job_search_results": None,
        "job_search_succeeded": False,
    }

    with pytest.raises(ValueError, match="Job search results are required"):
        asyncio.run(handle_job_search_results_node(state))


def test_job_file_identifier_uses_stable_url_hash_when_handle_is_missing() -> None:
    """Jobs without provider handles receive deterministic safe identifiers."""
    job = JobDataLakeJob(title="Backend Engineer", url="https://example.test/jobs/1")

    assert _job_file_identifier(job) == _job_file_identifier(job)
    assert len(_job_file_identifier(job)) == 24
