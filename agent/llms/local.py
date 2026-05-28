"""Local language model client placeholder."""

from __future__ import annotations

from .base import LLMClient


class LocalLLMClient(LLMClient):
    """Placeholder local model client for future local inference support."""

    def __init__(self, model_name: str) -> None:
        """Create a local model client with no loaded model file."""
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
