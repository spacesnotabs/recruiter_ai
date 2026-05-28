"""Agent controller for prompting the configured OpenRouter chat model."""

from __future__ import annotations

import os
import logging

from .llms.langchain import LangChainChatClient


logger = logging.getLogger(__name__)
OPEN_ROUTER_API_KEY_ENV_VAR = "OPENROUTER_API_KEY"


class AgentController:
    """Prompting facade for the OpenRouter-backed chat model."""

    def __init__(self, api_key: str) -> None:
        """Create a controller with an OpenRouter API key.

        The key is saved on the instance and copied into ``OPENROUTER_API_KEY``
        because LangChain's OpenRouter provider reads that environment variable
        during model initialization.
        """
        self.api_key = api_key
        os.environ[OPEN_ROUTER_API_KEY_ENV_VAR] = api_key
        self.model: LangChainChatClient = LangChainChatClient(
            model_name="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            model_provider="openrouter",
        )
        self.model.set_system_prompt("You are a helpful assistant.")
        self.model.configure()

    def prompt_model(self, prompt: str) -> str | None:
        """Send a prompt to the configured model and return its response."""
        return self.model.prompt(prompt)
