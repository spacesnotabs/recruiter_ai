import json
from typing import Any
from agent.llms.factory import ModelFactory, ModelProvider
from config.environment import OPENROUTER_API_KEY_ENV_VAR, ROOT_ENV_PATH
from tools.env_file import read_env_file_value
from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
RUBRIC_PATH = CURRENT_DIR / "rubric.json"

def evaluate_job_search_query_construction():
    with open(RUBRIC_PATH, "r") as f:
        rubric = json.load(f)

    for eval in rubric.get("evals"):
        desc: str = eval.get("description")
        prompt: str = eval.get("input_prompt")
        expected_output: dict[str, Any] = eval.get("expected_output")

        # prompt the LLM
        model_provider = "openrouter"
        model_name = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

        openrouter_api_key = read_env_file_value(ROOT_ENV_PATH, OPENROUTER_API_KEY_ENV_VAR)
        if openrouter_api_key is None:
            return 0

        model_client = ModelFactory.create(provider=ModelProvider(model_provider), model_name=model_name, api_key=openrouter_api_key)
        model_client.set_system_prompt(prompt=JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT)
        response:str = model_client.prompt(prompt=prompt)
        response_json: dict[str, Any] = json.loads(response)

        complete_value: bool | None = response_json.get("complete", None)

        assert complete_value != None
        assert complete_value == expected_output.get("complete", None)

evaluate_job_search_query_construction()
