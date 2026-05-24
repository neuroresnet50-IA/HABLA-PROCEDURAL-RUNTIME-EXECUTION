# Guía paso a paso para ingenieros

## Objetivo
Conectar una pregunta humana con un motor HABLA que estructura el razonamiento antes de enviarlo a un LLM local, Ollama, Codex CLI u otro modelo open source.

---

## Flujo completo

```text
Usuario escribe pregunta
  ↓
Codificador HABLA convierte la pregunta en protocolo
  ↓
Motor HABLA V4 clasifica el tipo de conocimiento
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

## 2. Probar motor sin LLM

```bash
python -m chat.chat_cli --provider echo --show-debug
```

Pregunta:

```text
¿Cuánta gente vive en México?
```

El motor debe:

1. clasificar como HECHO_TEMPORAL,
2. fallar primero con RAG local simulado,
3. usar fuente oficial simulada,
4. intentar segunda fuente,
5. triangular,
6. responder con margen.

---

## 3. Conectar con Ollama

Instala o ejecuta Ollama, luego descarga un modelo:

```bash
ollama run gemma:2b
```

Después corre:

```bash
python -m chat.chat_cli --provider ollama --model gemma:2b --show-debug
```

---

## 4. Conectar con Codex CLI

Si en tu terminal puedes escribir:

```bash
codex
```

y se abre Codex CLI, entonces prueba:

```bash
python -m chat.chat_cli --provider codex --codex-cmd codex --show-debug
```

Si tu Codex usa otra sintaxis, por ejemplo `codex exec`, usa:

```bash
python -m chat.chat_cli --provider codex --codex-cmd "codex exec" --show-debug
```

El conector envía por STDIN la directiva completa que genera HABLA.

---

## 5. Convertir prompt humano a HABLA

```bash
python -m runtime.prompt_converter examples/normal_prompt_01.txt
```

---

## 6. Ejecutar archivo HABLA

```bash
python -m runtime.habla_cli examples/habla_prompt_01.habla --provider echo
```

---

## 7. Integrar otro LLM local

Crea un conector en `connectors/mi_modelo_connector.py`:

```python
from .base import LLMConnector

class MiModeloConnector(LLMConnector):
    def generate(self, prompt: str) -> str:
        # llama tu API local, subprocess, websocket, etc.
        return "respuesta del modelo"
```

Luego agrégalo en `connectors/factory.py`.

---

## 8. Dónde modificar herramientas reales

Archivo:

```text
runtime/tools.py
```

Ahí puedes reemplazar:

- `official_source()` por búsqueda web real,
- `rag_local()` por FAISS/Chroma/Qdrant,
- `calculator()` por Python seguro o API matemática.

---

## 9. Dónde modificar las reglas constitucionales

Archivo:

```text
runtime/constitutional.py
```

---

## 10. Dónde revisar memoria episódica

Archivo generado:

```text
memory/episodic_memory.jsonl
```
