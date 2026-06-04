"""Unit tests for job search workflow routing helpers."""

from __future__ import annotations

import json

from langchain.messages import AIMessage

from agent.workflows.job_search.workflow import (
    ValidationResult,
    _validate_json,
    validate_llm_response_edge,
)


def test_validate_json_rejects_malformed_llm_response() -> None:
    """Malformed model text is classified before schema validation."""
    assert _validate_json("not json") is ValidationResult.INVALID_JSON


def test_validate_json_routes_incomplete_query_to_user_prompt() -> None:
    """Incomplete model JSON requests more user input."""
    raw_text = json.dumps({"response": "Which role are you looking for?", "complete": False})

    assert _validate_json(raw_text) is ValidationResult.INCOMPLETE_QUERY


def test_validate_json_rejects_complete_json_with_wrong_shape() -> None:
    """Complete JSON without the required query fields is invalid."""
    raw_text = json.dumps({"response": "Searching now.", "complete": True})

    assert _validate_json(raw_text) is ValidationResult.INVALID_QUERY


def test_validate_llm_response_edge_routes_valid_query_to_search() -> None:
    """Valid complete job search JSON transitions to the search node."""
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

    next_node = validate_llm_response_edge({"messages": [AIMessage(content=raw_text)]})

    assert next_node == "run_job_search_query"

