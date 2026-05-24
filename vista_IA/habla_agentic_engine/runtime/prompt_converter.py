import sys
from pathlib import Path

TEMPLATE = """PROTOCOLO habla_reasoning_agent_v4:

OBJETIVO:
Resolver la pregunta humana sin inventar información, usando clasificación semántica, ReAct, RAG, triangulación, confianza por componente, verificación constitucional y memoria episódica.

ENTRADA:
-> DEFINE pregunta_usuario COMO "{question}"
-> VERIFICA pregunta_usuario ≠ ""

FASE 0: SEMANTIC_CLASSIFIER
-> ANALIZA pregunta_usuario por significado
-> CLASIFICA como HECHO_TEMPORAL, CALCULO, HECHO_ESTABLE o INFERENCIA_OPINION

FASE 1: THOUGHT
-> DEFINE estrategia según clasificación

FASE 2: ACTION
-> USA herramienta obligatoria si aplica

FASE 3: OBSERVATION
-> SI no hay evidencia, cambia estrategia y reintenta

FASE 4: RAG_RECUPERATION
-> RECUPERA fragmentos candidatos sin validarlos todavía

FASE 5: TRIANGULATE
-> COMPARA fuentes y detecta consistencia, contradicción o evidencia limitada

FASE 6: CONFIDENCE_PER_COMPONENT
-> ASIGNA confianza a dato, fecha, fuente, cálculo e inferencia

FASE 7: CONSTITUTIONAL_CHECK
-> NO inventar
-> NO ocultar incertidumbre
-> SEPARAR hecho, cálculo e inferencia
-> BLOQUEAR si evidencia insuficiente

FASE 8: ANSWER
-> RESPONDE con dato, margen, confianza y límites

FASE 9: EPISODIC_MEMORY_UPDATE
-> GUARDA tipo, herramienta, resultado y confianza
FIN PROTOCOLO
"""

def convert_to_habla(question: str) -> str:
    return TEMPLATE.format(question=question.replace('"', '\\"'))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m runtime.prompt_converter <archivo_o_texto>")
        raise SystemExit(1)
    arg = sys.argv[1]
    p = Path(arg)
    text = p.read_text(encoding="utf-8").strip() if p.exists() else arg
    print(convert_to_habla(text))
