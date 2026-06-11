"""Utilities for normalizing JSON text returned by language models."""

from __future__ import annotations


def strip_json_fence(value: str) -> str:
    """Remove an optional Markdown code fence surrounding an entire response.

    The helper accepts fences labeled ``json`` as well as unlabeled fences.
    The JSON may begin on the same line as the opening fence. Text without a
    complete surrounding fence is returned unchanged except for leading and
    trailing whitespace.

    Args:
        value: Raw text that may contain a fenced JSON document.

    Returns:
        The normalized JSON text without an enclosing Markdown code fence.
    """
    text = value.strip()
    if not text.startswith("```") or not text.endswith("```") or len(text) <= 6:
        return text

    content = text[3:-3].strip()
    if content.lower().startswith("json"):
        after_label = content[4:]
        if not after_label or after_label[0].isspace() or after_label[0] in "[{":
            content = after_label.strip()

    return content
