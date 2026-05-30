"""Proof-of-concept LangGraph nodes for collecting and parsing job searches."""

from __future__ import annotations

from langchain.messages import AIMessage, HumanMessage

from agent.factory import ModelFactory
from agent.state import MessageState


model_factory: ModelFactory | None = None


def set_model_factory(factory: ModelFactory) -> None:
    """Set the model factory used by the proof-of-concept LLM node."""
    global model_factory
    model_factory = factory


def prompt_user_node(state: MessageState) -> dict[str, list[HumanMessage]]:
    """Read one user prompt from stdin and append it to workflow messages."""
    prompt: str = input("YOU: ")
    return {"messages": [HumanMessage(content=prompt)]}


def llm_call_node(state: MessageState) -> dict[str, list[AIMessage]] | None:
    """Prompt the configured LLM with the latest user message."""
    if model_factory is not None:
        response: str | None = model_factory.prompt_model(state["messages"][-1].text)
        print(f"AI: {response}")
        return {"messages": [AIMessage(content=response)]}

    return None
