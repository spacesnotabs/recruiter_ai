"""Entrypoint for running the recruiter AI workflow."""

from __future__ import annotations

import asyncio
import logging
import tomllib

from agent.llms.factory import OPEN_ROUTER_API_KEY_ENV_VAR, ModelFactory, ModelProvider
from agent.workflows.job_search.workflow import run_job_search_workflow
from api.job_data_lake import ROOT_ENV_PATH
from tools.env_file import read_env_file_value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
)

def get_config_data(config_path: str):
    """Load configuration data from a TOML file."""
    with open(config_path, "rb") as config_file:
        data = tomllib.load(config_file)
        print(data)
        return data

async def run() -> int:
    """Run the proof-of-concept LangGraph job search workflow."""
    openrouter_api_key = read_env_file_value(ROOT_ENV_PATH, OPEN_ROUTER_API_KEY_ENV_VAR)
    if openrouter_api_key is None:
        return 0

    config_data = get_config_data("config/config.toml")
    model_provider = config_data["llm"]["default"]["model_provider"]
    model_name = config_data["llm"]["default"]["model_name"]

    model_client = ModelFactory.create(provider=ModelProvider(model_provider), model_name=model_name, api_key=openrouter_api_key)
    return await run_job_search_workflow(model_client)


def main() -> int:
    """Run the async workflow entrypoint."""
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
