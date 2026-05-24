from abc import ABC, abstractmethod

class LLMConnector(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError
