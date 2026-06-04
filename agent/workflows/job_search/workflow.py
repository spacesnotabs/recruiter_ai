"""LangGraph workflow for job search parameter extraction."""

from __future__ import annotations

import json
from enum import Enum
from typing import Literal

from langgraph.graph import END, START, StateGraph

from agent.llms.base import LLMClient
from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from agent.workflows.job_search.nodes import (
    llm_call_node,
    llm_returned_invalid_json,
    prompt_user_node,
    run_job_search_query,
)
from agent.workflows.job_search.state import JobSearchContext, JobSearchState
from agent.workflows.job_search.validation import validate_job_search_query


class ValidationResult(Enum):
    """Validation outcomes used to route the job search workflow graph."""

    INVALID_JSON = "invalid_json"
    INCOMPLETE_QUERY = "incomplete_query"
    INVALID_QUERY = "invalid_query"
    VALID_QUERY = "valid_query"


def build_job_search_workflow():
    """Build the job search workflow graph."""
    workflow = StateGraph(JobSearchState, context_schema=JobSearchContext)

    workflow.add_node("prompt_user", prompt_user_node)
    workflow.add_node("llm_call", llm_call_node)
    workflow.add_node("llm_returned_invalid_json", llm_returned_invalid_json)
    workflow.add_node("run_job_search_query", run_job_search_query)

    workflow.add_edge(START, "prompt_user")
    workflow.add_edge("prompt_user", "llm_call")
    workflow.add_conditional_edges("llm_call", validate_llm_response_edge)
    workflow.add_edge("llm_returned_invalid_json", "llm_call")
    workflow.add_edge("run_job_search_query", END)

    return workflow.compile()


async def run_job_search_workflow(llm_client: LLMClient) -> int:
    """Run one job search workflow interaction."""
    llm_client.set_system_prompt(prompt=JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT)
    app = build_job_search_workflow()

    messages = []
    state: JobSearchState = JobSearchState(messages=messages)
    app.invoke(input=state, context=JobSearchContext(llm_client=llm_client))

    return 1

def validate_llm_response_edge(state: JobSearchState) -> Literal["llm_returned_invalid_json", "prompt_user", "run_job_search_query"]:
    """Validate the LLM response and determine the next node to transition to."""
    messages = state["messages"]
    last_message: str = messages[-1].text

    json_validation_result: ValidationResult = _validate_json(last_message)

    if json_validation_result == ValidationResult.INVALID_JSON:
        print("LLM returned invalid JSON.")
        return "llm_returned_invalid_json"
    elif json_validation_result == ValidationResult.INCOMPLETE_QUERY:
        print("LLM indicated the query is not complete. Prompting user for more information.")
        return "prompt_user"
    elif json_validation_result == ValidationResult.INVALID_QUERY:
        print("LLM returned JSON that was valid but did not match the expected format for job search queries.")
        return "llm_returned_invalid_json"
    else:
        print("LLM returned a complete and valid job search query. Running the query.")
        return "run_job_search_query"

def _validate_json(message: str) -> ValidationResult:
    """Validate an LLM response against job search workflow requirements.

    Args:
        message: Raw LLM response text to parse and validate.

    Returns:
        A ``ValidationResult`` indicating whether the text was malformed,
        incomplete, structurally invalid, or ready to query.
    """
    try:
        last_message_json = json.loads(message)
    except json.JSONDecodeError:
        return ValidationResult.INVALID_JSON

    complete: bool = last_message_json.get("complete", False)
    if not complete:
        return ValidationResult.INCOMPLETE_QUERY
 
    is_valid: bool = validate_job_search_query(message)
    if not is_valid:
        return ValidationResult.INVALID_QUERY

    return ValidationResult.VALID_QUERY
 
