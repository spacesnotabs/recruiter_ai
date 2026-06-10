"""Unit tests for entrypoint configuration and dependency construction."""

from __future__ import annotations

import asyncio

import pytest

import main
from agent.llms.factory import ModelProvider
from config.environment import JOB_DATA_LAKE_API_KEY_ENV_VAR, OPENROUTER_API_KEY_ENV_VAR


def test_run_does_not_read_openrouter_key_for_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ollama runs without reading or passing an OpenRouter API key."""
    env_reads: list[str] = []
    factory_call: dict[str, object] = {}
    model_client = object()

    monkeypatch.setattr(
        main,
        "get_config_data",
        lambda config_path: {
            "llm": {"default": {"model_provider": "ollama", "model_name": "gemma4:e2b"}}
        },
    )

    def read_env_value(env_path: object, variable_name: str) -> str | None:
        env_reads.append(variable_name)
        if variable_name == JOB_DATA_LAKE_API_KEY_ENV_VAR:
            return "jobs-key"
        return None

    def create_model(**kwargs: object) -> object:
        factory_call.update(kwargs)
        return model_client

    async def run_workflow(created_model: object, job_client: object) -> int:
        assert created_model is model_client
        assert job_client.api_key == "jobs-key"
        return 7

    monkeypatch.setattr(main, "read_env_file_value", read_env_value)
    monkeypatch.setattr(main.ModelFactory, "create", create_model)
    monkeypatch.setattr(main, "run_job_search_workflow", run_workflow)

    assert asyncio.run(main.run()) == 7
    assert OPENROUTER_API_KEY_ENV_VAR not in env_reads
    assert factory_call == {
        "provider": ModelProvider.OLLAMA,
        "model_name": "gemma4:e2b",
    }


def test_run_requires_openrouter_key_for_openrouter(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenRouter runs stop before client construction when its key is absent."""
    monkeypatch.setattr(
        main,
        "get_config_data",
        lambda config_path: {
            "llm": {"default": {"model_provider": "openrouter", "model_name": "test-model"}}
        },
    )
    monkeypatch.setattr(
        main,
        "read_env_file_value",
        lambda env_path, variable_name: (
            "jobs-key" if variable_name == JOB_DATA_LAKE_API_KEY_ENV_VAR else None
        ),
    )

    def fail_create(**kwargs: object) -> object:
        raise AssertionError("ModelFactory.create should not be called without an OpenRouter key.")

    monkeypatch.setattr(main.ModelFactory, "create", fail_create)

    assert asyncio.run(main.run()) == 0
