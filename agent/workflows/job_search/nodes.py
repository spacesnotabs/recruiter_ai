"""Proof-of-concept LangGraph nodes for collecting and parsing job searches."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from hashlib import sha256
import json
import logging
from pathlib import Path
import re
from typing import Any

from langchain.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from agent.workflows.job_search.state import JobSearchContext, JobSearchState
from agent.workflows.job_search.validation import JobSearchQuery, ValidationResult, validate_job_search_query
from models.job import JobDataLakeJob
from models.job_search_params import JobSearchParams
from tools.job_description_scraper import JobPostingDetails, JobPostingExtractionError, fetch_job_posting

logger = logging.getLogger(__name__)

JOB_DATA_DIRECTORY = Path(__file__).resolve().parents[3] / "data"
MAX_DESCRIPTION_FETCHES = 5
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def prompt_user_node(state: JobSearchState) -> dict[str, list[HumanMessage]]:
    """Read one user prompt from stdin and append it to workflow messages."""
    # Print last response from AI if applicable
    messages = state["messages"]
    if messages:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage):
            message_json = json.loads(last_message.text)
            print(f"AI {message_json.get('response')}")

    prompt: str = input("YOU: ")
    return {"messages": [HumanMessage(content=prompt)]}


def llm_call_node(state: JobSearchState, runtime: Runtime[JobSearchContext]) -> dict[str, list[AIMessage]]:
    """Prompt the configured LLM with the latest user message."""
    response: str | None = runtime.context.llm_client.prompt(state["messages"][-1].text)
    print(f"AI: {response}")
    return {"messages": [AIMessage(content=response)]}


def llm_returned_invalid_json_node(state: JobSearchState) -> dict[str, list[HumanMessage]]:
    """Append a retry instruction when the model response cannot be used."""
    return {"messages": [HumanMessage(content="The JSON you returned was invalid. Please try again.")]}


def validate_llm_response_node(state: JobSearchState) -> dict[str, JobSearchQuery | ValidationResult | None]:
    """Validate the latest LLM response and return durable state updates."""
    messages = state["messages"]
    last_message: str = messages[-1].text

    validation_result, job_search_query = _validate_llm_json(last_message)
    return {"validation_result": validation_result, "job_search_query": job_search_query}


async def run_job_search_query_node(
    state: JobSearchState,
    runtime: Runtime[JobSearchContext],
) -> dict[str, object] | None:
    """Execute a validated job search query against the configured jobs API."""
    job_search_query = state["job_search_query"]
    if job_search_query is None:
        raise ValueError("Job search query is required before running the jobs API search.")

    job_results = await runtime.context.job_client.search_jobs(_job_search_query_to_params(job_search_query))
    if job_results is None:
        return None

    return {"job_search_results": job_results}


async def handle_job_search_results_node(state: JobSearchState) -> None:
    """Fetch descriptions and save each returned job as a local JSON record.

    Description requests run concurrently with a small upper bound to avoid
    overwhelming job sites. A failed scrape is recorded with the source job so
    one inaccessible page does not prevent the remaining results from being
    saved.

    Args:
        state: Workflow state containing a validated jobs API response.

    Raises:
        ValueError: If the state does not contain job search results.
        OSError: If the data directory or a job record cannot be written.
    """
    job_search_results = state["job_search_results"]
    if job_search_results is None:
        raise ValueError("Job search results are required before job records can be saved.")

    JOB_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(MAX_DESCRIPTION_FETCHES)
    records = await asyncio.gather(
        *(_build_job_record(job, semaphore) for job in job_search_results.jobs)
    )

    for job, record in zip(job_search_results.jobs, records, strict=True):
        _write_job_record(job, record)

    print(f"AI: Saved {len(records)} job records to {JOB_DATA_DIRECTORY}.")
    return None


async def _build_job_record(
    job: JobDataLakeJob,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """Combine one API job with its scraped posting details."""
    scrape_details: JobPostingDetails | None = None
    scrape_error: str | None = None

    try:
        async with semaphore:
            scrape_details = await fetch_job_posting(url=job.url)
    except JobPostingExtractionError as error:
        scrape_error = str(error)
        logger.warning(
            "Could not extract job description for %s at %s: %s",
            job.title,
            job.company_name or "unknown company",
            error,
        )

    return {
        "source": "job_data_lake",
        "source_job_id": job.job_handle,
        "job": job.model_dump(mode="json"),
        "scrape": {
            "status": "succeeded" if scrape_details else "failed",
            "error": scrape_error,
            "details": asdict(scrape_details) if scrape_details else None,
        },
    }


def _write_job_record(job: JobDataLakeJob, record: dict[str, Any]) -> None:
    """Write one job record using a stable, filesystem-safe filename."""
    output_path = JOB_DATA_DIRECTORY / f"job_{_job_file_identifier(job)}.json"
    output_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def _job_file_identifier(job: JobDataLakeJob) -> str:
    """Return a safe external handle or deterministic URL hash for a job."""
    if job.job_handle:
        safe_handle = SAFE_FILENAME_PATTERN.sub("_", job.job_handle).strip("._")
        if safe_handle:
            return safe_handle

    return sha256(job.url.encode("utf-8")).hexdigest()[:24]


def _job_search_query_to_params(job_search_query: JobSearchQuery) -> JobSearchParams:
    """Convert the LLM-facing query schema into API-facing search parameters."""
    return JobSearchParams(
        keywords=job_search_query.keywords,
        job_function=job_search_query.job_function,
        location=job_search_query.location,
        salary_min=job_search_query.salary_min,
        remote_type=job_search_query.remote_type,
        posted_after=job_search_query.posted_after,
        seniority=tuple(job_search_query.seniority) if job_search_query.seniority else None,
    )


def _validate_llm_json(message: str) -> tuple[ValidationResult, JobSearchQuery | None]:
    """Validate an LLM response against job search workflow requirements.

    Args:
        message: Raw LLM response text to parse and validate.

    Returns:
        A ``ValidationResult`` and the parsed ``JobSearchQuery`` when the text
        is ready to query.
    """
    try:
        last_message_json = json.loads(message)
    except json.JSONDecodeError:
        return ValidationResult.INVALID_JSON, None

    complete: bool = last_message_json.get("complete", False)
    if not complete:
        return ValidationResult.INCOMPLETE_QUERY, None

    job_search_query = validate_job_search_query(message)
    if job_search_query is None:
        return ValidationResult.INVALID_QUERY, None

    return ValidationResult.VALID_QUERY, job_search_query
