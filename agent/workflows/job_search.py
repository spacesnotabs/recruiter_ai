"""Proof-of-concept LangGraph workflow for job search parameter extraction."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.llms.base import LLMClient
from agent.nodes.job_search import llm_call_node, prompt_user_node, set_model_client
from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from agent.state import MessageState


def build_job_search_workflow(model_client: LLMClient):
    """Build the proof-of-concept job search workflow graph."""
    set_model_client(model_client)

    workflow = StateGraph(MessageState)

    workflow.add_node("prompt_user", prompt_user_node)
    workflow.add_node("llm_call", llm_call_node)

    workflow.add_edge(START, "prompt_user")
    workflow.add_edge("prompt_user", "llm_call")
    workflow.add_edge("llm_call", END)

    return workflow.compile()


async def run_job_search_workflow(model_client: LLMClient) -> int:
    """Run one proof-of-concept job search workflow interaction."""
    model_client.set_system_prompt(prompt=JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT)
    app = build_job_search_workflow(model_client)

    messages = []
    state: MessageState = MessageState(messages=messages)
    app.invoke(input=state)

    return 1
