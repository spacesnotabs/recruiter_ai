"""Client for the Job Data Lake job listings API.

Keep this module focused on API request/response behavior. CLI usage can read a
local config/.env file for the service API key.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

# Keep the root URL separate from endpoint paths so the client can support
# additional Job Data Lake endpoints without changing its construction.
JOB_DATA_LAKE_BASE_URL = "https://api.jobdatalake.com/"
JOB_DATA_LAKE_JOBS_ENDPOINT = "/v1/jobs"
PACKAGE_CONFIG_ENV_PATH = Path(__file__).resolve().parents[2] / "config" / ".env"
JOB_DATA_LAKE_API_KEY_ENV_VAR = "JOB_DATA_LAKE_API_KEY"


class RemoteType(str, Enum):
    """Remote work types supported by the upstream jobs API."""

    FULLY_REMOTE = "fully_remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"


@dataclass(frozen=True)
class JobSearchParams:
    """Search filters supported by the upstream jobs API."""

    keywords: str | None = None
    job_function: str | None = None
    salary_min: int | None = None
    remote_type: RemoteType | None = None

    def to_query_params(self) -> dict[str, str | int]:
        """Convert populated search fields to Job Data Lake query parameters."""
        return {
            key: value
            for key, value in {
                "q": self.keywords,
                "job_function": self.job_function,
                "salary_min": self.salary_min,
                "remote_type": self.remote_type.value if self.remote_type else None,
            }.items()
            if value is not None
        }


class JobApiClient:
    """Small client wrapper for the Job Data Lake API."""

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 30) -> None:
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
        # Normalize endpoint joins so callers can pass either "v1/jobs" or
        # "/v1/jobs" and still get a URL under the configured API root.
        base_url = httpx.URL(self.base_url)
        endpoint_url = base_url.join(endpoint_path.lstrip("/"))
        return str(endpoint_url.copy_merge_params(query_params or {}))

    def build_query_url(
        self,
        params: JobSearchParams | None = None,
        endpoint_path: str = JOB_DATA_LAKE_JOBS_ENDPOINT,
    ) -> str:
        """Build a troubleshooting URL for a job-search style request."""
        return self.build_url(endpoint_path, params.to_query_params() if params else None)

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
                    "X-API-Key": f"{self.api_key}",
                },
            )
            response.raise_for_status()
            return response.json()

    async def search_jobs(self, params: JobSearchParams | None = None) -> dict[str, Any]:
        """Search the default jobs endpoint with optional job search filters."""
        return await self.get(
            JOB_DATA_LAKE_JOBS_ENDPOINT,
            params.to_query_params() if params else None,
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the API client CLI."""
    parser = argparse.ArgumentParser(description="Fetch jobs from a configured API.")
    parser.add_argument("--keywords", help="Search keywords for job listings.")
    parser.add_argument("--base-url", default=os.getenv("JOB_API_URL", JOB_DATA_LAKE_BASE_URL))
    parser.add_argument(
        "--endpoint",
        default=JOB_DATA_LAKE_JOBS_ENDPOINT,
        help="API endpoint path to call, relative to the base URL.",
    )
    parser.add_argument("--api-key", default=os.getenv("JOB_API_KEY"))
    parser.add_argument(
        "--print-query",
        action="store_true",
        help="Print the API query URL to stderr before sending the request.",
    )
    parser.add_argument("--job-function", help="Filter by job function.")
    parser.add_argument("--salary-min", type=int, help="Minimum salary filter.")
    parser.add_argument(
        "--remote-type",
        choices=[remote_type.value for remote_type in RemoteType],
        help="Filter by remote work type.",
    )
    return parser.parse_args()


def read_env_file_value(env_path: Path, variable_name: str) -> str | None:
    """Read a single variable from a simple KEY=VALUE environment file."""
    if not env_path.exists():
        return None

    # Parse only the simple KEY=VALUE format this project needs instead of
    # adding a dotenv dependency for a single CLI fallback.
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue

        key, value = stripped_line.split("=", 1)
        if key.strip() == variable_name:
            return value.strip().strip("'\"") or None

    return None


async def run_from_cli() -> int:
    """Run the command-line client and return a process exit code."""
    args = parse_args()

    # Prefer the project config key for this service, then fall back to the
    # existing CLI/environment API key path.
    api_key = read_env_file_value(PACKAGE_CONFIG_ENV_PATH, JOB_DATA_LAKE_API_KEY_ENV_VAR)
    if not api_key:
        api_key = args.api_key

    if not args.base_url or not api_key:
        print(
            "Provide --api-key, set JOB_API_KEY, or add JOB_DATA_LAKE_API_KEY to config/.env.",
            file=sys.stderr,
        )
        return 1

    client = JobApiClient(base_url=args.base_url, api_key=api_key)
    params = JobSearchParams(
        keywords=args.keywords,
        job_function=args.job_function,
        salary_min=args.salary_min,
        remote_type=RemoteType(args.remote_type) if args.remote_type else None,
    )
    if args.print_query:
        # Send troubleshooting output to stderr so stdout remains valid JSON.
        print(f"Query URL: {client.build_query_url(params, args.endpoint)}", file=sys.stderr)

    try:
        result = await client.get(args.endpoint, params.to_query_params())
    except httpx.HTTPStatusError as error:
        print(
            f"API returned HTTP {error.response.status_code}: {error.response.text}",
            file=sys.stderr,
        )
        return 1
    except httpx.HTTPError as error:
        print(f"Could not complete API request: {error}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("API response was not valid JSON.", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    """Entrypoint for running the module as a script."""
    return asyncio.run(run_from_cli())


if __name__ == "__main__":
    raise SystemExit(main())
