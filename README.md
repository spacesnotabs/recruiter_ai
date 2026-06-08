# Recruiter AI

Recruiter AI is a Python 3.12 proof of concept that uses an LLM-driven
LangGraph workflow to collect job search criteria, query Job Data Lake, scrape
job descriptions, and store local job records for later processing.

## Current Workflow

1. The LLM collects and validates job search parameters.
2. The async Job Data Lake client calls `/v1/jobs`.
3. Pydantic models validate the response and convert fields such as Unix
   timestamps and salaries into typed Python values.
4. Job posting pages are scraped concurrently, with at most five requests in
   flight.
5. Each combined API and scrape record is written to `data/`.

Scrape failures do not discard the Job Data Lake record. The saved JSON records
include a scrape status and error so failed pages can be retried later.

## Setup

Create a `.env` file in the repository root with:

```text
OPENROUTER_API_KEY=...
JOB_DATA_LAKE_API_KEY=...
```

Install dependencies and run the workflow:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe .\main.py
```

The workflow creates `data/` when results are saved. That directory contains
generated local data and is ignored by Git.

## Stored Job Records

Files use `job_<job_handle>.json` when Job Data Lake provides a handle. If a
handle is missing, the filename uses a deterministic hash of the job URL.

Each record has this high-level structure:

```json
{
  "source": "job_data_lake",
  "source_job_id": "provider-handle",
  "job": {
    "title": "Backend Engineer",
    "url": "https://example.com/jobs/1"
  },
  "scrape": {
    "status": "succeeded",
    "error": null,
    "details": {
      "description": "..."
    }
  }
}
```

These files are temporary development persistence. The API response models in
`models/job.py` are intentionally separate from a future application-owned
database schema.

## Tests

Tests mock external HTTP behavior and redirect generated records to temporary
directories:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The suite covers API response validation, query conversion, scraping,
concurrent result association, scrape failure persistence, and filename
fallback behavior.

## Documentation

More documentation can be found in the [docs folder](./docs/)