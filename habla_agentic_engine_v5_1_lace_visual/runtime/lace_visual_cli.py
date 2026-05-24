from __future__ import annotations

import argparse
from runtime.lace import LaceRuntime


def main() -> None:
    parser = argparse.ArgumentParser(description="Muestra el modelo visual/auditable de LACE en terminal.")
    parser.add_argument("--lace", default="LACE.md")
    parser.add_argument("--log", default="LACE_LOG.md")
    parser.add_argument("--prompt", default="Proyecto sin prompt explícito")
    parser.add_argument("--init", action="store_true", help="Inicializa LACE_LOG.md antes de mostrar estado")
    args = parser.parse_args()

    runtime = LaceRuntime(policy_path=args.lace, log_path=args.log)
    if args.init:
        runtime.preflight(args.prompt)
    print(runtime.visual_markdown())


if __name__ == "__main__":
    main()
