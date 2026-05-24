import argparse
from connectors.factory import make_connector
from runtime.engine import HablaEngineV5

BANNER = """
================================================
CHAT HABLA V5 + LACE
Humano → HABLA → Motor de razonamiento → LLM/CLI
Escribe 'salir' para cerrar.
================================================
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="echo", choices=["echo", "ollama", "codex"])
    parser.add_argument("--model", default="gemma:2b")
    parser.add_argument("--codex-cmd", default="codex")
    parser.add_argument("--show-debug", action="store_true")
    parser.add_argument("--no-lace", action="store_true", help="Desactiva lectura/inyección de LACE.md")
    parser.add_argument("--lace", default="LACE.md", help="Ruta a LACE.md")
    parser.add_argument("--lace-log", default="LACE_LOG.md", help="Ruta a LACE_LOG.md")
    args = parser.parse_args()

    llm = make_connector(args.provider, model=args.model, codex_cmd=args.codex_cmd)
    engine = HablaEngineV5(llm=llm, lace_path=args.lace, lace_log_path=args.lace_log, lace_enabled=not args.no_lace)

    print(BANNER)
    while True:
        try:
            q = input("Humano> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCerrando chat HABLA.")
            break
        if q.lower() in {"salir", "exit", "quit"}:
            break
        if not q:
            continue
        state = engine.run(q)
        print("\nHABLA/LLM>")
        print(state.answer)
        if args.show_debug:
            print("\n[DEBUG]")
            for line in state.debug:
                print("-", line)
        print()

if __name__ == "__main__":
    main()
