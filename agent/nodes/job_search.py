"""Proof-of-concept LangGraph nodes for collecting and parsing job searches."""

from __future__ import annotations

from langchain.messages import AIMessage, HumanMessage

from agent.agent_controller import AgentController
from agent.state import MessageState


controller: AgentController | None = None


def set_controller(agent_controller: AgentController) -> None:
    """Set the model controller used by the proof-of-concept LLM node."""
    global controller
    controller = agent_controller


def prompt_user_node(state: MessageState) -> dict[str, list[HumanMessage]]:
    """Read one user prompt from stdin and append it to workflow messages."""
    prompt: str = input("YOU: ")
    return {"messages": [HumanMessage(content=prompt)]}


def llm_call_node(state: MessageState) -> dict[str, list[AIMessage]] | None:
    """Prompt the configured LLM with the latest user message."""
    if controller is not None:
        response: str | None = controller.prompt_model(state["messages"][-1].text)
        print(f"AI: {response}")
        return {"messages": [AIMessage(content=response)]}

    return None
