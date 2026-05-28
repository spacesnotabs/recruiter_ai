import logging

logger = logging.getLogger(__name__)

"""
Base class for an LLM model
"""
class BaseLLM():
    def __init__(self, model_name: str):
        self._model_name: str = model_name
        self._system_prompt: str | None = None

    @property
    def model_name(self) -> str:
        return self._model_name
    
    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement this method.")
    
    def set_system_prompt(self, prompt:str):
        raise NotImplementedError("Subclasses must implement this method.")
    
    def prompt(self, prompt: str) -> str:
        raise NotImplementedError("Subclasses must implement this method.")

    def configure(self, **kwargs):
        pass

    def set_api_key(self, api_key:str):
        pass

class LocalLLM(BaseLLM):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self._model_filepath: str = ""

    @property
    def model_filepath(self) -> str:
        return self._model_filepath

    @model_filepath.setter
    def model_filepath(self, filepath: str):
        self._model_filepath = filepath
        # Here you would add code to load the model from the specified filepath

    def generate(self, prompt: str) -> str:
        # Placeholder implementation for local LLM generation
        return f"Generated response for prompt: {prompt} with system prompt: {self.system_prompt}"

    def set_system_prompt(self, prompt:str):
        self.system_prompt = prompt

    def configure(self, **kwargs):
        # Placeholder for any additional configuration needed for the local LLM
        pass
