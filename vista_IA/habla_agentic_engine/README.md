# HABLA Agentic Reasoning Engine V4

**HABLA** es un lenguaje procedimental agéntico y un runtime de razonamiento avanzado diseñado para controlar cómo un LLM razona antes de responder.

Este proyecto incluye:

- Motor fundacional **HABLA BASIC V4**.
- Runtime Python para ejecutar protocolos HABLA.
- Conversor de prompt normal a prompt HABLA.
- Motor agéntico con:
  - Semantic Classifier
  - ReAct Loop
  - RAG simulado
  - Tool Use
  - Triangulación
  - Confianza por componente
  - Constitutional Check
  - Memoria episódica
- Conectores para:
  - Ollama local
  - Codex CLI / cualquier CLI LLM
  - Echo mock para pruebas sin modelo
- Chat CLI rápido.
- Tests básicos.

---

## 1. Instalación rápida

```bash
cd habla_agentic_engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Probar sin LLM

```bash
python -m chat.chat_cli --provider echo
```

---

## 3. Probar con Ollama

Primero asegúrate de tener Ollama corriendo:

```bash
ollama serve
ollama run gemma:2b
```

Luego:

```bash
python -m chat.chat_cli --provider ollama --model gemma:2b
```

---

## 4. Probar con Codex CLI

Este conector asume que puedes ejecutar `codex` en terminal.

```bash
python -m chat.chat_cli --provider codex --codex-cmd codex
```

El flujo será:

```text
Humano → Codificador HABLA → Motor HABLA V4 → Prompt estructurado → Codex CLI → Respuesta procesada
```

---

## 5. Convertir un prompt normal a HABLA

```bash
python -m runtime.prompt_converter examples/normal_prompt_01.txt
```

---

## 6. Ejecutar protocolo HABLA desde archivo

```bash
python -m runtime.habla_cli examples/habla_prompt_01.habla --provider echo
```

---

## 7. Ejecutar tests

```bash
pytest -q
```

---

## 8. Estructura

```text
habla_agentic_engine/
├── habla_basic/              # Modelo fundacional HABLA BASIC V4
├── runtime/                  # Motor Python V4
├── connectors/               # Ollama, Codex CLI, Echo
├── chat/                     # Chat CLI
├── examples/                 # Prompts normales y HABLA
├── docs/                     # Guías y paper
├── tests/                    # Tests
├── memory/                   # Memoria episódica JSONL
├── logs/                     # Logs del runtime
└── scripts/                  # Scripts auxiliares
```

---

## Idea central

HABLA no deja que el LLM responda directo. Primero transforma la pregunta humana en una estructura procedimental, luego ejecuta el razonamiento y finalmente entrega al LLM una directiva controlada.

```text
Pregunta humana
  ↓
Codificador HABLA
  ↓
Semantic Classifier
  ↓
ReAct Loop
  ↓
RAG / Tool Use
  ↓
Triangulación
  ↓
Confianza por componente
  ↓
Constitutional Check
  ↓
LLM responde bajo control del motor
```
