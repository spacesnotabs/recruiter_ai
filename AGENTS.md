# Agent Guide

This repository is intentionally small right now. Keep it that way until the
project needs more structure.

## Repository Shape

- `main.py`: thin entrypoint that runs the current recruiter AI workflow.
- `agent/`: LLM clients, prompts, and workflow packages. The current job search
  workflow lives in `agent/workflows/job_search/`.
- `api/`: Job Data Lake API code and response formatting helpers.
- `models/`: small shared data models, such as job search parameters.
- `tools/`: small local utilities such as dotenv reading and job description
  scraping.
- `tests/`: unit tests for API, model, tool, and workflow behavior.
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

Set `OPENROUTER_API_KEY` in `.env` for the current workflow. Set the Job Data
Lake API key with `JOB_API_KEY` or `JOB_DATA_LAKE_API_KEY` when working on the
API client.

## Coding Conventions

- Keep `main.py` thin. API request and response behavior belongs in `api/`.
- Keep job search workflow orchestration in `agent/workflows/job_search/`;
  shared LLM abstractions belong in `agent/llms/`.
- Prefer small typed dataclasses or explicit domain models for structured data.
- Keep external API constants near the client that owns them unless they become
  shared configuration.
- Use async APIs consistently when extending `JobDataLakeClient`; do not mix
  blocking HTTP calls into async flows.
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
