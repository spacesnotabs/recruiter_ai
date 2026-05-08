# Jobs API

This package contains API clients for external job data providers.

The Job Data Lake jobs API client is implemented in `job_api_client.py`. Use the
[JobDataLake API documentation](https://www.jobdatalake.com/dashboard/docs) as
the primary reference when updating request parameters, response handling, or
authentication behavior.

The client CLI can render the documented jobs response as a table, CSV, or raw
JSON. Table output is the default for local inspection:

```powershell
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m recruiter_ai.ingestion.apis.job_api_client --keywords "backend engineer"
```

Use CSV output when you want a simple artifact for spreadsheet review or later
database import experiments:

```powershell
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe -m recruiter_ai.ingestion.apis.job_api_client --keywords "backend engineer" --format csv --output data\processed\jobs.csv
```
