"""Factory for creating provider-specific language model clients."""

from __future__ import annotations

from enum import Enum
import logging
import os

from agent.llms.base import LLMClient
from agent.llms.langchain import LangChainChatClient
from config.environment import OPENROUTER_API_KEY_ENV_VAR

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported language model providers."""

    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class ModelFactory:
    """Namespace for provider-specific language model construction."""

    @staticmethod
    def create(provider: ModelProvider, **kwargs: object) -> LLMClient:
        """Create and configure a language model client for the selected provider.

        ``provider`` selects the model backend. OPENROUTER requires
        ``api_key`` and ``model_name`` arguments. OLLAMA requires a
        ``model_name`` matching a model installed in the local Ollama service.
        Missing required provider arguments raise ``ValueError``.
        """
        model_client = ModelFactory._create_model_client(provider, **kwargs)
        model_client.set_system_prompt("You are a helpful assistant.")
        model_client.configure()
        return model_client

    @staticmethod
    def _create_model_client(provider: ModelProvider, **kwargs: object) -> LLMClient:
        """Create a provider-specific model client from keyword arguments."""
        if provider is ModelProvider.OPENROUTER:
            return ModelFactory._create_openrouter_client(**kwargs)

        if provider is ModelProvider.OLLAMA:
            return ModelFactory._create_ollama_client(**kwargs)

        raise ValueError(f"Unsupported model provider: {provider!r}")

    @staticmethod
    def _create_openrouter_client(**kwargs: object) -> LangChainChatClient:
        """Create a LangChain OpenRouter client using the provided API key."""
        api_key = kwargs.get("api_key")
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("OPENROUTER model provider requires api_key.")

        model_name = kwargs.get("model_name")
        if not isinstance(model_name, str) or not model_name:
            raise ValueError("OPENROUTER model provider requires model_name to be a non-empty string.")

        os.environ[OPENROUTER_API_KEY_ENV_VAR] = api_key
        model_client = LangChainChatClient(model_name=model_name, model_provider=ModelProvider.OPENROUTER.value)
        model_client.set_api_key(api_key)
        return model_client

    @staticmethod
    def _create_ollama_client(**kwargs: object) -> LangChainChatClient:
        """Create a LangChain client for a model served by local Ollama."""
        model_name = kwargs.get("model_name")
        if not isinstance(model_name, str) or not model_name:
            raise ValueError("OLLAMA model provider requires model_name to be a non-empty string.")

        return LangChainChatClient(
            model_name=model_name,
            model_provider=ModelProvider.OLLAMA.value,
        )
