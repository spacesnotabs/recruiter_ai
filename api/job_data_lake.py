"""Async client for the Job Data Lake jobs API."""

from __future__ import annotations

from typing import Any

import httpx

from models.job import JobDataLakeResponse
from models.job_search_params import JobSearchParams


JOB_DATA_LAKE_BASE_URL = "https://api.jobdatalake.com/"
JOB_DATA_LAKE_JOBS_ENDPOINT = "/v1/jobs"


class JobDataLakeClient:
    """Small async client wrapper for the Job Data Lake API."""

    def __init__(self, api_key: str, base_url: str = JOB_DATA_LAKE_BASE_URL, timeout_seconds: int = 30) -> None:
        """Create a client for a Job Data Lake API root URL and API key."""
        self.base_url = f"{base_url.rstrip('/')}/"
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def build_url(
        self,
        endpoint_path: str,
        query_params: dict[str, str | int] | None = None,
    ) -> str:
        """Build a full API URL for an endpoint path and optional query params."""
        base_url = httpx.URL(self.base_url)
        endpoint_url = base_url.join(endpoint_path.lstrip("/"))
        return str(endpoint_url.copy_merge_params(query_params or {}))

    async def get(
        self,
        endpoint_path: str,
        query_params: dict[str, str | int] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated GET request to an endpoint and return JSON."""
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.build_url(endpoint_path),
                params=query_params,
                headers={
                    "Accept": "application/json",
                    "X-API-Key": self.api_key,
                },
            )
            response.raise_for_status()
            return response.json()

    async def search_jobs(self, params: JobSearchParams | None = None) -> JobDataLakeResponse:
        """Search the jobs endpoint and validate its documented response."""
        response_data = await self.get(
            JOB_DATA_LAKE_JOBS_ENDPOINT,
            params.to_query_params() if params else None,
        )
        return JobDataLakeResponse.model_validate(response_data)
