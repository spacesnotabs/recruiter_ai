"""Unit tests for provider-specific model factory construction."""

from __future__ import annotations

import os

import pytest

from agent.llms.factory import ModelFactory, ModelProvider
from agent.llms.langchain import LangChainChatClient
from config.environment import OPENROUTER_API_KEY_ENV_VAR


def test_ollama_factory_configures_langchain_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """OLLAMA construction targets the named model in the local Ollama service."""
    monkeypatch.setattr(LangChainChatClient, "configure", lambda self: None)
    model = ModelFactory.create(provider=ModelProvider.OLLAMA, model_name="gemma4:e2b")

    assert isinstance(model, LangChainChatClient)
    assert model.model_name == "gemma4:e2b"


def test_ollama_factory_requires_model_name() -> None:
    """OLLAMA construction fails clearly when its model name is missing."""
    with pytest.raises(ValueError, match="model_name"):
        ModelFactory.create(provider=ModelProvider.OLLAMA)


def test_openrouter_factory_sets_api_key_without_live_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPENROUTER construction exports its API key before model configuration."""
    monkeypatch.delenv(OPENROUTER_API_KEY_ENV_VAR, raising=False)
    monkeypatch.setattr(LangChainChatClient, "configure", lambda self: None)

    model = ModelFactory.create(
        provider=ModelProvider.OPENROUTER,
        api_key="test-key",
        model_name="test-model",
    )

    assert isinstance(model, LangChainChatClient)
    assert model.model is None
    assert model.model_name == "test-model"
    assert os.environ[OPENROUTER_API_KEY_ENV_VAR] == "test-key"


def test_openrouter_factory_requires_api_key() -> None:
    """OPENROUTER construction fails clearly when its API key is missing."""
    with pytest.raises(ValueError, match="api_key"):
        ModelFactory.create(provider=ModelProvider.OPENROUTER)


def test_openrouter_factory_requires_model_name() -> None:
    """OPENROUTER construction fails clearly when its model name is missing."""
    with pytest.raises(ValueError, match="model_name"):
        ModelFactory.create(provider=ModelProvider.OPENROUTER, api_key="test-key")
