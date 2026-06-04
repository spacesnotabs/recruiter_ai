"""LangGraph workflow for job search parameter extraction."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.llms.base import LLMClient
from agent.workflows.job_search.nodes import llm_call_node, prompt_user_node, run_job_search_query, llm_returned_invalid_json
from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from agent.workflows.job_search.state import JobSearchState, JobSearchContext
from agent.workflows.job_search.validation import validate_job_search_query
from typing import Literal
import json

from enum import Enum

"""Validation results for LLM responses in the job search workflow."""
class ValidationResult(Enum):
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
    """
    Validate whether the LLM response is valid JSON and matches the expected format for job search queries. 
    Args:
        message: the string response from the LLM to validate
    Returns:
        A ValidationResult indicating the outcome.
    """
    # is the response valid json?
    try:
        last_message_json = json.loads(message)
    except json.JSONDecodeError:
        return ValidationResult.INVALID_JSON

    # did the user supply enough information to create a query?
    complete: bool = last_message_json.get("complete", False)
    if not complete:
        return ValidationResult.INCOMPLETE_QUERY
 
    # did the LLM respond with a complete valid job search query?
    is_valid: bool = validate_job_search_query(message)
    if not is_valid:
        return ValidationResult.INVALID_QUERY

    return ValidationResult.VALID_QUERY
 