"""Controller for prompting the configured OpenRouter chat model."""

from __future__ import annotations

import os
import logging
from typing import Any

from langchain.chat_models import init_chat_model


logger = logging.getLogger(__name__)
OPEN_ROUTER_API_KEY_ENV_VAR = "OPENROUTER_API_KEY"


class Controller:
    """Prompting facade for the OpenRouter-backed chat model."""

    def __init__(self, api_key: str) -> None:
        """Create a controller with an OpenRouter API key.

        The key is saved on the instance and copied into ``OPENROUTER_API_KEY``
        because LangChain's OpenRouter provider reads that environment variable
        during model initialization.
        """
        self.api_key = api_key
        os.environ[OPEN_ROUTER_API_KEY_ENV_VAR] = api_key
        self.model = init_chat_model(
            model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            model_provider="openrouter",
        )

    def prompt_model(self, prompt: str) -> Any:
        """Send a prompt to the configured model and return its response."""
        logger.info(f"Prompting model with input: {prompt}")
        return self.model.invoke(input=prompt)
