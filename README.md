# Recruiter AI

Recruiter AI is a project that uses LangGraph workflows to collect job search criteria, query Job Data Lake, and enrich saved job records with LLM-extracted descriptions.  See Future Goals below to learn more about the plans for this application!

## Current Workflow
Currently, the workflow that is enabled is searching for jobs using natural language.

1. The user enters a prompt such as "Find me X-Wing mechanic jobs on Endor or remote"
2. An LLM takes this prompt, and crafts a JSON structure which matches the expectations of the supported API
3. A request to a `jobs` endpoint using the JobDataLake API is sent.
4. When a response is retrieved from the API, the data is saved to a JSON file

You can get an API key from JobDataLake at www.jobdatalake.com.

Future versions of Recruiter AI may support other job search APIs or methods of retrieving available job data.

## Setup

#### JobDataLake API
Create a `.env` file in the repository root with:

```text
JOB_DATA_LAKE_API_KEY=...
```

This is required for the current workflow.

#### OpenRouter

`OPENROUTER_API_KEY` is required only when `model_provider` is `openrouter`.
For local models, install and start Ollama, pull a model, and configure its tag
in `config/config.toml`:

```toml
[llm.default]
model_provider = "ollama"
model_name = "gemma4:e2b"
```

Ollama owns the files under the local model directory. The application connects
to the local Ollama service and identifies models by tag rather than by file
path.

#### Running

Install dependencies and run the workflow:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe .\main.py
```

The workflow creates `data/` when results are saved. That directory contains
generated local data and is ignored by Git.

## Description Enrichment (Coming soon)

The results from JobDataLake API contain some job role information, including a link to the job description, but not the job description itself.  I am working on creating a new workflow which will retrieve the HTML from a job description URL, and parse the actual descriptionf from it.  This data will be appended to the existing job data.


## Saved Job Viewer (Very prototype)

Run the lightweight read-only viewer to browse records in `data/`:

```powershell
.\.venv\Scripts\python.exe .\job_viewer.py
```

The viewer opens `http://127.0.0.1:8000/` in the default browser. It reads the
JSON files directly and reloads them on each page request. Use `--no-browser`
to prevent automatic browser launch, or `--data-dir` to inspect another
directory.

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
    "status": "pending",
    "error": null,
    "details": null,
    "input_truncated": false
  }
}
```

## Future Goals
I have many ideas to improve this application. Here are some of the current goals:

* Complete the workflow for retrieving job description text from links.  Sometimes, simply requesting the HTML from a link doesn't return usable data so this work may involve implementing other methods of HTML page reading.
* Model evaluation is high on the priority list.  The job search workflow uses an LLM for creating the API json structure.  Evaluating various smaller models to determine which most consistently create this structure will be helpful.  Another LLM will be used to parse job description data and information from HTML pages.  Evaluating various models for this work will also be important.
* I will switch from storing job data as JSON files to records in a database such as SQLite or Postgres
* Docker containerization
* Resume optimization will allow a user to upload his or her resume and have it modified for particular job descriptions.
* More... 

## AI Disclosure
I love LLMs.  I very much enjoy coding with LLMs.  However, I learn best when coding for myself.  In this project, I use a combination of methods.  For more boiler plate code, or code that I'm fairly confident I understand how to write myself, I use AI tools to speed up development.  For code that I want to learn more thoroughly, such as LangChain and LangGraph, or model evaluation, I write most of the code by hand (like the good ol' days) so I retain the knowledge better.  