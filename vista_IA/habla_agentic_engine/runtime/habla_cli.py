import argparse
from pathlib import Path
from connectors.factory import make_connector
from runtime.engine import HablaEngineV4


def main():
    parser = argparse.ArgumentParser(description="Ejecuta HABLA Engine V4 desde texto o archivo.")
    parser.add_argument("input", help="Pregunta directa o ruta a archivo .habla/.txt")
    parser.add_argument("--provider", default="echo", choices=["echo", "ollama", "codex"])
    parser.add_argument("--model", default="gemma:2b")
    parser.add_argument("--codex-cmd", default="codex")
    args = parser.parse_args()

    p = Path(args.input)
    question = p.read_text(encoding="utf-8") if p.exists() else args.input
    llm = make_connector(args.provider, model=args.model, codex_cmd=args.codex_cmd)
    engine = HablaEngineV4(llm=llm)
    state = engine.run(question.strip())

    print("\n=== RESPUESTA ===")
    print(state.answer)
    print("\n=== DEBUG HABLA ===")
    for line in state.debug:
        print("-", line)
    print("\n=== DIRECTIVA ENVIADA AL LLM ===")
    print(state.llm_directive)

if __name__ == "__main__":
    main()
