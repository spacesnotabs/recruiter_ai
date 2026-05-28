"""Shared abstractions for language model integrations."""

from __future__ import annotations


class BaseLLM:
    """Base interface for local and remote language model wrappers."""

    def __init__(self, model_name: str) -> None:
        """Create a model wrapper with a provider-specific model name."""
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

    def prompt(self, prompt: str) -> str:
        """Send a prompt to the model and return its text response."""
        raise NotImplementedError("Subclasses must implement this method.")

    def configure(self, **kwargs: object) -> None:
        """Apply implementation-specific configuration before prompting."""
        pass

    def set_api_key(self, api_key: str) -> None:
        """Store an API key for providers that require explicit credentials."""
        pass


class LocalLLM(BaseLLM):
    """Placeholder local model wrapper for future local inference support."""

    def __init__(self, model_name: str) -> None:
        """Create a local model wrapper with no loaded model file."""
        super().__init__(model_name)
        self._model_filepath: str = ""

    @property
    def model_filepath(self) -> str:
        """Return the configured local model file path."""
        return self._model_filepath

    @model_filepath.setter
    def model_filepath(self, filepath: str) -> None:
        """Set the local model file path without loading the model yet."""
        self._model_filepath = filepath
        # Here you would add code to load the model from the specified filepath

    def generate(self, prompt: str) -> str:
        """Return a placeholder response for local model generation."""
        return f"Generated response for prompt: {prompt} with system prompt: {self.system_prompt}"

    def configure(self, **kwargs: object) -> None:
        """Accept local model configuration options for future use."""
        pass
