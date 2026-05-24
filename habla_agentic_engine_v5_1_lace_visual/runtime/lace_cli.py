import argparse
from pathlib import Path
from runtime.lace import LaceRuntime


def main():
    parser = argparse.ArgumentParser(description="Inicializa LACE antes de ejecutar un agente LLM/Codex.")
    parser.add_argument("prompt", help="Prompt del proyecto o ruta a archivo")
    parser.add_argument("--lace", default="LACE.md", help="Ruta a LACE.md")
    parser.add_argument("--log", default="LACE_LOG.md", help="Ruta a LACE_LOG.md")
    parser.add_argument("--scaffold", action="store_true", help="Crear plantillas de 10 ciclos sin marcarlas como completadas")
    args = parser.parse_args()

    p = Path(args.prompt)
    project_prompt = p.read_text(encoding="utf-8") if p.exists() else args.prompt
    runtime = LaceRuntime(policy_path=args.lace, log_path=args.log)
    directive = runtime.preflight(project_prompt)
    if args.scaffold:
        runtime.scaffold_cycles()
    can_close, status = runtime.closure_status()
    print("=== DIRECTIVA LACE ===")
    print(directive)
    print("\n=== ESTADO PUERTA DE CIERRE ===")
    print(status)
    print("\n=== LOG ===")
    print(Path(args.log).resolve())


if __name__ == "__main__":
    main()
