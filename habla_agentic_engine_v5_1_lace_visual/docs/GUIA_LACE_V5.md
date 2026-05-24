# Guía V5 — Cómo usar HABLA + LACE con Codex, Ollama o cualquier LLM

## 1. Instalar

```bash
cd habla_agentic_engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Verificar que LACE.md existe

```bash
ls LACE.md
```

`LACE.md` debe estar en la raíz. El motor lo lee antes de activar el agente.

## 3. Inicializar LACE para un proyecto

```bash
python -m runtime.lace_cli "Crear un juego en Python con pygame" --scaffold
```

Esto crea `LACE_LOG.md` con el plan inicial y las plantillas de 10 ciclos.

## 4. Chat con motor HABLA y LACE

### Echo local de prueba

```bash
python -m chat.chat_cli --provider echo --show-debug
```

### Ollama

```bash
ollama run gemma:2b
python -m chat.chat_cli --provider ollama --model gemma:2b --show-debug
```

### Codex CLI

```bash
python -m chat.chat_cli --provider codex --codex-cmd "codex" --show-debug
```

La pregunta humana pasa por:

```text
Humano → HABLA → LACE → directiva razonada → Codex/LLM → respuesta procesada
```

## 5. Ejecutar una sola pregunta

```bash
python -m runtime.habla_cli "Cuál es el PIB per cápita de México?" --provider echo
```

## 6. Desactivar LACE si solo quieres pruebas atómicas

```bash
python -m chat.chat_cli --provider echo --no-lace
```

## 7. Regla de cierre

El proyecto no debe declararse terminado hasta que `LACE_LOG.md` tenga 10 ciclos reales con:

```text
¿El proyecto mejoró objetivamente? SI
```

Si no hay 10, la puerta de cierre bloquea.
