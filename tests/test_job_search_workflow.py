"""Unit tests for job search workflow routing helpers."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from langchain.messages import AIMessage
import pytest

from agent.workflows.job_search.nodes import (
    _job_file_identifier,
    _validate_llm_json,
    handle_job_search_results_node,
    run_job_search_query_node,
    validate_llm_response_node,
)
from agent.workflows.job_search.validation import ValidationResult
from agent.workflows.job_search.workflow import (
    validate_llm_response_edge,
)
from models.job import JobDataLakeJob, JobDataLakeResponse
from models.job_search_params import JobFunction, JobSearchParams, RemoteType, Seniority
from tools.job_description_scraper import JobPostingDetails, JobPostingExtractionError


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


def test_handle_job_search_results_saves_successes_and_scrape_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Each API job is saved even when one description cannot be scraped."""
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

    async def fake_fetch_job_posting(url: str) -> JobPostingDetails:
        if url.endswith("/2"):
            raise JobPostingExtractionError("blocked")
        return JobPostingDetails(url=url, description="Build backend services.")

    monkeypatch.setattr("agent.workflows.job_search.nodes.fetch_job_posting", fake_fetch_job_posting)
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

    successful_record = json.loads((tmp_path / "job_example_backend_1.json").read_text(encoding="utf-8"))
    failed_filename = f"job_{_job_file_identifier(jobs[1])}.json"
    failed_record = json.loads((tmp_path / failed_filename).read_text(encoding="utf-8"))
    assert successful_record["job"]["title"] == "Backend Engineer"
    assert successful_record["scrape"]["status"] == "succeeded"
    assert successful_record["scrape"]["details"]["description"] == "Build backend services."
    assert failed_record["job"]["title"] == "Platform Engineer"
    assert failed_record["scrape"] == {
        "status": "failed",
        "error": "blocked",
        "details": None,
    }


def test_handle_job_search_results_keeps_records_matched_when_fetches_finish_out_of_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Concurrent fetch completion order does not mix descriptions between jobs."""
    jobs = [
        JobDataLakeJob(
            title="First Job",
            url="https://example.test/jobs/slow",
            job_handle="first-job",
        ),
        JobDataLakeJob(
            title="Second Job",
            url="https://example.test/jobs/fast",
            job_handle="second-job",
        ),
    ]
    completion_order: list[str] = []

    async def fake_fetch_job_posting(url: str) -> JobPostingDetails:
        if url.endswith("/slow"):
            await asyncio.sleep(0.01)
        completion_order.append(url)
        return JobPostingDetails(url=url, description=f"Description for {url}")

    monkeypatch.setattr("agent.workflows.job_search.nodes.fetch_job_posting", fake_fetch_job_posting)
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

    first_record = json.loads((tmp_path / "job_first-job.json").read_text(encoding="utf-8"))
    second_record = json.loads((tmp_path / "job_second-job.json").read_text(encoding="utf-8"))
    assert completion_order == [
        "https://example.test/jobs/fast",
        "https://example.test/jobs/slow",
    ]
    assert first_record["scrape"]["details"]["url"] == jobs[0].url
    assert first_record["scrape"]["details"]["description"] == f"Description for {jobs[0].url}"
    assert second_record["scrape"]["details"]["url"] == jobs[1].url
    assert second_record["scrape"]["details"]["description"] == f"Description for {jobs[1].url}"


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
