"""Helpers for reading simple local environment files."""

from __future__ import annotations

from pathlib import Path


def read_env_file_value(env_path: Path, variable_name: str) -> str | None:
    """Read one variable from a simple KEY=VALUE environment file.

    Missing files, absent variables, and blank values return ``None``. The
    parser intentionally supports only straightforward dotenv-style entries and
    ignores comments or malformed lines.
    """
    if not env_path.exists():
        return None

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#") or "=" not in stripped_line:
            continue

        key, value = stripped_line.split("=", 1)
        if key.strip() == variable_name:
            return value.strip().strip("'\"") or None

    return None
