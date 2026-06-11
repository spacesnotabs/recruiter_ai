"""Unit tests for language-model JSON text normalization."""

from __future__ import annotations

import pytest

from tools.json_text import strip_json_fence


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ('```json\n{"complete": true}\n```', '{"complete": true}'),
        ('```json {"complete": true}\n```', '{"complete": true}'),
        ('```json {"complete": true} ```', '{"complete": true}'),
        ('```json{"complete": true}```', '{"complete": true}'),
        ('```\n{"complete": true}\n```', '{"complete": true}'),
        ('``` {"complete": true} ```', '{"complete": true}'),
        ('  {"complete": true}  ', '{"complete": true}'),
        ('```json\n{"complete": true}', '```json\n{"complete": true}'),
        ('Model output:\n```json\n{"complete": true}\n```', 'Model output:\n```json\n{"complete": true}\n```'),
    ],
)
def test_strip_json_fence_normalizes_only_complete_surrounding_fences(
    raw_text: str,
    expected: str,
) -> None:
    """Only a complete fence around the entire response is removed."""
    assert strip_json_fence(raw_text) == expected
