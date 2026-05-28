"""Unit tests for local environment file helpers."""

from __future__ import annotations

from pathlib import Path

from tools.env_file import read_env_file_value


def test_read_env_file_value_returns_matching_unquoted_value(tmp_path: Path) -> None:
    """Env file parsing ignores comments and strips surrounding quotes."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# local settings",
                "JOB_DATA_LAKE_API_KEY='secret-value'",
                "OTHER=value",
            ]
        ),
        encoding="utf-8",
    )

    assert read_env_file_value(env_path, "JOB_DATA_LAKE_API_KEY") == "secret-value"


def test_read_env_file_value_returns_none_for_missing_file_or_empty_value(tmp_path: Path) -> None:
    """Missing files, missing variables, and blank values do not produce secrets."""
    missing_path = tmp_path / "missing.env"
    env_path = tmp_path / ".env"
    env_path.write_text("JOB_DATA_LAKE_API_KEY=\nOTHER=value\n", encoding="utf-8")

    assert read_env_file_value(missing_path, "JOB_DATA_LAKE_API_KEY") is None
    assert read_env_file_value(env_path, "JOB_DATA_LAKE_API_KEY") is None
    assert read_env_file_value(env_path, "UNKNOWN") is None
