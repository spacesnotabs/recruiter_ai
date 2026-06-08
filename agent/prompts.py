"""Prompt text used by model-backed recruiter workflows."""

from __future__ import annotations

import json

from agent.workflows.job_search.validation import JobSearchQuery


def _build_job_search_parameter_extraction_prompt() -> str:
    """Build extraction instructions from the current job search schema."""
    schema = json.dumps(JobSearchQuery.model_json_schema(), indent=2)
    return f"""
You will parse a user's input into job search parameters. Your responses must
always be valid JSON with no Markdown code fence or additional text.

If the user did not provide any keywords, ask for more information using only:
{{
  "response": "your response asking for more information",
  "complete": false
}}

If the user provided keywords, set "complete" to true and return JSON that
conforms to the following JSON Schema:

{schema}

The "response" field should summarize the query. The "salary_min" field is an
integer in thousands. Convert relative posting-time requests such as "in the
last week" to a Unix timestamp in milliseconds for "posted_after". Omit
optional fields when the user did not provide enough information to infer them
reliably.
""".strip()


JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT = _build_job_search_parameter_extraction_prompt()
