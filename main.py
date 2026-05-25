"""Command-line entrypoint for querying Job Data Lake jobs."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from api.job_data_lake import (
    JOB_DATA_LAKE_API_KEY_ENV_VAR,
    JOB_DATA_LAKE_BASE_URL,
    JOB_DATA_LAKE_JOBS_ENDPOINT,
    ROOT_ENV_PATH,
    JobDataLakeClient,
    read_env_file_value,
)
from api.job_response_formatter import format_jobs_csv, format_jobs_table
from models.job_search_params import JobSearchParams, RemoteType


def parse_args() -> argparse.Namespace:
    """Parse command-line options for a Job Data Lake job search."""
    parser = argparse.ArgumentParser(description="Fetch jobs from Job Data Lake.")
    parser.add_argument("--keywords", help="Search keywords for job listings.")
    parser.add_argument("--job-function", help="Filter by job function.")
    parser.add_argument("--salary-min", type=int, help="Minimum salary filter.")
    parser.add_argument(
        "--remote-type",
        choices=[remote_type.value for remote_type in RemoteType],
        help="Filter by remote work type.",
    )
    parser.add_argument("--base-url", default=os.getenv("JOB_API_URL", JOB_DATA_LAKE_BASE_URL))
    parser.add_argument(
        "--endpoint",
        default=JOB_DATA_LAKE_JOBS_ENDPOINT,
        help="API endpoint path to call, relative to the base URL.",
    )
    parser.add_argument("--api-key", default=os.getenv("JOB_API_KEY"))
    parser.add_argument(
        "--format",
        choices=("table", "csv", "json"),
        default="table",
        help="Output format for the API response.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path for formatted output. Stdout is used when omitted.",
    )
    parser.add_argument(
        "--print-query",
        action="store_true",
        help="Print the API query URL to stderr before sending the request.",
    )
    return parser.parse_args()


async def run() -> int:
    """Run the CLI and return a process exit code."""
    args = parse_args()
    api_key = read_env_file_value(ROOT_ENV_PATH, JOB_DATA_LAKE_API_KEY_ENV_VAR) or args.api_key
    if not api_key:
        print(
            "Provide --api-key, set JOB_API_KEY, or add JOB_DATA_LAKE_API_KEY to .env.",
            file=sys.stderr,
        )
        return 1

    params = JobSearchParams(
        keywords=args.keywords,
        job_function=args.job_function,
        salary_min=args.salary_min,
        remote_type=RemoteType(args.remote_type) if args.remote_type else None,
    )
    client = JobDataLakeClient(base_url=args.base_url, api_key=api_key)

    if args.print_query:
        print(f"Query URL: {client.build_url(args.endpoint, params.to_query_params())}", file=sys.stderr)

    try:
        result = await client.get(args.endpoint, params.to_query_params())
    except httpx.HTTPStatusError as error:
        print(f"API returned HTTP {error.response.status_code}: {error.response.text}", file=sys.stderr)
        return 1
    except httpx.HTTPError as error:
        print(f"Could not complete API request: {error}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print("API response was not valid JSON.", file=sys.stderr)
        return 1

    if args.format == "json":
        output = f"{json.dumps(result, indent=2)}\n"
    elif args.format == "csv":
        output = format_jobs_csv(result)
    else:
        output = f"{format_jobs_table(result)}\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8", newline="")
    else:
        print(output, end="")

    return 0


def main() -> int:
    """Run the async CLI entrypoint."""
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
