"""Tests for Job Data Lake response presentation helpers."""

from __future__ import annotations

import csv
import io
import unittest

from recruiter_ai.ingestion.apis.job_response_formatter import (
    build_display_rows,
    format_jobs_csv,
    format_jobs_table,
)


SAMPLE_RESPONSE = {
    "found": 3800,
    "page": 1,
    "per_page": 10,
    "jobs": [
        {
            "title": "Senior Backend Engineer",
            "company_name": "Stripe",
            "domain_name": "stripe.com",
            "posted_at": 1775520869,
            "locations": ["San Francisco, CA", "Remote"],
            "countries": ["US"],
            "remote_type": "fully_remote",
            "job_function": "eng",
            "seniority": ["Senior"],
            "salary_min_usd": 180,
            "salary_max_usd": 250,
            "required_skills": ["Python", "AWS", "Kubernetes"],
            "employment_type": "full_time",
            "url": "https://stripe.com/jobs/backend",
            "job_handle": "stripe-senior-backend-engineer-abc123",
        }
    ],
    "stats": {
        "total_jobs": 1080000,
        "new_last_24h": 1100,
    },
}


class JobResponseFormatterTests(unittest.TestCase):
    """Behavior tests for formatting documented jobs API responses."""

    def test_build_display_rows_normalizes_documented_job_fields(self) -> None:
        """Structured API values are converted into readable display fields."""
        row = build_display_rows(SAMPLE_RESPONSE)[0]

        self.assertEqual(row.title, "Senior Backend Engineer")
        self.assertEqual(row.company, "Stripe")
        self.assertEqual(row.locations, "San Francisco, CA, Remote")
        self.assertEqual(row.skills, "Python, AWS, Kubernetes")
        self.assertEqual(row.salary, "$180-$250")
        self.assertEqual(row.posted, "2026-04-07")

    def test_format_jobs_table_includes_summary_and_job_values(self) -> None:
        """Table output includes response-level metadata and scan-friendly rows."""
        output = format_jobs_table(SAMPLE_RESPONSE)

        self.assertIn("found: 3800", output)
        self.assertIn("total jobs: 1080000", output)
        self.assertIn("Senior Backend Engineer", output)
        self.assertIn("Stripe", output)
        self.assertIn("fully_remote", output)

    def test_format_jobs_table_handles_empty_results(self) -> None:
        """Empty responses still show useful paging metadata."""
        output = format_jobs_table({"found": 0, "page": 1, "per_page": 10, "jobs": []})

        self.assertIn("found: 0", output)
        self.assertIn("No jobs found.", output)

    def test_format_jobs_csv_writes_header_and_normalized_row(self) -> None:
        """CSV output can be parsed by standard tools without custom handling."""
        output = format_jobs_csv(SAMPLE_RESPONSE)
        rows = list(csv.DictReader(io.StringIO(output)))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Senior Backend Engineer")
        self.assertEqual(rows[0]["locations"], "San Francisco, CA, Remote")
        self.assertEqual(rows[0]["salary"], "$180-$250")
        self.assertEqual(rows[0]["job_handle"], "stripe-senior-backend-engineer-abc123")


if __name__ == "__main__":
    unittest.main()
