"""Unit tests for the Job Data Lake API client helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from api import job_data_lake
from api.job_data_lake import JobDataLakeClient
from models.job import JobDataLakeResponse
from models.job_search_params import JobFunction, JobSearchParams, RemoteType


def test_client_initializes_with_normalized_base_url() -> None:
    """The client stores the API key, timeout, and a slash-terminated base URL."""
    client = JobDataLakeClient(
        api_key="test-key",
        base_url="https://api.example.test/root",
        timeout_seconds=12,
    )

    assert client.api_key == "test-key"
    assert client.base_url == "https://api.example.test/root/"
    assert client.timeout_seconds == 12


def test_build_url_joins_endpoint_and_merges_query_params() -> None:
    """Endpoint paths and query params are combined into a full API URL."""
    client = JobDataLakeClient(api_key="test-key", base_url="https://api.example.test/")

    url = client.build_url("/v1/jobs", {"q": "backend engineer", "page": 2})

    assert url == "https://api.example.test/v1/jobs?q=backend+engineer&page=2"


def test_get_sends_authenticated_request_and_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET requests include auth headers and return the decoded JSON body."""
    calls: list[dict[str, Any]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            calls.append({"raised": True})

        def json(self) -> dict[str, Any]:
            return {"jobs": [{"title": "Backend Engineer"}]}

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            calls.append({"timeout": self.timeout})
            return self

        async def __aexit__(self, *exc_info: object) -> None:
            calls.append({"closed": True})

        async def get(
            self,
            url: str,
            *,
            params: dict[str, str | int] | None,
            headers: dict[str, str],
        ) -> FakeResponse:
            calls.append({"url": url, "params": params, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr(job_data_lake.httpx, "AsyncClient", FakeAsyncClient)
    client = JobDataLakeClient(
        api_key="secret-key",
        base_url="https://api.example.test/",
        timeout_seconds=7,
    )

    result = asyncio.run(client.get("/v1/jobs", {"q": "backend"}))

    assert result == {"jobs": [{"title": "Backend Engineer"}]}
    assert calls == [
        {"timeout": 7},
        {
            "url": "https://api.example.test/v1/jobs",
            "params": {"q": "backend"},
            "headers": {"Accept": "application/json", "X-API-Key": "secret-key"},
        },
        {"raised": True},
        {"closed": True},
    ]


def test_search_jobs_passes_default_endpoint_and_query_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search uses the jobs endpoint and converts populated filters to query params."""
    calls: list[tuple[str, dict[str, str | int] | None]] = []

    async def fake_get(
        self: JobDataLakeClient,
        endpoint_path: str,
        query_params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        calls.append((endpoint_path, query_params))
        return {
            "found": 1,
            "page": 1,
            "per_page": 10,
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "url": "https://example.test/jobs/1",
                    "posted_at": 1_700_000_000,
                    "salary_min_usd": 180,
                }
            ],
            "stats": {"total_jobs": 100, "new_last_24h": 5},
        }

    monkeypatch.setattr(JobDataLakeClient, "get", fake_get)
    params = JobSearchParams(
        keywords="backend",
        job_function=JobFunction.ENGINEERING,
        location="Seattle",
        salary_min=120000,
        remote_type=RemoteType.FULLY_REMOTE,
    )

    result = asyncio.run(JobDataLakeClient("key").search_jobs(params))

    assert isinstance(result, JobDataLakeResponse)
    assert result.found == 1
    assert result.jobs[0].posted_at == datetime.fromtimestamp(1_700_000_000, tz=UTC)
    assert result.jobs[0].salary_min_usd == Decimal("180")
    assert calls == [
        (
            "/v1/jobs",
            {
                "q": "backend",
                "job_function": "eng",
                "location": "Seattle",
                "salary_min": 120000,
                "remote_type": "fully_remote",
            },
        )
    ]


def test_search_jobs_passes_no_query_params_when_filters_are_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Search can request the jobs endpoint without filter params."""
    calls: list[tuple[str, dict[str, str | int] | None]] = []

    async def fake_get(
        self: JobDataLakeClient,
        endpoint_path: str,
        query_params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        calls.append((endpoint_path, query_params))
        return {"found": 0, "page": 1, "per_page": 10, "jobs": []}

    monkeypatch.setattr(JobDataLakeClient, "get", fake_get)

    result = asyncio.run(JobDataLakeClient("key").search_jobs())

    assert result == JobDataLakeResponse(found=0, page=1, per_page=10, jobs=[])
    assert calls == [("/v1/jobs", None)]
