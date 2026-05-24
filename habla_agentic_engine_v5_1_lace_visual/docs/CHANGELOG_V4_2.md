# CHANGELOG V4.2

## Cierre final del razonamiento agéntico

### 1. Orquestador de sub-tareas
Se añadió `runtime/planner.py` con `CompoundPlanner`.

Caso inicial soportado:

```text
PIB per cápita = PIB nominal reciente / población reciente
```

El motor ahora puede detectar preguntas compuestas y convertirlas en subtareas coordinadas:

1. Recuperar población reciente.
2. Recuperar PIB nominal reciente.
3. Calcular PIB per cápita.
4. Responder con confianza por componente.

Esto evita que el motor trate preguntas compuestas como si fueran preguntas atómicas.

### 2. Corrección matemática de `global_score`
Antes, `Confidence.global_score` dividía siempre entre 5 componentes, incluso cuando algunos no aplicaban:

```python
return sum(values) / len(values)
```

Ahora solo promedia componentes activos:

```python
active = [v for v in values if v > 0]
return sum(active) / len(active) if active else 0.0
```

Ejemplo:

```text
dato=90, fecha=85, fuente=88, calculo=0, inferencia=0
antes: 52.6
ahora: 87.7
```

### 3. Herramientas nuevas
`ToolRegistry` incluye:

- `population_official`
- `gdp_official`
- `calculator_internal` vía orquestador compuesto

`gdp_official` usa World Bank (`NY.GDP.MKTP.CD`) cuando hay internet, y fixtures offline para pruebas.

### 4. Tests
Suite actual:

```text
7 passed
```

Tests nuevos:

- `test_global_score_ignores_inactive_components`
- `test_compound_gdp_per_capita_orchestrates_subtasks`
