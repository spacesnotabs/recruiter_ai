"""Small example script for calling the Job Data Lake jobs API.

Edit the constants near the top of this file, then run it from the repository
root with:

    python my_script.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx


REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recruiter_ai.ingestion.apis.job_api_client import (  # noqa: E402
    JOB_DATA_LAKE_API_KEY_ENV_VAR,
    JOB_DATA_LAKE_BASE_URL,
    JOB_DATA_LAKE_JOBS_ENDPOINT,
    PACKAGE_CONFIG_ENV_PATH,
    JobApiClient,
    JobSearchParams,
    RemoteType,
    read_env_file_value,
)


# Update these values before running the script.
BASE_URL = JOB_DATA_LAKE_BASE_URL
ENDPOINT = JOB_DATA_LAKE_JOBS_ENDPOINT
KEYWORDS = "ai software engineer"
JOB_FUNCTION = "eng"
SALARY_MIN = "160"
REMOTE_TYPE = RemoteType.FULLY_REMOTE
TIMEOUT_SECONDS = 30
PRINT_QUERY_URL = True

# Leave API_KEY as None to read JOB_DATA_LAKE_API_KEY from
# src/recruiter_ai/config/.env, then from the process environment.
API_KEY = None


def get_api_key() -> str:
    """Return the configured API key or raise a clear setup error."""
    api_key = API_KEY
    if not api_key:
        api_key = read_env_file_value(PACKAGE_CONFIG_ENV_PATH, JOB_DATA_LAKE_API_KEY_ENV_VAR)
    if not api_key:
        api_key = os.getenv(JOB_DATA_LAKE_API_KEY_ENV_VAR)
    if not api_key:
        raise RuntimeError(
            "Set API_KEY in my_script.py, add JOB_DATA_LAKE_API_KEY to "
            "src/recruiter_ai/config/.env, or set the JOB_DATA_LAKE_API_KEY "
            "environment variable."
        )

    return api_key


def build_search_params() -> JobSearchParams:
    """Build the jobs API query parameters from the editable defaults."""
    return JobSearchParams(
        keywords=KEYWORDS,
        job_function=JOB_FUNCTION,
        salary_min=SALARY_MIN,
        remote_type=REMOTE_TYPE,
    )


async def call_jobs_api() -> dict[str, Any]:
    """Call the configured jobs API endpoint and return the JSON response."""
    client = JobApiClient(
        base_url=BASE_URL,
        api_key=get_api_key(),
        timeout_seconds=TIMEOUT_SECONDS,
    )
    params = build_search_params()

    if PRINT_QUERY_URL:
        print(f"Query URL: {client.build_query_url(params, ENDPOINT)}", file=sys.stderr)

    return await client.get(ENDPOINT, params.to_query_params())


async def main() -> int:
    """Run the example API call and print the response as formatted JSON."""
    try:
        result = await call_jobs_api()
    except httpx.HTTPStatusError as error:
        print(
            f"API returned HTTP {error.response.status_code}: {error.response.text}",
            file=sys.stderr,
        )
        return 1
    except httpx.HTTPError as error:
        print(f"Could not complete API request: {error}", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
