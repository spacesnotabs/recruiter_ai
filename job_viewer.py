"""Serve a small read-only web interface for locally saved job records."""

from __future__ import annotations

import argparse
import html
import json
import threading
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qs, quote, urlparse

DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_SORT = "company"
SORT_OPTIONS = {
    "company": "Company: A-Z",
    "title": "Role: A-Z",
    "posted-desc": "Posted: Newest first",
    "posted-asc": "Posted: Oldest first",
}


@dataclass(frozen=True)
class SavedJob:
    """A saved job record and the display metadata derived from it."""

    filename: str
    title: str
    company: str
    payload: dict[str, Any] | None
    error: str | None = None


def load_saved_jobs(data_dir: Path) -> list[SavedJob]:
    """Load saved job JSON files in title order.

    Invalid records remain visible in the interface with an error message so a
    malformed development artifact does not hide silently.

    Args:
        data_dir: Directory containing generated ``job_*.json`` files.

    Returns:
        Saved records sorted by company, title, and filename.
    """
    jobs: list[SavedJob] = []
    if not data_dir.exists():
        return jobs

    for path in data_dir.glob("job_*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("the top-level JSON value must be an object")
            job = payload.get("job")
            job_data = job if isinstance(job, dict) else {}
            title = _display_value(job_data.get("title"), "Untitled role")
            company = _display_value(job_data.get("company_name"), "Unknown company")
            jobs.append(SavedJob(path.name, title, company, payload))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            jobs.append(
                SavedJob(
                    filename=path.name,
                    title=path.stem.removeprefix("job_").replace("-", " ").title(),
                    company="Unreadable record",
                    payload=None,
                    error=str(exc),
                )
            )

    return sorted(
        jobs,
        key=lambda saved: (saved.company.casefold(), saved.title.casefold(), saved.filename),
    )


def render_page(
    jobs: Sequence[SavedJob],
    selected_filename: str | None = None,
    selected_sort: str = DEFAULT_SORT,
) -> str:
    """Render the complete job browser page.

    Args:
        jobs: Saved jobs available for selection.
        selected_filename: Filename requested in the ``job`` query parameter.
        selected_sort: Sort method requested in the ``sort`` query parameter.

    Returns:
        A self-contained HTML document.
    """
    selected = next((job for job in jobs if job.filename == selected_filename), None)
    if selected is None and jobs:
        selected = jobs[0]

    selected_sort = selected_sort if selected_sort in SORT_OPTIONS else DEFAULT_SORT
    list_items = "".join(
        _render_list_item(job, selected, selected_sort) for job in jobs
    )
    sort_options = "".join(
        f'<option value="{value}"{" selected" if value == selected_sort else ""}>'
        f"{label}</option>"
        for value, label in SORT_OPTIONS.items()
    )
    detail = _render_job_detail(selected) if selected else _render_empty_state()
    count_label = f"{len(jobs)} saved role{'s' if len(jobs) != 1 else ''}"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Saved Jobs</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172126;
      --muted: #647179;
      --paper: #f4f1e9;
      --panel: #fffdf8;
      --line: #dcd8cd;
      --accent: #177866;
      --accent-soft: #dceee8;
      --danger: #a33b32;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--paper); color: var(--ink); }}
    .layout {{ display: grid; grid-template-columns: minmax(260px, 340px) 1fr; min-height: 100vh; }}
    aside {{
      position: sticky; top: 0; height: 100vh; overflow: auto; padding: 28px 18px;
      background: #203238; color: white; border-right: 1px solid #14252a;
    }}
    h1 {{ margin: 0 0 4px; font-family: Georgia, serif; font-size: 1.8rem; font-weight: 600; }}
    .count {{ margin: 0 0 20px; color: #b8c7ca; font-size: .88rem; }}
    .controls {{ display: grid; gap: 9px; }}
    #search, #sort {{
      width: 100%; border: 1px solid #53666b; border-radius: 9px; padding: 10px 12px;
      background: #15272c; color: white; font: inherit; outline: none;
    }}
    #search:focus, #sort:focus {{ border-color: #71b9a8; box-shadow: 0 0 0 3px #71b9a833; }}
    .jobs {{ display: grid; gap: 8px; margin-top: 16px; }}
    .job-link {{
      display: block; padding: 12px; border-radius: 9px; color: white; text-decoration: none;
      border: 1px solid transparent; transition: background .12s ease;
    }}
    .job-link:hover {{ background: #2b444b; }}
    .job-link.active {{ background: var(--accent-soft); color: #17342e; }}
    .job-link strong, .job-link span {{ display: block; }}
    .job-link strong {{ font-size: .94rem; line-height: 1.3; }}
    .job-link span {{ margin-top: 4px; opacity: .72; font-size: .8rem; }}
    main {{ width: min(980px, 100%); padding: 48px clamp(24px, 5vw, 72px) 80px; }}
    .eyebrow {{ color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }}
    h2 {{ margin: 8px 0; font-family: Georgia, serif; font-size: clamp(2rem, 4vw, 3.35rem); line-height: 1.08; }}
    .company {{ margin: 0 0 24px; color: var(--muted); font-size: 1.1rem; }}
    .meta, .skills {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0; }}
    .pill {{ padding: 6px 10px; border-radius: 999px; background: var(--accent-soft); color: #245348; font-size: .82rem; }}
    .card {{ margin-top: 28px; padding: 24px; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); box-shadow: 0 8px 30px #2632380b; }}
    .card h3 {{ margin: 0 0 16px; font-size: 1rem; }}
    .facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 18px; }}
    .fact dt {{ color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; }}
    .fact dd {{ margin: 5px 0 0; }}
    .description {{ white-space: pre-wrap; line-height: 1.72; overflow-wrap: anywhere; }}
    .status-ok {{ color: var(--accent); }}
    .status-pending {{ color: var(--muted); }}
    .status-error, .error {{ color: var(--danger); }}
    a.external {{ color: var(--accent); font-weight: 650; }}
    details summary {{ cursor: pointer; color: var(--muted); }}
    pre {{ overflow: auto; max-height: 600px; padding: 16px; border-radius: 9px; background: #17272c; color: #e5eeee; font-size: .78rem; }}
    .empty {{ margin-top: 20vh; text-align: center; color: var(--muted); }}
    @media (max-width: 760px) {{
      .layout {{ display: block; }}
      aside {{ position: relative; height: auto; max-height: 42vh; }}
      main {{ padding-top: 32px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <h1>Saved Jobs</h1>
      <p class="count">{count_label}</p>
      <div class="controls">
        <input id="search" type="search" placeholder="Filter roles or companies..." aria-label="Filter saved jobs">
        <select id="sort" aria-label="Sort saved jobs">
          {sort_options}
        </select>
      </div>
      <nav class="jobs" aria-label="Saved jobs">{list_items}</nav>
    </aside>
    <main>{detail}</main>
  </div>
  <script>
    const search = document.querySelector("#search");
    const sort = document.querySelector("#sort");
    const jobList = document.querySelector(".jobs");
    search.addEventListener("input", () => {{
      const query = search.value.toLowerCase().trim();
      document.querySelectorAll(".job-link").forEach((item) => {{
        item.hidden = !item.dataset.search.includes(query);
      }});
    }});
    const applySort = () => {{
      const items = Array.from(document.querySelectorAll(".job-link"));
      const textCompare = (left, right, field) =>
        left.dataset[field].localeCompare(right.dataset[field], undefined, {{ sensitivity: "base" }});
      items.sort((left, right) => {{
        if (sort.value === "title") return textCompare(left, right, "title");
        if (sort.value.startsWith("posted-")) {{
          const leftPosted = Number(left.dataset.posted);
          const rightPosted = Number(right.dataset.posted);
          if (!leftPosted) return rightPosted ? 1 : 0;
          if (!rightPosted) return -1;
          return sort.value === "posted-asc"
            ? leftPosted - rightPosted
            : rightPosted - leftPosted;
        }}
        return textCompare(left, right, "company") || textCompare(left, right, "title");
      }});
      items.forEach((item) => {{
        const url = new URL(item.href);
        url.searchParams.set("sort", sort.value);
        item.href = `${{url.pathname}}${{url.search}}`;
        jobList.appendChild(item);
      }});
    }};
    sort.addEventListener("change", applySort);
    applySort();
  </script>
</body>
</html>"""


def make_handler(data_dir: Path) -> type[BaseHTTPRequestHandler]:
    """Create an HTTP handler bound to a particular job data directory."""

    class JobViewerHandler(BaseHTTPRequestHandler):
        """Serve the read-only job browser."""

        def do_GET(self) -> None:
            """Serve the browser page and reject unknown paths."""
            parsed = urlparse(self.path)
            if parsed.path != "/":
                self.send_error(404)
                return

            query = parse_qs(parsed.query)
            selected = query.get("job", [None])[0]
            selected_sort = query.get("sort", [DEFAULT_SORT])[0]
            body = render_page(
                load_saved_jobs(data_dir),
                selected,
                selected_sort,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            """Suppress routine local request logging."""

    return JobViewerHandler


def run_server(
    data_dir: Path = DEFAULT_DATA_DIR,
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = True,
) -> None:
    """Run the local job viewer until interrupted.

    Args:
        data_dir: Directory containing generated job JSON records.
        host: Interface on which the development server listens.
        port: TCP port on which the development server listens.
        open_browser: Whether to open the viewer in the default browser.
    """
    server = ThreadingHTTPServer((host, port), make_handler(data_dir))
    url = f"http://{host}:{server.server_port}/"
    print(f"Saved job viewer: {url}")
    print(f"Reading records from: {data_dir.resolve()}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.25, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    """Parse command-line options and run the local viewer."""
    parser = argparse.ArgumentParser(description="Browse saved recruiter AI job records.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    run_server(args.data_dir, args.host, args.port, not args.no_browser)


def _render_list_item(
    job: SavedJob,
    selected: SavedJob | None,
    selected_sort: str,
) -> str:
    active = " active" if selected and selected.filename == job.filename else ""
    search_text = html.escape(f"{job.title} {job.company}".casefold(), quote=True)
    job_data = (
        job.payload.get("job")
        if job.payload and isinstance(job.payload.get("job"), dict)
        else {}
    )
    posted = _timestamp_value(job_data.get("posted_at"))
    href = html.escape(
        f"/?job={quote(job.filename)}&sort={quote(selected_sort)}",
        quote=True,
    )
    return (
        f'<a class="job-link{active}" href="{href}" data-search="{search_text}" '
        f'data-title="{html.escape(job.title, quote=True)}" '
        f'data-company="{html.escape(job.company, quote=True)}" data-posted="{posted}">'
        f"<strong>{html.escape(job.title)}</strong>"
        f"<span>{html.escape(job.company)}</span></a>"
    )


def _render_job_detail(saved: SavedJob) -> str:
    if saved.payload is None:
        return (
            '<section class="empty"><h2>Unreadable record</h2>'
            f'<p class="error">{html.escape(saved.error or "Unknown error")}</p></section>'
        )

    payload = saved.payload
    job = payload.get("job") if isinstance(payload.get("job"), dict) else {}
    scrape = payload.get("scrape") if isinstance(payload.get("scrape"), dict) else {}
    details = scrape.get("details") if isinstance(scrape.get("details"), dict) else {}
    description = details.get("description") or "No scraped description is available."
    url = job.get("url")
    status = _display_value(scrape.get("status"), "unknown")
    status_class = (
        "status-ok" if status == "succeeded"
        else "status-pending" if status == "pending"
        else "status-error"
    )

    metadata = [
        *_as_strings(job.get("locations")),
        _prettify(job.get("remote_type")),
        _prettify(job.get("employment_type")),
        *_as_strings(job.get("seniority")),
    ]
    pills = "".join(
        f'<span class="pill">{html.escape(value)}</span>' for value in metadata if value
    )
    skills = "".join(
        f'<span class="pill">{html.escape(skill)}</span>'
        for skill in _as_strings(job.get("required_skills"))
    )
    link = (
        f'<a class="external" href="{html.escape(str(url), quote=True)}" '
        'target="_blank" rel="noreferrer">Open original posting</a>'
        if url
        else "Not available"
    )
    error = scrape.get("error")
    scrape_error = (
        f'<p class="error">{html.escape(str(error))}</p>' if error else ""
    )
    raw_json = html.escape(json.dumps(payload, indent=2, ensure_ascii=False))

    return f"""
      <div class="eyebrow">{html.escape(saved.filename)}</div>
      <h2>{html.escape(saved.title)}</h2>
      <p class="company">{html.escape(saved.company)}</p>
      <div class="meta">{pills}</div>
      <section class="card">
        <h3>At a glance</h3>
        <dl class="facts">
          {_fact("Posted", _format_posted_at(job.get("posted_at")))}
          {_fact("Countries", ", ".join(_as_strings(job.get("countries"))))}
          {_fact("Salary (USD)", _salary(job))}
          {_fact("Company size", job.get("employee_count"))}
          {_fact("Funding", job.get("funding"))}
          <div class="fact"><dt>Scrape status</dt><dd class="{status_class}">{html.escape(status)}</dd></div>
          <div class="fact"><dt>Source</dt><dd>{link}</dd></div>
        </dl>
        {scrape_error}
      </section>
      <section class="card">
        <h3>Required skills</h3>
        <div class="skills">{skills or "No skills listed."}</div>
      </section>
      <section class="card">
        <h3>Description</h3>
        <div class="description">{html.escape(str(description))}</div>
      </section>
      <section class="card">
        <details>
          <summary>Raw saved record</summary>
          <pre>{raw_json}</pre>
        </details>
      </section>"""


def _render_empty_state() -> str:
    return (
        '<section class="empty"><h2>No saved jobs yet</h2>'
        "<p>Run a job search first, then refresh this page.</p></section>"
    )


def _fact(label: str, value: object) -> str:
    return (
        '<div class="fact">'
        f"<dt>{html.escape(label)}</dt>"
        f"<dd>{html.escape(_display_value(value))}</dd>"
        "</div>"
    )


def _salary(job: dict[str, Any]) -> str:
    minimum = job.get("salary_min_usd")
    maximum = job.get("salary_max_usd")
    if minimum is None and maximum is None:
        return "Not listed"
    if minimum is not None and maximum is not None:
        return f"${minimum} - ${maximum}"
    return f"${minimum or maximum}"


def _format_posted_at(value: object) -> str:
    """Format an ISO posting timestamp as a readable UTC date and time."""
    parsed = _parse_timestamp(value)
    if parsed is None:
        return _display_value(value)
    utc_value = parsed.astimezone(timezone.utc)
    hour = utc_value.strftime("%I").lstrip("0") or "0"
    return (
        f"{utc_value.strftime('%B')} {utc_value.day}, {utc_value.year} "
        f"at {hour}:{utc_value.strftime('%M %p')} UTC"
    )


def _timestamp_value(value: object) -> float:
    """Return a sortable Unix timestamp, placing missing dates last."""
    parsed = _parse_timestamp(value)
    return parsed.timestamp() if parsed is not None else 0


def _parse_timestamp(value: object) -> datetime | None:
    """Parse a saved ISO timestamp, treating timestamps without offsets as UTC."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def _as_strings(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    if value is None:
        return []
    return [str(value)]


def _prettify(value: object) -> str:
    return str(value).replace("_", " ").title() if value else ""


def _display_value(value: object, fallback: str = "Not listed") -> str:
    return str(value) if value is not None and str(value) else fallback


if __name__ == "__main__":
    main()
