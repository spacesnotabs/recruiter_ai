"""Search parameter model for Job Data Lake job queries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RemoteType(str, Enum):
    """Remote work types supported by the upstream jobs API."""

    FULLY_REMOTE = "fully_remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"


class JobFunction(str, Enum):
    """Job functions supported by the upstream jobs API."""

    ENGINEERING = "eng"
    DATA = "data"
    DESIGN = "design"
    SALES = "sales"
    OPERATIONS = "ops"
    MARKETING = "marketing"
    SECURITY = "security"
    PRODUCT = "product"
    FINANCE = "finance"
    HUMAN_RESOURCES = "hr"
    LEGAL = "legal"
    OTHER = "other"


class Seniority(str, Enum):
    """Seniority levels supported by the upstream jobs API."""

    ENTRY = "Entry"
    MID_LEVEL = "Mid Level"
    SENIOR = "Senior"
    STAFF = "Staff"
    PRINCIPAL = "Principal"
    MANAGER = "Manager"
    DIRECTOR = "Director"
    LEAD = "Lead"
    C_LEVEL = "C Level"
    INTERNSHIP = "Internship"


@dataclass(frozen=True)
class JobSearchParams:
    """Search filters supported by the upstream jobs API."""

    keywords: str | None = None
    job_function: JobFunction | None = None
    location: str | None = None
    salary_min: int | None = None
    remote_type: RemoteType | None = None
    posted_after: int | None = None
    seniority: tuple[Seniority, ...] | None = None

    def to_query_params(self) -> dict[str, str | int]:
        """Convert populated search fields to Job Data Lake query parameters."""
        return {
            key: value
            for key, value in {
                "q": self.keywords,
                "job_function": self.job_function.value if self.job_function else None,
                "location": self.location,
                "salary_min": self.salary_min,
                "remote_type": self.remote_type.value if self.remote_type else None,
                "posted_after": self.posted_after,
                "seniority": ",".join(level.value for level in self.seniority) if self.seniority else None,
            }.items()
            if value is not None
        }
