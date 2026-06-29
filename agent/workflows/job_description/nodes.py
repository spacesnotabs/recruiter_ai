"""Nodes for enriching saved jobs with LLM-extracted posting descriptions."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langgraph.runtime import Runtime

from agent.llms.base import LLMClient
from agent.prompts import JOB_SEARCH_DESCRIPTION_EXTRACTION_PROMPT
from agent.workflows.job_description.state import JobDescriptionContext, JobDescriptionState
from agent.workflows.job_search.validation import JobDescription, validate_job_description
from tools.json_text import strip_json_fence
from tools.web_scraping import HtmlFetchError, fetch_html, html_to_clean_text

logger = logging.getLogger(__name__)

MAX_CLEANED_TEXT_CHARACTERS = 30_000
MAX_EXTRACTION_ATTEMPTS = 2
CORRECTION_PROMPT = (
    "Your previous response was not valid for the required schema. Return only valid JSON "
    "with a non-empty description and nullable metadata fields where source text is absent."
)


class JobDescriptionExtractionError(RuntimeError):
    """Raised when cleaned text cannot produce a valid job description."""


async def enrich_saved_jobs_node(
    state: JobDescriptionState,
    runtime: Runtime[JobDescriptionContext],
) -> dict[str, int]:
    """Enrich saved job records that lack a non-empty description.

    Records are processed sequentially because the configured LLM client keeps
    conversation state. A fetch or model failure is recorded on its own job and
    does not prevent later records from being attempted.
    """
    counters = {
        "processed_count": 0,
        "skipped_count": 0,
        "succeeded_count": 0,
        "failed_count": 0,
    }
    data_directory = state["data_directory"]
    if not data_directory.exists():
        logger.info("Job data directory does not exist: %s", data_directory)
        return counters

    for record_path in sorted(data_directory.glob("job_*.json")):
        payload = _read_job_record(record_path)
        if payload is None:
            continue
        if _has_description(payload):
            counters["skipped_count"] += 1
            continue

        counters["processed_count"] += 1
        input_truncated = False
        try:
            url = _job_url(payload)
            raw_html = await fetch_html(url)
            cleaned_text = html_to_clean_text(raw_html)
            if not cleaned_text:
                raise JobDescriptionExtractionError("Job posting contained no usable text.")

            input_truncated = len(cleaned_text) > MAX_CLEANED_TEXT_CHARACTERS
            model_input = cleaned_text[:MAX_CLEANED_TEXT_CHARACTERS]
            details = _extract_job_description(runtime.context.llm_client, model_input)
        except (HtmlFetchError, JobDescriptionExtractionError, ValueError) as error:
            _set_scrape_failure(payload, str(error), input_truncated)
            _write_failure_record(record_path, payload)
            counters["failed_count"] += 1
            logger.warning("Could not enrich %s: %s", record_path.name, error)
            continue
        except Exception as error:  # Model providers can raise provider-specific exceptions.
            _set_scrape_failure(payload, f"Description extraction failed: {error}", input_truncated)
            _write_failure_record(record_path, payload)
            counters["failed_count"] += 1
            logger.exception("Unexpected enrichment failure for %s", record_path.name)
            continue

        payload["scrape"] = {
            "status": "succeeded",
            "error": None,
            "details": details.model_dump(mode="json"),
            "input_truncated": input_truncated,
        }
        try:
            _write_job_record(record_path, payload)
        except OSError as error:
            counters["failed_count"] += 1
            logger.error("Could not save enrichment result for %s: %s", record_path.name, error)
        else:
            counters["succeeded_count"] += 1

    return counters


def _extract_job_description(llm_client: LLMClient, cleaned_text: str) -> JobDescription:
    """Prompt one reset model conversation and retry a malformed response once."""
    # Setting the prompt resets LangChainChatClient history before each posting.
    llm_client.set_system_prompt(JOB_SEARCH_DESCRIPTION_EXTRACTION_PROMPT)
    response = llm_client.prompt(cleaned_text)
    details = _validated_description(response)
    if details is not None:
        return details

    retry_response = llm_client.prompt(CORRECTION_PROMPT)
    details = _validated_description(retry_response)
    if details is None:
        raise JobDescriptionExtractionError(
            f"LLM did not return a valid description after {MAX_EXTRACTION_ATTEMPTS} attempts."
        )
    return details


def _validated_description(response: str | None) -> JobDescription | None:
    """Strip an optional fence and validate a model response."""
    if not isinstance(response, str) or not response.strip():
        return None
    return validate_job_description(strip_json_fence(response))


def _read_job_record(record_path: Path) -> dict[str, Any] | None:
    """Load one object-shaped saved record, logging malformed files for review."""
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        logger.warning("Skipping unreadable job record %s: %s", record_path, error)
        return None
    if not isinstance(payload, dict):
        logger.warning("Skipping non-object job record %s", record_path)
        return None
    return payload


def _has_description(payload: dict[str, Any]) -> bool:
    """Return whether a record already has a non-blank extracted description."""
    scrape = payload.get("scrape")
    if not isinstance(scrape, dict):
        return False
    details = scrape.get("details")
    if not isinstance(details, dict):
        return False
    description = details.get("description")
    return isinstance(description, str) and bool(description.strip())


def _job_url(payload: dict[str, Any]) -> str:
    """Return the source URL or raise a record-specific enrichment error."""
    job = payload.get("job")
    url = job.get("url") if isinstance(job, dict) else None
    if not isinstance(url, str) or not url.strip():
        raise JobDescriptionExtractionError("Saved job record does not contain a usable job URL.")
    return url


def _set_scrape_failure(payload: dict[str, Any], error: str, input_truncated: bool) -> None:
    """Replace a record's scrape section with a retryable failure result."""
    payload["scrape"] = {
        "status": "failed",
        "error": error,
        "details": None,
        "input_truncated": input_truncated,
    }


def _write_failure_record(record_path: Path, payload: dict[str, Any]) -> None:
    """Try to persist a failure without stopping later batch records on I/O errors."""
    try:
        _write_job_record(record_path, payload)
    except OSError as write_error:
        logger.error("Could not save enrichment failure for %s: %s", record_path.name, write_error)


def _write_job_record(record_path: Path, payload: dict[str, Any]) -> None:
    """Persist one enrichment result using the established record format."""
    record_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
