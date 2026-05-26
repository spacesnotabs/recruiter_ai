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


@dataclass(frozen=True)
class JobSearchParams:
    """Search filters supported by the upstream jobs API."""

    keywords: str | None = None
    job_function: JobFunction | None = None
    location: str | None = None
    salary_min: int | None = None
    remote_type: RemoteType | None = None

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
            }.items()
            if value is not None
        }
