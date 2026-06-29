# Agent Guide

This repository is intentionally small right now. Keep it that way until the
project needs more structure.

## Repository Shape

- `main.py`: thin entrypoint that runs the current recruiter AI workflow.
- `agent/`: LLM clients, prompts, and workflow packages. The current job search
  workflow lives in `agent/workflows/job_search/`.
- `api/`: Job Data Lake API code and response formatting helpers.
- `models/`: shared typed models. `models/job.py` validates Job Data Lake
  responses, while `models/job_search_params.py` represents outgoing filters.
- `tools/`: small local utilities such as dotenv reading and job description
  scraping.
- `tests/`: unit tests for API, model, tool, and workflow behavior.
- `data/`: generated local job records. The workflow creates this directory as
  needed; its contents are ignored by Git and must not be treated as source.
- `.env`: optional local secret file. Treat it as private and do not print it.

## Current Runtime Assumptions

- Use Python 3.12; the local virtual environment is `.venv`.
- Existing code depends on `httpx`, `beautifulsoup4`, `pydantic`,
  `langchain`, and `langgraph`.
- No `pyproject.toml`, lockfile, or test configuration is present yet.
- Prefer PowerShell-friendly commands when documenting local usage.

Useful commands from the repository root:

```powershell
.\.venv\Scripts\python.exe .\main.py
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe -m pytest
```

Set `OPENROUTER_API_KEY` and `JOB_DATA_LAKE_API_KEY` in `.env` for the current
workflow. The entrypoint reads these values from the repository-root `.env`
file and exits without running when either value is missing.

## Current Job Data Flow

1. The workflow validates LLM-produced search criteria.
2. `JobDataLakeClient.search_jobs()` fetches the `/v1/jobs` response and
   validates it as `JobDataLakeResponse`.
3. The result-handling node saves each API result to
   `data/job_<identifier>.json` with the complete Job Data Lake record and a
   pending scrape section.
4. The callable job-description workflow fetches saved job URLs sequentially,
   cleans HTML, and uses the LLM to fill missing descriptions. It caps model
   input at 30,000 cleaned-text characters and records whether truncation
   occurred.

`job_handle` is used for the local identifier when present. Jobs without a
handle use a deterministic hash of the URL. Local JSON files are temporary
persistence for development, not the future database schema.

## Coding Conventions

- Keep `main.py` thin. API request and response behavior belongs in `api/`.
- Keep job search workflow orchestration in `agent/workflows/job_search/`;
  shared LLM abstractions belong in `agent/llms/`.
- Prefer small typed dataclasses or explicit domain models for structured data.
- Keep external API constants near the client that owns them unless they become
  shared configuration.
- Use async APIs consistently when extending `JobDataLakeClient`; do not mix
  blocking HTTP calls into async flows.
- Keep upstream response models separate from display formatting and future
  database models. API models describe provider data; persistence models should
  describe application-owned records.
- Keep description enrichment sequential while the LLM client retains
  conversation state. Reset its system prompt before each posting. A single
  inaccessible page or invalid model result must be recorded as a scrape
  failure without discarding other jobs; retry invalid output once.
- Keep workflow nodes focused on orchestration. When database storage is added,
  move file/database writes and duplicate handling behind a storage or
  repository abstraction rather than adding more persistence behavior to the
  node.
- Preserve the current style: type hints, `from __future__ import annotations`,
  narrow helper functions, and clear error handling at boundaries.
- Avoid adding dependencies for trivial parsing or formatting. Add a dependency
  only when it removes meaningful complexity or is needed by the product.
- Do not read, print, or commit secrets from `.env`.

## Documentation Standards

Document all code well. In this repo that means:

- Every public module starts with a concise module docstring explaining its
  responsibility and any important boundary decisions.
- Every public class, dataclass, enum, function, and method has a docstring.
- Docstrings should explain purpose, inputs, outputs, side effects, and failure
  modes when those are not obvious from the signature.
- Follow PEP 257 docstring conventions. For non-trivial Python docstrings, use
  clear `Args:`, `Returns:`, and `Raises:` sections where they help readability;
  very short docstrings can stay as a single sentence.
- Keep docstrings factual and maintainable. Do not restate implementation line by
  line, and do not include stale examples.
- Add short inline comments before non-obvious decisions, protocol quirks,
  external API constraints, or security-sensitive behavior.
- Avoid noisy comments that paraphrase simple assignments or standard library
  calls.
- When adding configuration, document the environment variable name, where it is
  read, whether it is required, and what fallback is used.
- When adding prompts, document expected inputs, output shape, model/tool
  assumptions, and any safety or privacy constraints.
- When adding database models or migrations, document the business meaning of
  fields that are not self-evident and any compatibility assumptions.
- When adding tests, use descriptive test names that read as behavior
  documentation.

## Testing Guidance

- Tests live in `tests/`.
- Add focused tests only when they pull their weight for the current change.
- Mock external HTTP calls; do not require live Job Data Lake requests in normal
  tests.
- For concurrent behavior, test the association between input jobs and output
  records even when requests complete in a different order.
- Redirect generated job output to pytest temporary directories; tests must not
  write into the repository `data/` directory.
- When changing entrypoint behavior, test missing configuration and error
  output where practical.
- If a test framework or config file is introduced, update this guide with the
  exact command.

## Change Hygiene

- Keep generated artifacts, caches, virtual environments, and local data out of
  source changes.
- Do not modify `.venv` or `__pycache__` contents.
- Prefer narrowly scoped changes that match the existing directory ownership.
- Before larger changes, inspect nearby files and keep naming and layout
  consistent with what already exists.
- If creating project metadata, include dependency declarations, test commands,
  and package import behavior in the same change so future agents have a stable
  workflow.
