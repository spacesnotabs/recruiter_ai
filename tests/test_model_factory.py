"""Unit tests for provider-specific model factory construction."""

from __future__ import annotations

import os

import pytest

from agent.llms.factory import ModelFactory, ModelProvider, OPEN_ROUTER_API_KEY_ENV_VAR
from agent.llms.langchain import LangChainChatClient
from agent.llms.local import LocalLLMClient


def test_ollama_factory_configures_local_model_filename() -> None:
    """OLLAMA construction stores the provider-specific model filename."""
    model = ModelFactory.create(provider=ModelProvider.OLLAMA, filename="local-model.gguf")

    assert isinstance(model, LocalLLMClient)
    assert model.model_name == ModelProvider.OLLAMA.value
    assert model.model_filepath == "local-model.gguf"


def test_ollama_factory_requires_filename() -> None:
    """OLLAMA construction fails clearly when its filename is missing."""
    with pytest.raises(ValueError, match="filename"):
        ModelFactory.create(provider=ModelProvider.OLLAMA)


def test_openrouter_factory_sets_api_key_without_live_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPENROUTER construction exports its API key before model configuration."""
    monkeypatch.delenv(OPEN_ROUTER_API_KEY_ENV_VAR, raising=False)
    monkeypatch.setattr(LangChainChatClient, "configure", lambda self: None)

    model = ModelFactory.create(provider=ModelProvider.OPENROUTER, api_key="test-key")

    assert isinstance(model, LangChainChatClient)
    assert model.model is None
    assert os.environ[OPEN_ROUTER_API_KEY_ENV_VAR] == "test-key"


def test_openrouter_factory_requires_api_key() -> None:
    """OPENROUTER construction fails clearly when its API key is missing."""
    with pytest.raises(ValueError, match="api_key"):
        ModelFactory.create(provider=ModelProvider.OPENROUTER)
