"""Entrypoint for running the recruiter AI workflow."""

from __future__ import annotations

import asyncio
import logging
import tomllib
from typing import Any

from agent.llms.factory import ModelFactory, ModelProvider
from agent.workflows.job_search.workflow import run_job_search_workflow
from api.job_data_lake import JobDataLakeClient
from config.environment import (
    JOB_DATA_LAKE_API_KEY_ENV_VAR,
    OPENROUTER_API_KEY_ENV_VAR,
    ROOT_ENV_PATH,
)
from tools.env_file import read_env_file_value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
)


def get_config_data(config_path: str) -> dict[str, Any]:
    """Load configuration data from a TOML file."""
    with open(config_path, "rb") as config_file:
        return tomllib.load(config_file)


async def run() -> int:
    """Run the LangGraph job search workflow."""
    config_data = get_config_data("config/config.toml")
    model_provider = ModelProvider(config_data["llm"]["default"]["model_provider"])
    model_name = config_data["llm"]["default"]["model_name"]

    job_data_lake_api_key = read_env_file_value(ROOT_ENV_PATH, JOB_DATA_LAKE_API_KEY_ENV_VAR)
    if job_data_lake_api_key is None:
        return 0

    model_options: dict[str, object] = {"model_name": model_name}
    if model_provider is ModelProvider.OPENROUTER:
        openrouter_api_key = read_env_file_value(ROOT_ENV_PATH, OPENROUTER_API_KEY_ENV_VAR)
        if openrouter_api_key is None:
            return 0
        model_options["api_key"] = openrouter_api_key

    model_client = ModelFactory.create(provider=model_provider, **model_options)
    job_client = JobDataLakeClient(api_key=job_data_lake_api_key)
    return await run_job_search_workflow(model_client, job_client)


def main() -> int:
    """Run the async workflow entrypoint."""
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
