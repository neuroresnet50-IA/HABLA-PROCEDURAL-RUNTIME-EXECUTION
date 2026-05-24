# CHANGELOG V5 — HABLA + LACE

## Cambios principales

- `LACE.md` queda embebido como política de arranque obligatoria.
- `HablaEngineV5` lee `LACE.md` antes de construir la directiva para LLM/Codex.
- Se crea/inicializa `LACE_LOG.md` automáticamente.
- Se agrega `runtime/lace.py` con:
  - `LacePolicy`
  - `LaceLog`
  - `LaceGate`
  - `LaceRuntime`
- Se agrega `runtime/lace_cli.py` para inicializar LACE desde terminal.
- `chat_cli.py` y `habla_cli.py` aceptan `--lace`, `--lace-log` y `--no-lace`.
- La directiva enviada al LLM ahora incluye el bloque LACE antes del protocolo HABLA.

## Importante

El sistema NO falsifica los 10 ciclos. `scaffold_cycles()` crea plantillas para guiar al agente, pero no marca los ciclos como completados. La puerta de cierre solo pasa si `LACE_LOG.md` contiene 10 ciclos con mejora objetiva real.
