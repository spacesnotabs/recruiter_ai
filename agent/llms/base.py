"""Shared abstractions for language model integrations."""

from __future__ import annotations


class LLMClient:
    """Base interface for local and remote language model clients."""

    def __init__(self, model_name: str) -> None:
        """Create a model client with a provider-specific model name."""
        self._model_name: str = model_name
        self._system_prompt: str | None = None

    @property
    def model_name(self) -> str:
        """Return the provider-specific model identifier."""
        return self._model_name

    @property
    def system_prompt(self) -> str | None:
        """Return the system prompt configured for the model, if any."""
        return self._system_prompt

    def generate(self, prompt: str) -> str:
        """Generate text from a prompt without preserving conversation state."""
        raise NotImplementedError("Subclasses must implement this method.")

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt used to guide future model responses."""
        self._system_prompt = prompt

    def reset_history(self) -> None:
        """Reset the conversation history"""
        raise NotImplementedError("Subclasses must implement this method.")

    def prompt(self, prompt: str) -> str:
        """Send a prompt to the model and return its text response."""
        raise NotImplementedError("Subclasses must implement this method.")

    def configure(self, **kwargs: object) -> None:
        """Apply implementation-specific configuration before prompting."""
        pass

    def set_api_key(self, api_key: str) -> None:
        """Store an API key for providers that require explicit credentials."""
        pass
