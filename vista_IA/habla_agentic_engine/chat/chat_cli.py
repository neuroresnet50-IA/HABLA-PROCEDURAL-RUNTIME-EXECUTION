import argparse
from connectors.factory import make_connector
from runtime.engine import HablaEngineV4

BANNER = """
================================================
CHAT HABLA V4
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
    args = parser.parse_args()

    llm = make_connector(args.provider, model=args.model, codex_cmd=args.codex_cmd)
    engine = HablaEngineV4(llm=llm)

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
