"""Callable LangGraph workflow for enriching saved job descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agent.llms.base import LLMClient
from agent.workflows.job_description.nodes import enrich_saved_jobs_node
from agent.workflows.job_description.state import JobDescriptionContext, JobDescriptionState

DEFAULT_JOB_DATA_DIRECTORY = Path(__file__).resolve().parents[3] / "data"


@dataclass(frozen=True)
class JobDescriptionEnrichmentSummary:
    """Counts produced by one saved-job description enrichment run."""

    processed_count: int
    skipped_count: int
    succeeded_count: int
    failed_count: int


def build_job_description_workflow():
    """Build the single-batch-node graph for saved job enrichment."""
    workflow = StateGraph(JobDescriptionState, context_schema=JobDescriptionContext)
    workflow.add_node("enrich_saved_jobs", enrich_saved_jobs_node)
    workflow.add_edge(START, "enrich_saved_jobs")
    workflow.add_edge("enrich_saved_jobs", END)
    return workflow.compile()


async def run_job_description_workflow(
    llm_client: LLMClient,
    data_directory: Path = DEFAULT_JOB_DATA_DIRECTORY,
) -> JobDescriptionEnrichmentSummary:
    """Enrich descriptions for saved jobs that are not already complete.

    Args:
        llm_client: Configured model client used for extraction.
        data_directory: Directory holding generated ``job_*.json`` records.

    Returns:
        Counts for processed, skipped, succeeded, and failed records.
    """
    app = build_job_description_workflow()
    state: JobDescriptionState = {
        "data_directory": data_directory,
        "processed_count": 0,
        "skipped_count": 0,
        "succeeded_count": 0,
        "failed_count": 0,
    }
    result = await app.ainvoke(state, context=JobDescriptionContext(llm_client=llm_client))
    return JobDescriptionEnrichmentSummary(
        processed_count=result["processed_count"],
        skipped_count=result["skipped_count"],
        succeeded_count=result["succeeded_count"],
        failed_count=result["failed_count"],
    )
