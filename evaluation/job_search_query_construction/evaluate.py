import json
from typing import Any
from agent.llms.base import LLMClient
from agent.llms.factory import ModelFactory, ModelProvider
from agent.prompts import JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT
from config.environment import OPENROUTER_API_KEY_ENV_VAR, ROOT_ENV_PATH
from tools.env_file import read_env_file_value
from tools.web_scraping import html_to_clean_text
from agent.prompts import (
    JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT,
    JOB_SEARCH_DESCRIPTION_EXTRACTION_PROMPT,
)
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
RUBRIC_PATH = CURRENT_DIR / "rubric.json"
# HTML_PATH = CURRENT_DIR / "eval_files" / "job_description.html"


def _get_model_client(
    model_provider: str, model_name: str, system_prompt: str
) -> LLMClient:
    openrouter_api_key = read_env_file_value(ROOT_ENV_PATH, OPENROUTER_API_KEY_ENV_VAR)
    if openrouter_api_key is None:
        raise ValueError("OpenRouter API key not found in environment variables.")

    model_client: LLMClient = ModelFactory.create(
        provider=ModelProvider(model_provider),
        model_name=model_name,
        api_key=openrouter_api_key,
    )
    model_client.set_system_prompt(prompt=system_prompt)
    return model_client


def evaluate_job_search_query_construction():
    print(f"Running test cases from {RUBRIC_PATH}.")
    with open(RUBRIC_PATH, "r") as f:
        rubric = json.load(f)

    for eval in rubric.get("evals"):
        desc: str = eval.get("description")
        prompt_to_evaluate: str = eval.get("evaluation_prompt")

        if prompt_to_evaluate == "JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT":
            system_prompt = JOB_SEARCH_PARAMETER_EXTRACTION_PROMPT

        llm_client: LLMClient = _get_model_client(
            model_provider="openrouter",
            model_name="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            system_prompt=system_prompt,
        )

        print("Running the following evaluations:")
        print(f"Description: ", desc)
        print(f"Prompt to test: ", prompt_to_evaluate)

        for test_case in eval.get("test_cases"):
            print(f"Running test case {test_case['id']}")

            input_prompt = test_case.get("input_prompt")
            print(f"Input Prompt: {input_prompt}")
            expected_output: dict[str, Any] = test_case.get("expected_output")
            print(f"Expected Output: {expected_output}")

            llm_client.reset_history()
            response: str = llm_client.prompt(prompt=input_prompt)
            print(f"Actual Output: {response}")
            response_json: dict[str, Any] = json.loads(response)
            print(f"Actual Output JSON: {response_json}")

            complete_value: bool | None = response_json.get("complete", None)
            keywords_value: list[str] | None = response_json.get("keywords_value", None)

            assert complete_value != None
            assert complete_value == expected_output.get("complete", None)
            assert keywords_value == expected_output.get("keywords", None)


def evaluate_job_description_scraping():
    prompt: str = ""
    with open(HTML_PATH, "r") as f:
        prompt = f.read()

    # clean up the raw HTML
    cleaned_prompt: str = html_to_clean_text(prompt)
    print("Cleaned Prompt:" + cleaned_prompt)

    print("System Prompt:" + JOB_SEARCH_DESCRIPTION_EXTRACTION_PROMPT)
    llm_client: LLMClient = _get_model_client(
        model_provider="openrouter",
        model_name="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        system_prompt=JOB_SEARCH_DESCRIPTION_EXTRACTION_PROMPT,
    )

    response: str = llm_client.prompt(prompt=cleaned_prompt)
    response_json: dict[str, Any] = json.loads(response)
    print(response_json)
