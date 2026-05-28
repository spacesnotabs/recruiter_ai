"""LangChain-backed language model integration."""

from __future__ import annotations

import logging

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .llm_base import BaseLLM

logger = logging.getLogger(__name__)


class LangChainLLM(BaseLLM):
    """Language model wrapper that delegates chat completion to LangChain."""

    def __init__(self, model_name: str, model_provider: str) -> None:
        """Create a LangChain model wrapper for the given provider."""
        super().__init__(model_name)
        self._api_key: str = ""
        self._model: BaseChatModel | None = None
        self._model_provider: str = model_provider
        self._conversation_history: list[BaseMessage] = []

    @property
    def model(self) -> BaseChatModel | None:
        """Return the configured LangChain chat model, if initialized."""
        return self._model

    def generate(self, prompt: str) -> str:
        """Return a placeholder response for stateless generation."""
        return f"Generated response for prompt: {prompt} with system prompt: {self.system_prompt}"

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt and reset the conversation to use it."""
        super().set_system_prompt(prompt)
        self._conversation_history = [SystemMessage(content=prompt)]

    def set_api_key(self, api_key: str) -> None:
        """Store an API key for callers that manage credentials explicitly."""
        self._api_key = api_key

    def configure(self, **kwargs: object) -> None:
        """Initialize the LangChain chat model if it has not been created."""
        if self._model is None:
            self._model = init_chat_model(
                model=self._model_name,
                model_provider=self._model_provider,
            )
        else:
            logger.info("Model already initialized.")

    def prompt(self, prompt: str) -> str | None:
        """Send a prompt with conversation history and return model text."""
        logger.debug("Prompting model with input: %s", prompt)
        if self.system_prompt is None:
            raise ValueError("System prompt is not set. Please call set_system_prompt() before prompting.")

        if self._model is None:
            raise ValueError("Model is not configured. Please call configure() before prompting.")

        # TODO Validate user prompt
        self._conversation_history.append(HumanMessage(content=prompt))
        response: AIMessage = self._model.invoke(input=self._conversation_history)
        self._conversation_history.append(response)

        return response.text
