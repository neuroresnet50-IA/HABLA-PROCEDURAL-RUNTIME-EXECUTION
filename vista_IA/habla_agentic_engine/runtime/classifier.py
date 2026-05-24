import json
import re
from typing import Optional

from .types import HablaState

TEMPORAL_PATTERNS = [
    r"\b(actual|hoy|ayer|mañana|reciente|último|ultimo|ahora|202\d|precio|presidente|ceo|versi[oó]n|clima|noticias)\b",
    r"\b(poblaci[oó]n|habitantes|cu[aá]nta gente|cu[aá]ntas personas|vive en|viven en|residentes)\b",
    r"\b(current|latest|population|inhabitants|residents|price|weather|news)\b",
]
CALC_PATTERNS = [
    r"\b(calcula|cu[aá]nto es|suma|multiplica|divide|ra[ií]z|porcentaje|calcular|resolver)\b",
    r"[0-9]+\s*[+\-*/]\s*[0-9]+",
]
OPINION_PATTERNS = [r"\b(opini[oó]n|crees|estrategia|recomienda|interpreta|analiza|qué piensas|que piensas)\b"]
ALLOWED_TYPES = {"HECHO_TEMPORAL", "CALCULO", "HECHO_ESTABLE", "INFERENCIA_OPINION", "AMBIGUA"}


class SemanticClassifier:
    """Clasificador semántico híbrido: LLM-first, reglas como fallback."""

    def __init__(self, llm: Optional[object] = None):
        self.llm = llm

    def classify(self, state: HablaState) -> HablaState:
        llm_result = self._classify_with_llm(state.question) if self.llm is not None else None
        if llm_result:
            knowledge_type = llm_result.get("knowledge_type", "").strip().upper()
            if knowledge_type in ALLOWED_TYPES:
                self._apply_type(state, knowledge_type, reason=llm_result.get("reason", "clasificación LLM"), source="llm_classifier")
                return state
            state.log(f"CLASSIFY_LLM_INVALID => {llm_result}")

        self._classify_with_rules(state)
        return state

    def _classify_with_llm(self, question: str) -> Optional[dict]:
        prompt = f"""
Eres un clasificador semántico para un motor de razonamiento HABLA.
NO respondas la pregunta humana.
Devuelve SOLO JSON válido con estas claves:
{{"knowledge_type":"HECHO_TEMPORAL|CALCULO|HECHO_ESTABLE|INFERENCIA_OPINION|AMBIGUA","tool_required":"...","strategy":"...","reason":"..."}}

Criterios:
- HECHO_TEMPORAL: datos del mundo real que pueden cambiar o dependen de fecha/lugar/fuente: población, habitantes, precios, clima, presidentes, CEO, versiones, noticias, estadísticas actuales.
- CALCULO: operación matemática exacta.
- HECHO_ESTABLE: definiciones, conceptos estables, explicación técnica no temporal.
- INFERENCIA_OPINION: juicio, recomendación, interpretación o análisis subjetivo.
- AMBIGUA: no se puede clasificar con seguridad.

Pregunta: {question}
""".strip()
        try:
            raw = self.llm.generate(prompt).strip()
            raw = self._extract_json(raw)
            return json.loads(raw)
        except Exception:
            return None

    def _extract_json(self, text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end + 1]
        return text

    def _classify_with_rules(self, state: HablaState) -> None:
        question = state.question.lower()
        if any(re.search(pattern, question) for pattern in CALC_PATTERNS):
            self._apply_type(state, "CALCULO", "patrones de cálculo", "rule_fallback")
        elif any(re.search(pattern, question) for pattern in TEMPORAL_PATTERNS):
            self._apply_type(state, "HECHO_TEMPORAL", "patrones de hecho temporal/ampliado", "rule_fallback")
        elif any(re.search(pattern, question) for pattern in OPINION_PATTERNS):
            self._apply_type(state, "INFERENCIA_OPINION", "patrones de opinión/inferencia", "rule_fallback")
        else:
            self._apply_type(state, "HECHO_ESTABLE", "fallback estable por falta de señales temporales", "rule_fallback")

    def _apply_type(self, state: HablaState, knowledge_type: str, reason: str, source: str) -> None:
        state.knowledge_type = knowledge_type
        if knowledge_type == "CALCULO":
            state.tool_required = "calculator"
            state.strategy = "calcular_exactamente"
        elif knowledge_type == "HECHO_TEMPORAL":
            state.tool_required = "rag_or_external"
            state.strategy = "buscar_fuentes_actualizadas_y_contrastar"
        elif knowledge_type == "INFERENCIA_OPINION":
            state.tool_required = "llm_reasoning_declared"
            state.strategy = "responder_como_inferencia_declarada"
        elif knowledge_type == "AMBIGUA":
            state.tool_required = "clarification_or_block"
            state.strategy = "bloquear_o_pedir_aclaracion"
            state.blocked = True
            state.block_reason = "La pregunta es ambigua para el clasificador semántico."
        else:
            state.tool_required = "memory_optional"
            state.strategy = "memoria_con_verificacion_opcional"
        state.log(f"CLASSIFY => {state.knowledge_type} / {state.tool_required} / {source} / {reason}")
