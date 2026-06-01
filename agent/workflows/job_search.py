"""Proof-of-concept LangGraph workflow for job search parameter extraction."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.llms.base import LLMClient
from agent.nodes.job_search import llm_call_node, prompt_user_node, set_model_client, run_job_search_query, llm_returned_invalid_json
from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from agent.state import MessageState
from agent.validation import validate_job_search_query
from typing import Literal
import json


def build_job_search_workflow(model_client: LLMClient):
    """Build the proof-of-concept job search workflow graph."""
    set_model_client(model_client)

    workflow = StateGraph(MessageState)

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


async def run_job_search_workflow(model_client: LLMClient) -> int:
    """Run one proof-of-concept job search workflow interaction."""
    model_client.set_system_prompt(prompt=JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT)
    app = build_job_search_workflow(model_client)

    messages = []
    state: MessageState = MessageState(messages=messages)
    app.invoke(input=state)

    return 1

def validate_llm_response_edge(state: MessageState) -> Literal["llm_returned_invalid_json", "prompt_user", "run_job_search_query"]:
    messages = state["messages"]
    last_message: str = messages[-1].text

    try:
        last_message_json = json.loads(last_message)
    except json.JSONDecodeError:
        print("LLM returned invalid JSON.")
        return "llm_returned_invalid_json"
    
    # Did the user give enough information for a complete query?
    complete: bool = last_message_json.get("complete")
    if not complete:
        print("LLM indicated the query is not complete. Prompting user for more information.")
        return "prompt_user"
    
    # Did the LLM respond with a complete valid job search query?
    is_valid: bool = validate_job_search_query(last_message)
    if not is_valid:
        print("LLM returned JSON that did not match the expected format for job search queries.")
        return "llm_returned_invalid_json"
    
    # Job search query is complete
    print("LLM returned a complete and valid job search query. Running the query.")
    return "run_job_search_query"
