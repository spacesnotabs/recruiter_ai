from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, BaseMessage
from llm_base import BaseLLM
import logging

logger = logging.getLogger(__name__)

class LangChainLLM(BaseLLM):
    def __init__(self, model_name: str, model_provider: str):
        super().__init__(model_name)
        self._api_key: str = ""
        self._model: BaseChatModel | None = None
        self._model_provider: str = model_provider
        self._conversation_history: list[BaseMessage] = []

    @property
    def model(self) -> BaseChatModel | None:
        return self._model

    def generate(self, prompt: str) -> str:
        # Placeholder implementation for remote LLM generation
        return f"Generated response for prompt: {prompt} with system prompt: {self.system_prompt}"

    def set_system_prompt(self, prompt:str):
        self.system_prompt = prompt
        self._conversation_history.append(SystemMessage(content=prompt))

    def set_api_key(self, api_key:str):
        self._api_key = api_key

    def configure(self, **kwargs):
        # create the chat model if it doesn't already exist
        if self._model is None:
            self._model = init_chat_model(
                model=self._model_name,
                model_provider=self._model_provider,
            )
        else:
            # If the model already exists, we might want to reconfigure it with new parameters
            # This is a placeholder for any reconfiguration logic needed for the existing model
            logger.info(f"Model already initialized.")

    def prompt(self, prompt: str) -> str | None:
        logger.info(f"Prompting model with input: {prompt}")
        if self.system_prompt is None:
            raise ValueError("System prompt is not set. Please call set_system_prompt() before prompting.")
            return None

        if self._model is None:
            raise ValueError("Model is not configured. Please call configure() before prompting.")
            return None

        # TODO Validate user prompt
        self._conversation_history.append(HumanMessage(content=prompt))
        response: AIMessage = self._model.invoke(input=prompt)
        self._conversation_history.append(response)

        return response.text