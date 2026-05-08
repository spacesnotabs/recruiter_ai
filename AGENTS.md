# Agent Guide

This repository is a Python project for recruiter-oriented AI workflows. It is
currently a scaffold with one implemented module:
`src/recruiter_ai/ingestion/apis/job_api_client.py`, an async `httpx` client and
CLI for the Job Data Lake jobs API.

## Repository Shape

- `src/recruiter_ai/agents`: agent implementations.
- `src/recruiter_ai/chains`: chain or pipeline composition.
- `src/recruiter_ai/cli`: command-line entrypoints.
- `src/recruiter_ai/config`: local configuration. Treat `.env` files as secrets.
- `src/recruiter_ai/database`: migrations, models, and repositories.
- `src/recruiter_ai/domain`: core domain models and business rules.
- `src/recruiter_ai/graphs`: graph workflow definitions.
- `src/recruiter_ai/ingestion`: external data ingestion, API clients, and scrapers.
- `src/recruiter_ai/mcp_server`: MCP server integration.
- `src/recruiter_ai/prompts`: prompt templates and prompt assets.
- `src/recruiter_ai/services`: application services and orchestration logic.
- `src/recruiter_ai/tools`: tool adapters exposed to agents or workflows.
- `src/recruiter_ai/utils`: shared helpers with no domain ownership.
- `tests/unit`, `tests/integration`, `tests/fixtures`: test structure.
- `data/raw` and `data/processed`: local data areas. Do not commit bulky,
  generated, private, or credential-bearing data.
- `frontend`, `infra`, `scripts`, and `docs` are present but currently empty.

## Current Runtime Assumptions

- Use Python 3.12; the local virtual environment is `.venv`.
- Existing code depends on `httpx`.
- No `pyproject.toml`, lockfile, or test configuration is present yet.
- The workspace is not currently initialized as a Git repository.
- Prefer PowerShell-friendly commands when documenting local usage.

Useful commands from the repository root:

```powershell
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m recruiter_ai.ingestion.apis.job_api_client --help
.\.venv\Scripts\python.exe src\recruiter_ai\ingestion\apis\job_api_client.py --help
```

If package metadata is added later, update these commands to use the supported
entrypoint and test runner.

## Coding Conventions

- Keep modules focused on their layer. For example, API request and response
  behavior belongs in `ingestion/apis`; CLI parsing should either stay thin or
  move to `cli` when it grows.
- Prefer small typed dataclasses or explicit domain models for structured data.
- Keep external API constants near the client that owns them unless they become
  shared configuration.
- Use async APIs consistently when extending `JobApiClient`; do not mix blocking
  HTTP calls into async flows.
- Preserve the current style: type hints, `from __future__ import annotations`,
  narrow helper functions, and clear error handling at boundaries.
- Avoid adding dependencies for trivial parsing or formatting. Add a dependency
  only when it removes meaningful complexity or is needed by the product.
- Do not read, print, or commit secrets from `src/recruiter_ai/config/.env`.

## Documentation Standards

Document all code well. In this repo that means:

- Every public module starts with a concise module docstring explaining its
  responsibility and any important boundary decisions.
- Every public class, dataclass, enum, function, and method has a docstring.
- Docstrings should explain purpose, inputs, outputs, side effects, and failure
  modes when those are not obvious from the signature.
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

- Add focused unit tests under `tests/unit` for pure helpers, query building,
  parsing, and error handling.
- Add integration tests under `tests/integration` only for behavior that crosses
  process, database, network, or service boundaries.
- Mock external HTTP calls; do not require live Job Data Lake requests in normal
  tests.
- When changing CLI behavior, test argument parsing, missing configuration, and
  error output.
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
