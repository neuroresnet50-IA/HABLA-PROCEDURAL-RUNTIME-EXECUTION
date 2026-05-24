import subprocess
from .base import LLMConnector

class CodexCLIConnector(LLMConnector):
    """Conector genérico para Codex CLI o cualquier CLI compatible.

    Modo seguro por defecto:
    - Envía el prompt por STDIN.
    - Captura STDOUT.

    Si tu Codex CLI usa otra sintaxis, cambia cmd_args.
    Ejemplos posibles:
        codex
        codex --ask
        codex exec
    """
    def __init__(self, command: str = "codex", timeout: int = 180):
        self.command = command
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        cmd = self.command.split()
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout,
            )
            if proc.returncode != 0:
                return f"[ERROR CODEX CLI]\nSTDERR:\n{proc.stderr}\nSTDOUT:\n{proc.stdout}"
            return proc.stdout.strip()
        except FileNotFoundError:
            return "[ERROR CODEX CLI] No se encontró el comando codex. Verifica que 'codex' esté en PATH."
        except subprocess.TimeoutExpired:
            return "[ERROR CODEX CLI] Timeout ejecutando Codex CLI."
        except Exception as e:
            return f"[ERROR CODEX CLI] {e}"
