"""Proof-of-concept LangGraph nodes for collecting and parsing job searches."""

from __future__ import annotations

from langchain.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from agent.workflows.job_search.state import JobSearchContext, JobSearchState
import json


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

def llm_returned_invalid_json(state: JobSearchState) -> dict[str, list[HumanMessage]]:
    """Append a retry instruction when the model response cannot be used."""
    return {"messages": [HumanMessage(content="The JSON you returned was invalid. Please try again.")]}


def run_job_search_query(state: JobSearchState) -> dict[str, list[HumanMessage]] | None:
    """Placeholder node for executing a validated job search query."""
    # TODO: Convert the validated JSON into JobSearchParams and call the API.
    print("Running job search query")
    return None
