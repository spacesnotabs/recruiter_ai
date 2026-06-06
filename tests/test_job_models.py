"""Unit tests for validated Job Data Lake response models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from models.job import JobDataLakeResponse


def test_job_response_parses_documented_fields_and_retains_unknown_fields() -> None:
    """Documented job data is typed while provider additions remain available."""
    response = JobDataLakeResponse.model_validate(
        {
            "found": 1,
            "page": 1,
            "per_page": 10,
            "jobs": [
                {
                    "title": "Senior Backend Engineer",
                    "company_name": "Stripe",
                    "domain_name": "stripe.com",
                    "posted_at": 1_700_000_000,
                    "locations": ["San Francisco, CA", "Remote"],
                    "countries": ["US"],
                    "remote_type": "fully_remote",
                    "job_function": "eng",
                    "seniority": ["Senior"],
                    "salary_min_usd": 180,
                    "salary_max_usd": 250.5,
                    "required_skills": ["Python", "AWS", "Kubernetes"],
                    "employment_type": "full_time",
                    "url": "https://stripe.com/jobs/1",
                    "job_handle": "stripe-senior-backend-engineer-abc123",
                    "provider_field": "preserved",
                }
            ],
            "stats": {"total_jobs": 1_080_000, "new_last_24h": 1_100},
            "request_id": "request-123",
        }
    )

    job = response.jobs[0]
    assert job.posted_at == datetime.fromtimestamp(1_700_000_000, tz=UTC)
    assert job.salary_min_usd == Decimal("180")
    assert job.salary_max_usd == Decimal("250.5")
    assert job.provider_field == "preserved"
    assert response.request_id == "request-123"


def test_job_response_uses_independent_empty_lists_for_optional_collections() -> None:
    """Missing collection fields receive independent empty list defaults."""
    response = JobDataLakeResponse.model_validate(
        {
            "found": 2,
            "page": 1,
            "per_page": 10,
            "jobs": [
                {"title": "Backend Engineer", "url": "https://example.test/jobs/1"},
                {"title": "Platform Engineer", "url": "https://example.test/jobs/2"},
            ],
        }
    )

    response.jobs[0].locations.append("Remote")

    assert response.jobs[1].locations == []
