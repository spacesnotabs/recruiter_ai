"""Proof-of-concept LangGraph nodes for collecting and parsing job searches."""

from __future__ import annotations

from langchain.messages import AIMessage, HumanMessage

from agent.llms.base import LLMClient
from agent.state import MessageState
import json


model_client: LLMClient | None = None


def set_model_client(client: LLMClient) -> None:
    """Set the model client used by the proof-of-concept LLM node."""
    global model_client
    model_client = client


def prompt_user_node(state: MessageState) -> dict[str, list[HumanMessage]]:
    """Read one user prompt from stdin and append it to workflow messages."""
    # Print last response from AI if applicable
    messages = state["messages"]
    if messages:
        last_message = state["messages"][-1]
        if type(last_message) == AIMessage:
            message_json = json.loads(last_message.text)
            print(f"AI {message_json.get('response')}")

    prompt: str = input("YOU: ")
    return {"messages": [HumanMessage(content=prompt)]}


def llm_call_node(state: MessageState) -> dict[str, list[AIMessage]] | None:
    """Prompt the configured LLM with the latest user message."""
    if model_client is not None:
        response: str | None = model_client.prompt(state["messages"][-1].text)
        print(f"AI: {response}")
        return {"messages": [AIMessage(content=response)]}

    return None

def llm_returned_invalid_json(state: MessageState) -> dict[str, list[HumanMessage]]:
    return {"messages": [HumanMessage(content="The JSON you returned was invalid. Please try again.")]}

def run_job_search_query(state: MessageState) -> dict[str, list[HumanMessage]] | None:
    #TODO
    print("Running job search query")
    return None
