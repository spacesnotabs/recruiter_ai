"""State definitions for LangGraph-backed recruiter workflows."""

from __future__ import annotations

import operator
from typing import Annotated

from langchain.messages import AnyMessage
from typing_extensions import TypedDict


class MessageState(TypedDict):
    """Conversation state shared by the proof-of-concept LangGraph workflow."""

    messages: Annotated[list[AnyMessage], operator.add]
