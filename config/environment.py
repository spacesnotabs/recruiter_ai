"""Environment variable names and local environment file locations."""

from __future__ import annotations

from pathlib import Path


ROOT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
OPENROUTER_API_KEY_ENV_VAR = "OPENROUTER_API_KEY"
JOB_DATA_LAKE_API_KEY_ENV_VAR = "JOB_DATA_LAKE_API_KEY"
