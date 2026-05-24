import argparse
from pathlib import Path
from connectors.factory import make_connector
from runtime.engine import HablaEngineV5


def main():
    parser = argparse.ArgumentParser(description="Ejecuta HABLA Engine V5 + LACE desde texto o archivo.")
    parser.add_argument("input", help="Pregunta directa o ruta a archivo .habla/.txt")
    parser.add_argument("--provider", default="echo", choices=["echo", "ollama", "codex"])
    parser.add_argument("--model", default="gemma:2b")
    parser.add_argument("--codex-cmd", default="codex")
    parser.add_argument("--no-lace", action="store_true", help="Desactiva lectura/inyección de LACE.md")
    parser.add_argument("--lace", default="LACE.md", help="Ruta a LACE.md")
    parser.add_argument("--lace-log", default="LACE_LOG.md", help="Ruta a LACE_LOG.md")
    args = parser.parse_args()

    p = Path(args.input)
    question = p.read_text(encoding="utf-8") if p.exists() else args.input
    llm = make_connector(args.provider, model=args.model, codex_cmd=args.codex_cmd)
    engine = HablaEngineV5(llm=llm, lace_path=args.lace, lace_log_path=args.lace_log, lace_enabled=not args.no_lace)
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
