from .base import LLMConnector

class EchoConnector(LLMConnector):
    def generate(self, prompt: str) -> str:
        return "[ECHO LLM]\n" + prompt[-2000:]
