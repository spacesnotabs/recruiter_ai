"""Behavior tests for saved job-description enrichment."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent.llms.base import LLMClient
from agent.workflows.job_description.workflow import run_job_description_workflow
from tools.web_scraping import HtmlFetchError


class FakeLLMClient(LLMClient):
    """Scripted LLM client that exposes prompts for workflow assertions."""

    def __init__(self, responses: list[str | None]) -> None:
        super().__init__("test-model")
        self.responses = responses
        self.prompts: list[str] = []
        self.system_prompt_count = 0

    def set_system_prompt(self, prompt: str) -> None:
        """Record each reset requested by the workflow."""
        super().set_system_prompt(prompt)
        self.system_prompt_count += 1

    def prompt(self, prompt: str) -> str | None:
        """Return scripted model output in call order."""
        self.prompts.append(prompt)
        return self.responses.pop(0)


def _write_record(
    path: Path,
    *,
    url: str = "https://example.test/jobs/1",
    scrape: dict | None = None,
) -> None:
    """Create a representative generated job record."""
    path.write_text(
        json.dumps(
            {
                "source": "job_data_lake",
                "source_job_id": "example",
                "job": {"title": "Engineer", "url": url},
                "scrape": scrape
                or {"status": "pending", "error": None, "details": None, "input_truncated": False},
            }
        ),
        encoding="utf-8",
    )


def test_enrichment_retries_invalid_response_and_skips_existing_description(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Malformed output gets one correction while completed records remain untouched."""
    pending_path = tmp_path / "job_pending.json"
    completed_path = tmp_path / "job_complete.json"
    _write_record(pending_path)
    _write_record(
        completed_path,
        scrape={
            "status": "succeeded",
            "error": None,
            "details": {"description": "Already saved."},
            "input_truncated": False,
        },
    )

    async def fake_fetch_html(url: str) -> str:
        return "<main><p>Build reliable services.</p></main>"

    monkeypatch.setattr("agent.workflows.job_description.nodes.fetch_html", fake_fetch_html)
    llm_client = FakeLLMClient([
        "not JSON",
        '{"description": "Build reliable services.", "title": null, "salary": null, "location": null}',
    ])

    summary = asyncio.run(run_job_description_workflow(llm_client, tmp_path))

    saved = json.loads(pending_path.read_text(encoding="utf-8"))
    assert summary.processed_count == 1
    assert summary.skipped_count == 1
    assert summary.succeeded_count == 1
    assert summary.failed_count == 0
    assert saved["scrape"]["status"] == "succeeded"
    assert saved["scrape"]["details"]["description"] == "Build reliable services."
    assert llm_client.system_prompt_count == 1
    assert len(llm_client.prompts) == 2


def test_enrichment_records_fetch_failure_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """One inaccessible posting does not prevent a later record from succeeding."""
    blocked_path = tmp_path / "job_blocked.json"
    successful_path = tmp_path / "job_successful.json"
    _write_record(blocked_path, url="https://example.test/blocked")
    _write_record(successful_path, url="https://example.test/available")

    async def fake_fetch_html(url: str) -> str:
        if url.endswith("blocked"):
            raise HtmlFetchError("blocked")
        return "<p>Build products.</p>"

    monkeypatch.setattr("agent.workflows.job_description.nodes.fetch_html", fake_fetch_html)
    llm_client = FakeLLMClient(['{"description": "Build products."}'])

    summary = asyncio.run(run_job_description_workflow(llm_client, tmp_path))

    blocked = json.loads(blocked_path.read_text(encoding="utf-8"))
    successful = json.loads(successful_path.read_text(encoding="utf-8"))
    assert summary.processed_count == 2
    assert summary.failed_count == 1
    assert summary.succeeded_count == 1
    assert blocked["scrape"]["status"] == "failed"
    assert blocked["scrape"]["error"] == "blocked"
    assert successful["scrape"]["status"] == "succeeded"


def test_enrichment_records_failure_after_second_invalid_model_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A second invalid response is stored as a retryable per-job failure."""
    record_path = tmp_path / "job_invalid.json"
    _write_record(record_path)

    async def fake_fetch_html(url: str) -> str:
        return "<p>Build systems.</p>"

    monkeypatch.setattr("agent.workflows.job_description.nodes.fetch_html", fake_fetch_html)
    summary = asyncio.run(run_job_description_workflow(FakeLLMClient(["{}", "{}"]), tmp_path))

    saved = json.loads(record_path.read_text(encoding="utf-8"))
    assert summary.failed_count == 1
    assert saved["scrape"]["status"] == "failed"
    assert "after 2 attempts" in saved["scrape"]["error"]


def test_enrichment_marks_truncated_model_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The persisted record identifies when model input was capped."""
    record_path = tmp_path / "job_large.json"
    _write_record(record_path)

    async def fake_fetch_html(url: str) -> str:
        return f"<p>{'x' * 30_001}</p>"

    monkeypatch.setattr("agent.workflows.job_description.nodes.fetch_html", fake_fetch_html)
    llm_client = FakeLLMClient(['{"description": "Extracted text."}'])

    asyncio.run(run_job_description_workflow(llm_client, tmp_path))

    saved = json.loads(record_path.read_text(encoding="utf-8"))
    assert len(llm_client.prompts[0]) == 30_000
    assert saved["scrape"]["input_truncated"] is True
