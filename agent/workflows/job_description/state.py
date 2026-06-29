"""State and context types for saved job-description enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from typing_extensions import TypedDict

from agent.llms.base import LLMClient


@dataclass
class JobDescriptionContext:
    """Runtime dependencies used by the description-enrichment workflow."""

    llm_client: LLMClient


class JobDescriptionState(TypedDict):
    """Batch counters and input location shared by the enrichment graph."""

    data_directory: Path
    processed_count: int
    skipped_count: int
    succeeded_count: int
    failed_count: int
