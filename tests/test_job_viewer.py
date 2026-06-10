"""Unit tests for the local saved-job web viewer."""

from __future__ import annotations

import json
from pathlib import Path

from job_viewer import load_saved_jobs, render_page


def _write_job(
    data_dir: Path,
    filename: str,
    title: str,
    company: str,
    description: str = "Build useful software.",
) -> None:
    """Write a minimal saved job record for viewer tests."""
    payload = {
        "job": {
            "title": title,
            "company_name": company,
            "posted_at": "2026-06-09T08:06:48.632000Z",
            "locations": ["Remote"],
            "required_skills": ["Python"],
            "url": "https://example.com/job",
        },
        "scrape": {
            "status": "succeeded",
            "error": None,
            "details": {"description": description},
        },
    }
    (data_dir / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_load_saved_jobs_sorts_by_company_and_title(tmp_path: Path) -> None:
    """Saved jobs are sorted predictably for browsing."""
    _write_job(tmp_path, "job_z.json", "Developer", "Zulu")
    _write_job(tmp_path, "job_a.json", "Architect", "Alpha")
    _write_job(tmp_path, "job_b.json", "Backend Engineer", "Alpha")

    jobs = load_saved_jobs(tmp_path)

    assert [(job.company, job.title) for job in jobs] == [
        ("Alpha", "Architect"),
        ("Alpha", "Backend Engineer"),
        ("Zulu", "Developer"),
    ]


def test_load_saved_jobs_keeps_malformed_records_visible(tmp_path: Path) -> None:
    """Malformed generated records are shown with a readable error."""
    (tmp_path / "job_broken.json").write_text("{not-json", encoding="utf-8")

    jobs = load_saved_jobs(tmp_path)

    assert len(jobs) == 1
    assert jobs[0].payload is None
    assert jobs[0].error


def test_render_page_selects_requested_job_and_escapes_content(tmp_path: Path) -> None:
    """The requested role is active and saved text cannot inject HTML."""
    _write_job(tmp_path, "job_first.json", "First Role", "Alpha")
    _write_job(
        tmp_path,
        "job_second.json",
        "Second <Role>",
        "Beta",
        '<script>alert("no")</script>',
    )

    page = render_page(load_saved_jobs(tmp_path), "job_second.json")

    assert "Second &lt;Role&gt;" in page
    assert "&lt;script&gt;alert(&quot;no&quot;)&lt;/script&gt;" in page
    assert '<script>alert("no")</script>' not in page
    assert (
        'class="job-link active" href="/?job=job_second.json&amp;sort=company"'
        in page
    )
    assert "Raw saved record" in page
    assert "June 9, 2026 at 8:06 AM UTC" in page


def test_render_page_includes_client_side_sort_options(tmp_path: Path) -> None:
    """The sidebar offers common role and posting-date sort orders."""
    _write_job(tmp_path, "job_first.json", "First Role", "Alpha")

    page = render_page(load_saved_jobs(tmp_path))

    assert '<select id="sort"' in page
    assert "Company: A-Z" in page
    assert "Role: A-Z" in page
    assert "Posted: Newest first" in page
    assert "Posted: Oldest first" in page
    assert 'data-posted="1780992408.632"' in page


def test_render_page_preserves_selected_sort_in_options_and_links(tmp_path: Path) -> None:
    """Navigating to another role retains the current sidebar sort."""
    _write_job(tmp_path, "job_first.json", "First Role", "Alpha")
    _write_job(tmp_path, "job_second.json", "Second Role", "Beta")

    page = render_page(load_saved_jobs(tmp_path), "job_first.json", "posted-desc")

    assert '<option value="posted-desc" selected>Posted: Newest first</option>' in page
    assert 'href="/?job=job_second.json&amp;sort=posted-desc"' in page
    assert "applySort();" in page


def test_render_page_ignores_unknown_sort_value(tmp_path: Path) -> None:
    """Unknown query-string sort values fall back to company order."""
    _write_job(tmp_path, "job_first.json", "First Role", "Alpha")

    page = render_page(load_saved_jobs(tmp_path), selected_sort="unexpected")

    assert '<option value="company" selected>Company: A-Z</option>' in page
    assert "sort=company" in page


def test_render_page_handles_empty_directory() -> None:
    """An empty data directory produces a useful start state."""
    page = render_page([])

    assert "No saved jobs yet" in page
    assert "0 saved roles" in page
