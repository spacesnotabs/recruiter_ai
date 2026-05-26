"""Tests for job posting extraction helpers."""

from __future__ import annotations

import unittest

from tools.job_description_scraper import extract_job_posting_from_html


class JobDescriptionScraperTests(unittest.TestCase):
    """Behavior tests for static HTML job posting extraction."""

    def test_extracts_job_posting_json_ld(self) -> None:
        """JSON-LD JobPosting data is preferred over generic page text."""
        html = """
        <html>
          <head>
            <title>Fallback title</title>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "JobPosting",
              "title": "Backend Engineer",
              "description": "<p>Build APIs.</p><p>Own production systems.</p>",
              "datePosted": "2026-05-20",
              "employmentType": ["FULL_TIME", "REMOTE"],
              "hiringOrganization": {"name": "Colevity"},
              "jobLocation": {
                "address": {
                  "addressLocality": "Seattle",
                  "addressRegion": "WA",
                  "addressCountry": "US"
                }
              },
              "baseSalary": {
                "currency": "USD",
                "value": {
                  "minValue": 120000,
                  "maxValue": 150000,
                  "unitText": "YEAR"
                }
              }
            }
            </script>
          </head>
        </html>
        """

        details = extract_job_posting_from_html(html, "https://example.test/job")

        self.assertEqual(details.title, "Backend Engineer")
        self.assertEqual(details.company_name, "Colevity")
        self.assertEqual(details.location, "Seattle, WA, US")
        self.assertEqual(details.description, "Build APIs.\n\nOwn production systems.")
        self.assertEqual(details.employment_type, "FULL_TIME, REMOTE")
        self.assertEqual(details.date_posted, "2026-05-20")
        self.assertEqual(details.salary, "USD 120000-150000 YEAR")

    def test_falls_back_to_likely_description_container(self) -> None:
        """Visible job description containers are used when JSON-LD is absent."""
        html = """
        <html>
          <head><title>Senior Recruiter - ExampleCo</title></head>
          <body>
            <h1>Senior Recruiter</h1>
            <div class="job-description">
              <p>Partner with hiring managers across engineering and product.</p>
              <p>Build structured interview loops and improve candidate experience.</p>
              <p>Use data to manage pipeline quality, conversion, and hiring velocity.</p>
            </div>
          </body>
        </html>
        """

        details = extract_job_posting_from_html(html, "https://example.test/job")

        self.assertEqual(details.title, "Senior Recruiter")
        self.assertIn("Partner with hiring managers", details.description or "")
        self.assertIn("hiring velocity", details.description or "")


if __name__ == "__main__":
    unittest.main()
