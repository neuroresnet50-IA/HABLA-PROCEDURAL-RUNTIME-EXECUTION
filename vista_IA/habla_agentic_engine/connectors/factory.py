from .echo_connector import EchoConnector
from .ollama_connector import OllamaConnector
from .codex_cli_connector import CodexCLIConnector

def make_connector(provider: str, model: str = "gemma:2b", codex_cmd: str = "codex"):
    provider = provider.lower()
    if provider == "echo":
        return EchoConnector()
    if provider == "ollama":
        return OllamaConnector(model=model)
    if provider == "codex":
        return CodexCLIConnector(command=codex_cmd)
    raise ValueError(f"Provider no soportado: {provider}")
