# HABLA Agentic Engine V5 — HABLA + LACE

Motor de razonamiento agéntico modular con:

- HABLA V4.2: clasificación semántica, ReAct, RAG, herramientas, triangulación, confianza por componente, orquestador de subtareas y memoria episódica.
- LACE v2.0: loop de autocrítica y creatividad evolutiva con 10 ciclos obligatorios antes de cierre.

## Novedad V5

`LACE.md` ahora es una política de arranque. El runtime lo lee antes de activar el LLM, Codex CLI u otro agente. La directiva LACE se inyecta en el prompt de salida del motor.

## Estructura

```text
habla_agentic_engine/
├── LACE.md
├── LACE_LOG.md                 # se crea en ejecución
├── runtime/
│   ├── engine.py               # HablaEngineV5
│   ├── lace.py                 # LacePolicy, LaceLog, LaceGate, LaceRuntime
│   ├── lace_cli.py             # inicializador LACE
│   ├── planner.py              # orquestador de subtareas
│   ├── tools.py                # ToolRegistry
│   └── ...
├── chat/chat_cli.py            # chat humano → HABLA → LLM/Codex
├── connectors/                 # echo, ollama, codex_cli
├── tests/
└── docs/
```

## Prueba rápida

```bash
python -m pytest -q
python -m runtime.lace_cli "Crear un juego en Python" --scaffold
python -m chat.chat_cli --provider echo --show-debug
```

## Codex CLI

```bash
python -m chat.chat_cli --provider codex --codex-cmd "codex" --show-debug
```

## Ollama

```bash
python -m chat.chat_cli --provider ollama --model gemma:2b --show-debug
```

## Desactivar LACE

```bash
python -m chat.chat_cli --provider echo --no-lace
```

## Regla de cierre

La puerta LACE no permite declarar un proyecto como terminado hasta que `LACE_LOG.md` documente 10 ciclos con mejora objetiva real.

## V5.1 — LACE Visual + Puerta Ejecutable

Esta versión agrega la capa visual/auditable de LACE:

- `docs/visual/lace_system_diagram.html`: diagrama completo del loop LACE.
- `docs/visual/lace_md_execution_explained.html`: explicación de cómo el `.md` se convierte en contexto operativo.
- `runtime/lace_visual_cli.py`: imprime el modelo visual y estado de cierre en terminal.
- `LaceRuntime.record_cycle_completion(...)`: registra ciclos reales.
- `LaceRuntime.next_required_action()`: indica la siguiente acción obligatoria.

Comandos:

```bash
python -m runtime.lace_cli "Crear un juego en Python" --scaffold
python -m runtime.lace_visual_cli --init --prompt "Crear un juego en Python"
bash scripts/open_lace_visual.sh
pytest -q
```
