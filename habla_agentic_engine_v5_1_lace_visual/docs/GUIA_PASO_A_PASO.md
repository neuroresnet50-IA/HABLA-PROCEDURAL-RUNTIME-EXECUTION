# Guía paso a paso para ingenieros — HABLA V4.1

## Objetivo
Conectar una pregunta humana con un motor HABLA que estructura el razonamiento antes de enviarlo a un LLM local, Ollama, Codex CLI u otro modelo open source.

---

## Flujo completo

```text
Usuario escribe pregunta
  ↓
Codificador HABLA convierte la pregunta en protocolo
  ↓
Clasificador semántico LLM-first detecta tipo de conocimiento
  ↓
Memoria episódica reordena herramientas según experiencia previa
  ↓
ReAct decide acción y herramienta
  ↓
RAG/Tool Use recupera evidencia o calcula
  ↓
Triangulación compara fuentes
  ↓
Confianza por componente mide dato/fecha/fuente/cálculo/inferencia
  ↓
Constitutional Check bloquea o permite respuesta
  ↓
LLM recibe directiva controlada
  ↓
Chat muestra respuesta final
  ↓
Memoria guarda la experiencia para mejorar la siguiente decisión
```

---

## 1. Preparar entorno

```bash
cd habla_agentic_engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Prueba offline determinística

```bash
export HABLA_USE_OFFLINE_FIXTURES=1
python -m chat.chat_cli --provider echo --show-debug
```

Pregunta:

```text
¿Cuánta gente vive en México?
```

El motor debe:

1. clasificar como `HECHO_TEMPORAL`,
2. intentar `rag_local`,
3. usar fuentes fixture si no hay internet,
4. triangular,
5. responder con margen,
6. guardar memoria episódica.

---

## 3. Prueba con herramientas reales

```bash
unset HABLA_USE_OFFLINE_FIXTURES
python -m chat.chat_cli --provider echo --show-debug
```

Herramientas reales disponibles:

- `official_source`: REST Countries + World Bank.
- `general_source`: REST Countries.
- `rag_local`: archivos `.txt`, `.md`, `.json` en `docs/rag_corpus`.
- `calculator`: cálculo seguro.

---

## 4. Conectar con Ollama

```bash
ollama serve
ollama run gemma:2b
python -m chat.chat_cli --provider ollama --model gemma:2b --show-debug
```

El clasificador semántico intentará pedirle al modelo un JSON de clasificación. Si el modelo no responde JSON válido, HABLA cae a reglas ampliadas.

---

## 5. Conectar con Codex CLI

Si en tu terminal puedes escribir:

```bash
codex
```

prueba:

```bash
python -m chat.chat_cli --provider codex --codex-cmd codex --show-debug
```

Si Codex usa otra forma:

```bash
python -m chat.chat_cli --provider codex --codex-cmd "codex exec" --show-debug
```

El conector envía por STDIN la directiva completa que genera HABLA.

---

## 6. Inyectar herramientas propias

Archivo recomendado: `runtime/tools.py` o desde tu script principal:

```python
from runtime.engine import HablaEngineV4
from runtime.types import Evidence


def buscar_en_mi_base(state):
    return [Evidence(source="mi_base", value=None, text="Fragmento recuperado", confidence_hint=88)]

engine = HablaEngineV4(tools={"rag_local": buscar_en_mi_base})
state = engine.run("pregunta")
print(state.answer)
```

---

## 7. Usar RAG local simple

Crea la carpeta:

```bash
mkdir -p docs/rag_corpus
```

Agrega archivos `.txt` o `.md`. Luego pregunta algo relacionado. También puedes apuntar a otra ruta:

```bash
export HABLA_RAG_CORPUS=/ruta/a/mi/corpus
```

---

## 8. Revisar memoria episódica

```bash
cat memory/episodic_memory.jsonl
```

La memoria registra herramientas usadas, éxito, bloqueo, fuentes y confianza. En V4.1 el motor lee esta memoria y reordena herramientas para próximas preguntas similares.

---

## 9. Ejecutar tests

```bash
pytest -q
```

---

## 10. Archivos clave

```text
runtime/classifier.py      # Clasificador LLM-first + fallback
runtime/tools.py           # Herramientas reales e inyectables
runtime/memory.py          # Memoria que lee y escribe
runtime/engine.py          # Loop agéntico completo
runtime/triangulation.py   # Triangulación
runtime/confidence.py      # Confianza por componente
runtime/constitutional.py  # Reglas de bloqueo/respuesta
connectors/                # Ollama, Codex CLI, Echo
```
