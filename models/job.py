"""Validated models for responses from the Job Data Lake jobs endpoint.

These models represent the documented upstream API contract rather than a
future database schema. Unknown fields are retained so additions made by the
provider do not prevent otherwise valid responses from being processed.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class JobDataLakeModel(BaseModel):
    """Base configuration shared by Job Data Lake response models."""

    model_config = ConfigDict(extra="allow")


class JobDataLakeJob(JobDataLakeModel):
    """One job returned by the Job Data Lake jobs endpoint."""

    title: str
    company_name: str | None = None
    domain_name: str | None = None
    posted_at: datetime | None = None
    locations: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    remote_type: str | None = None
    job_function: str | None = None
    seniority: list[str] = Field(default_factory=list)
    salary_min_usd: Decimal | None = None
    salary_max_usd: Decimal | None = None
    required_skills: list[str] = Field(default_factory=list)
    employment_type: str | None = None
    url: str
    job_handle: str | None = None


class JobDataLakeStats(JobDataLakeModel):
    """Aggregate job counts included with a jobs endpoint response."""

    total_jobs: int
    new_last_24h: int


class JobDataLakeResponse(JobDataLakeModel):
    """A validated page returned by the Job Data Lake jobs endpoint."""

    found: int
    page: int
    per_page: int
    jobs: list[JobDataLakeJob] = Field(default_factory=list)
    stats: JobDataLakeStats | None = None
