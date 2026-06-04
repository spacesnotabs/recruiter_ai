"""Unit tests for job search workflow routing helpers."""

from __future__ import annotations

import json

from langchain.messages import AIMessage

from agent.workflows.job_search.validation import ValidationResult
from agent.workflows.job_search.workflow import (
    _validate_json,
    validate_llm_response_node,
    validate_llm_response_edge,
)


def test_validate_json_rejects_malformed_llm_response() -> None:
    """Malformed model text is classified before schema validation."""
    validation_result, job_search_query = _validate_json("not json")

    assert validation_result is ValidationResult.INVALID_JSON
    assert job_search_query is None


def test_validate_json_routes_incomplete_query_to_user_prompt() -> None:
    """Incomplete model JSON requests more user input."""
    raw_text = json.dumps({"response": "Which role are you looking for?", "complete": False})

    validation_result, job_search_query = _validate_json(raw_text)

    assert validation_result is ValidationResult.INCOMPLETE_QUERY
    assert job_search_query is None


def test_validate_json_rejects_complete_json_with_wrong_shape() -> None:
    """Complete JSON without the required query fields is invalid."""
    raw_text = json.dumps({"response": "Searching now.", "complete": True})

    validation_result, job_search_query = _validate_json(raw_text)

    assert validation_result is ValidationResult.INVALID_QUERY
    assert job_search_query is None


def test_validate_llm_response_node_returns_valid_query_for_state() -> None:
    """Valid complete job search JSON is parsed into workflow state."""
    raw_text = json.dumps(
        {
            "response": "Searching for backend engineering jobs.",
            "complete": True,
            "keywords": "backend engineer",
            "job_function": "eng",
            "salary_min": 120000,
            "remote_type": "fully_remote",
            "location": "Seattle",
        }
    )

    update = validate_llm_response_node(
        {"messages": [AIMessage(content=raw_text)], "job_search_query": None, "validation_result": None}
    )

    assert update["validation_result"] is ValidationResult.VALID_QUERY
    assert update["job_search_query"].keywords == "backend engineer"


def test_validate_llm_response_edge_routes_valid_query_to_search() -> None:
    """A stored valid validation result transitions to the search node."""
    next_node = validate_llm_response_edge(
        {"messages": [], "job_search_query": None, "validation_result": ValidationResult.VALID_QUERY}
    )

    assert next_node == "run_job_search_query"
