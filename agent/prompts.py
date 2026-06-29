"""Prompt text used by model-backed recruiter workflows."""

from __future__ import annotations

import json

from agent.workflows.job_search.validation import JobSearchQuery, JobDescription


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

The API searches job titles, company names, and skills using "keywords". Put
only those search terms in "keywords". Do not include salary, location,
seniority, remote type, job function, posting date, or other filter values in
"keywords"; put each value in its dedicated field instead.

The "response" field should summarize the query. The "salary_min" field is an
integer in thousands. Convert relative posting-time requests such as "in the
last week" to a Unix timestamp in milliseconds for "posted_after". Omit
optional fields when the user did not provide enough information to infer them
reliably.
""".strip()


def _build_job_description_extraction_prompt() -> str:
    """Build extraction instructions for cleaned job-posting text."""
    schema = json.dumps(JobDescription.model_json_schema(), indent=2)
    return f"""
You will be given cleaned plain text from a public job-posting page. Extract the
job description and the requested metadata from that text. The description must
preserve the source wording; do not summarize, rewrite, or invent content.

Return only valid JSON, with no Markdown code fence or additional text, that
conforms to this JSON Schema:

{schema}

The description is required and must be non-empty. If title, salary, or location
is not explicitly present in the supplied text, return null for that field. Do
not infer missing metadata. The Job Data Lake record is authoritative for its
own metadata fields.
""".strip()


JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT = _build_job_search_parameter_extraction_prompt()
JOB_SEARCH_DESCRIPTION_EXTRACTION_PROMPT = _build_job_description_extraction_prompt()
