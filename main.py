"""Command-line entrypoint for querying Job Data Lake jobs."""

from __future__ import annotations

from agent.controller import OPEN_ROUTER_API_KEY_ENV_VAR, AgentController

import argparse
import asyncio
import json
import os
import sys
import logging
from pathlib import Path

import httpx

from api.job_data_lake import (
    JOB_DATA_LAKE_API_KEY_ENV_VAR,
    JOB_DATA_LAKE_BASE_URL,
    JOB_DATA_LAKE_JOBS_ENDPOINT,
    ROOT_ENV_PATH,
    JobDataLakeClient,
)
from api.job_response_formatter import format_jobs_csv, format_jobs_table
from models.job_search_params import JobFunction, JobSearchParams, RemoteType
from tools.env_file import read_env_file_value
from tools.job_description_scraper import fetch_job_posting, JobPostingDetails

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename="app.log")
logger = logging.getLogger(__name__)

_JOB_PARAM_FILE_FIELDS = {
    "keywords",
    "job_function",
    "location",
    "salary_min",
    "remote_type",
}


def parse_args() -> argparse.Namespace:
    """Parse command-line options for a Job Data Lake job search."""
    parser = argparse.ArgumentParser(description="Fetch jobs from Job Data Lake.")

    parser.add_argument("--params-file", type=Path, help="Path to a JSON file containing job search parameters.")
    parser.add_argument("--keywords", help="Search keywords for job listings.")
    parser.add_argument(
        "--job-function",
        choices=[job_function.value for job_function in JobFunction],
        help="Filter by job function.",
    )
    parser.add_argument("--location", help='Free-text location filter, such as "Remote" or "San Francisco".')
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
        "--openrouter-api-key",
        default=os.getenv(OPEN_ROUTER_API_KEY_ENV_VAR),
        help="OpenRouter API key used for AI prompting.",
    )
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
    args = parser.parse_args()

    if args.params_file:
        _apply_params_file(args, parser)

    return args


def _apply_params_file(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Load job search parameter defaults from a JSON file into parsed arguments."""
    file_params = _read_params_file(args.params_file, parser)
    for field_name in _JOB_PARAM_FILE_FIELDS:
        if getattr(args, field_name) is None and field_name in file_params:
            setattr(args, field_name, file_params[field_name])


def _read_params_file(params_file: Path, parser: argparse.ArgumentParser) -> dict[str, object]:
    """Read and validate a JSON object containing supported job search parameters."""
    try:
        raw_params = json.loads(params_file.read_text(encoding="utf-8"))
    except OSError as error:
        parser.error(f"Could not read --params-file '{params_file}': {error}")
    except json.JSONDecodeError as error:
        parser.error(f"--params-file '{params_file}' is not valid JSON: {error}")

    if not isinstance(raw_params, dict):
        parser.error("--params-file must contain a JSON object.")

    unknown_fields = set(raw_params) - _JOB_PARAM_FILE_FIELDS
    if unknown_fields:
        fields = ", ".join(sorted(unknown_fields))
        allowed_fields = ", ".join(sorted(_JOB_PARAM_FILE_FIELDS))
        parser.error(f"--params-file contains unsupported field(s): {fields}. Allowed fields: {allowed_fields}.")

    for field_name, field_value in raw_params.items():
        _validate_params_file_value(field_name, field_value, parser)

    return raw_params


def _validate_params_file_value(
    field_name: str,
    field_value: object,
    parser: argparse.ArgumentParser,
) -> None:
    """Validate one JSON field from a params file against CLI argument types."""
    if field_value is None:
        return

    if field_name in {"keywords", "location"} and not isinstance(field_value, str):
        parser.error(f"--params-file field '{field_name}' must be a string.")

    if field_name == "job_function" and field_value not in {job_function.value for job_function in JobFunction}:
        choices = ", ".join(job_function.value for job_function in JobFunction)
        parser.error(f"--params-file field 'job_function' must be one of: {choices}.")

    if field_name == "salary_min" and (not isinstance(field_value, int) or isinstance(field_value, bool)):
        parser.error("--params-file field 'salary_min' must be an integer.")

    if field_name == "remote_type" and field_value not in {remote_type.value for remote_type in RemoteType}:
        choices = ", ".join(remote_type.value for remote_type in RemoteType)
        parser.error(f"--params-file field 'remote_type' must be one of: {choices}.")

async def _print_job_details(json_data: dict):
    """
    Print the job description for the first job in the JSON data.
    """
    job_to_print = json_data["jobs"][0]
    url = job_to_print.get("url", None)
    if url is not None:
        desc: JobPostingDetails = await fetch_job_posting(url=url)
        print(desc.description)


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
    openrouter_api_key = read_env_file_value(ROOT_ENV_PATH, OPEN_ROUTER_API_KEY_ENV_VAR) or args.openrouter_api_key
    if not openrouter_api_key:
        print(
            "Provide --openrouter-api-key, set OPENROUTER_API_KEY, or add OPENROUTER_API_KEY to .env.",
            file=sys.stderr,
        )
        return 1

    params = JobSearchParams(
        keywords=args.keywords,
        job_function=JobFunction(args.job_function) if args.job_function else None,
        location=args.location,
        salary_min=args.salary_min,
        remote_type=RemoteType(args.remote_type) if args.remote_type else None,
    )
    client = JobDataLakeClient(base_url=args.base_url, api_key=api_key)

    if args.print_query:
        print(f"Query URL: {client.build_url(args.endpoint, params.to_query_params())}", file=sys.stderr)

    # call the API to get the job data
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

    await _print_job_details(json_data=result)

    # handle the job data
    if args.format == "json":
        output: str = f"{json.dumps(result, indent=2)}\n"
    elif args.format == "csv":
        output: str = format_jobs_csv(result)
    else:
        output: str = f"{format_jobs_table(result)}\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8", newline="")
    else:
        print(output, end="")

    controller = AgentController(api_key=openrouter_api_key)
    response = controller.prompt_model(prompt="Hey, how are you?")
    print(f"AI response: {response}")
    return 0


def main() -> int:
    """Run the async CLI entrypoint."""
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
