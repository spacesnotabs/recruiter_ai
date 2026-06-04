"""LangGraph workflow for job search parameter extraction."""

from __future__ import annotations

import json
from typing import Literal

from langgraph.graph import END, START, StateGraph

from agent.llms.base import LLMClient
from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from agent.workflows.job_search.nodes import (
    llm_call_node,
    llm_returned_invalid_json_node,
    prompt_user_node,
    validate_llm_response_node,
    run_job_search_query_node,
)
from agent.workflows.job_search.state import JobSearchContext, JobSearchState
from agent.workflows.job_search.validation import ValidationResult


def build_job_search_workflow():
    """Build the job search workflow graph."""
    workflow = StateGraph(JobSearchState, context_schema=JobSearchContext)

    workflow.add_node("prompt_user", prompt_user_node)
    workflow.add_node("llm_call", llm_call_node)
    workflow.add_node("validate_llm_response", validate_llm_response_node)
    workflow.add_node("llm_returned_invalid_json", llm_returned_invalid_json_node)
    workflow.add_node("run_job_search_query", run_job_search_query_node)

    workflow.add_edge(START, "prompt_user")
    workflow.add_edge("prompt_user", "llm_call")
    workflow.add_edge("llm_call", "validate_llm_response")
    workflow.add_conditional_edges("validate_llm_response", validate_llm_response_edge)
    workflow.add_edge("llm_returned_invalid_json", "llm_call")
    workflow.add_edge("run_job_search_query", END)

    return workflow.compile()


async def run_job_search_workflow(llm_client: LLMClient) -> int:
    """Run one job search workflow interaction."""
    llm_client.set_system_prompt(prompt=JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT)
    app = build_job_search_workflow()

    messages = []
    state: JobSearchState = JobSearchState(messages=messages, job_search_query=None, validation_result=None)
    app.invoke(input=state, context=JobSearchContext(llm_client=llm_client))

    return 1


def validate_llm_response_edge(state: JobSearchState) -> Literal["llm_returned_invalid_json", "prompt_user", "run_job_search_query"]:
    """Route the workflow based on the stored validation result."""
    json_validation_result = state["validation_result"]

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


