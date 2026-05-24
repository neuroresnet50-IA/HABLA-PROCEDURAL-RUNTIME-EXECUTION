# HABLA V4.1 — Cierre de implementación pendiente

## Problema detectado
La V4 tenía una arquitectura correcta, pero faltaban tres implementaciones para acercarse a un agente real:

1. Herramientas simuladas.
2. Clasificador basado en regex.
3. Memoria episódica que guardaba pero no influía.

## Solución V4.1

### 1. ToolRegistry real e inyectable
`runtime/tools.py` ahora tiene:

- `calculator` seguro con AST.
- `rag_local` sobre corpus local.
- `official_source` con REST Countries + World Bank.
- `general_source` con REST Countries.
- modo fixture offline solo para pruebas: `HABLA_USE_OFFLINE_FIXTURES=1`.
- `register()` e inyección desde `HablaEngineV4(tools={...})`.

### 2. Clasificador semántico LLM-first
`runtime/classifier.py` ahora:

- usa un LLM si está disponible,
- exige JSON de clasificación,
- cae a reglas ampliadas si el LLM falla,
- clasifica preguntas como “¿Cuántos habitantes tiene Francia?” como `HECHO_TEMPORAL`.

### 3. Memoria episódica activa
`runtime/memory.py` ahora:

- lee registros recientes,
- calcula estadísticas por herramienta,
- reordena el plan de herramientas del motor,
- permite que el agente evite primero herramientas que han fallado repetidamente.

## Validación

```bash
pytest -q
# 5 passed
```
