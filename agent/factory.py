"""Factory for creating provider-specific language model clients."""

from __future__ import annotations

from enum import Enum
import logging
import os

from .llms.base import LLMClient
from .llms.langchain import LangChainChatClient
from .llms.local import LocalLLMClient


logger = logging.getLogger(__name__)
OPEN_ROUTER_API_KEY_ENV_VAR = "OPENROUTER_API_KEY"
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"


class ModelProvider(Enum):
    """Supported language model providers."""

    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class ModelFactory:
    """Namespace for provider-specific language model construction."""

    @staticmethod
    def create(provider: ModelProvider, **kwargs: object) -> LLMClient:
        """Create and configure a language model client for the selected provider.

        ``provider`` selects the model backend. OPENROUTER requires an
        ``api_key`` argument and accepts an optional ``model_name``. OLLAMA
        requires a ``filename`` argument and accepts an optional ``model_name``.
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

        model_name = kwargs.get("model_name", DEFAULT_OPENROUTER_MODEL)
        if not isinstance(model_name, str) or not model_name:
            raise ValueError("OPENROUTER model provider requires model_name to be a non-empty string.")

        os.environ[OPEN_ROUTER_API_KEY_ENV_VAR] = api_key
        model_client = LangChainChatClient(model_name=model_name, model_provider=ModelProvider.OPENROUTER.value)
        model_client.set_api_key(api_key)
        return model_client

    @staticmethod
    def _create_ollama_client(**kwargs: object) -> LocalLLMClient:
        """Create a local client configured with an Ollama model file path."""
        filename = kwargs.get("filename")
        if not isinstance(filename, str) or not filename:
            raise ValueError("OLLAMA model provider requires filename.")

        model_name = kwargs.get("model_name", ModelProvider.OLLAMA.value)
        if not isinstance(model_name, str) or not model_name:
            raise ValueError("OLLAMA model provider requires model_name to be a non-empty string.")

        model_client = LocalLLMClient(model_name=model_name)
        model_client.model_filepath = filename
        return model_client
