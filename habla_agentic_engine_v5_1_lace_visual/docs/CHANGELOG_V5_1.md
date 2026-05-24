# CHANGELOG V5.1 — LACE como motor visual + política ejecutable

## Cambios principales

- Se integran los diagramas HTML de LACE dentro de `docs/visual/`.
- Se añade modelo explícito de fases LACE: arranque, base, ciclos, puerta de calidad y cierre.
- Se añade `LaceStep`, `LaceVisualModel` y `LaceRunState` para auditar el avance.
- `LacePolicy` ahora detecta automáticamente la cantidad de ciclos requerida desde `LACE.md` cuando el texto contiene reglas como “10 ciclos”.
- Se añade `LaceRuntime.next_required_action()` para que el agente sepa qué debe hacer antes de cerrar.
- Se añade `LaceRuntime.record_cycle_completion()` para registrar ciclos reales con “¿Mejoró? SI”.
- Se añade CLI `runtime/lace_visual_cli.py` para inspeccionar el diagrama lógico en terminal.
- Se añade `scripts/open_lace_visual.sh` para abrir el diagrama HTML.
- Nuevos tests para visualización, parser de ciclos, puerta de calidad y registro de ciclos.

## Resultado

V5.1 convierte LACE en una capa más fuerte:

```text
LACE.md → política leída antes de actuar
LaceRuntime → ejecutor de preflight y puerta
LaceVisualModel → diagrama auditable del flujo
LACE_LOG.md → evidencia de ciclos reales
```
