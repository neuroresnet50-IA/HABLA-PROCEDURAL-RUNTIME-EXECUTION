import requests
from .base import LLMConnector

class OllamaConnector(LLMConnector):
    def __init__(self, model: str = "gemma:2b", host: str = "http://127.0.0.1:11434"):
        self.model = model
        self.host = host.rstrip("/")

    def generate(self, prompt: str) -> str:
        url = f"{self.host}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            return r.json().get("response", "")
        except Exception as e:
            return f"[ERROR OLLAMA] {e}"
