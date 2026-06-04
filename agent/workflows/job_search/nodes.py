"""Proof-of-concept LangGraph nodes for collecting and parsing job searches."""

from __future__ import annotations

import json

from langchain.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from agent.workflows.job_search.state import JobSearchContext, JobSearchState
from agent.workflows.job_search.validation import JobSearchQuery, ValidationResult, validate_job_search_query
from models.job_search_params import JobSearchParams


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


def handle_job_search_results_node(state: JobSearchState) -> dict[str, list[HumanMessage]] | None:
    """Format and return job search results to the user."""
    job_search_results = state["job_search_results"]
    if job_search_results is None:
        raise ValueError("Job search results are required to format a response to the user.")

    formatted_results = json.dumps(job_search_results, indent=2)
    print(f"AI: Here are the job search results:\n{formatted_results}")
    return None

def _job_search_query_to_params(job_search_query: JobSearchQuery) -> JobSearchParams:
    """Convert the LLM-facing query schema into API-facing search parameters."""
    return JobSearchParams(
        keywords=job_search_query.keywords,
        job_function=job_search_query.job_function,
        location=job_search_query.location,
        salary_min=job_search_query.salary_min,
        remote_type=job_search_query.remote_type,
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
