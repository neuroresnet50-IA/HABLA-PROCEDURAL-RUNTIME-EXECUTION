import re
from typing import Optional
from .types import HablaState, SubTask


class CompoundPlanner:
    """Orquestador ligero para preguntas compuestas.

    No reemplaza el motor HABLA: se sienta encima. Su trabajo es detectar
    preguntas que requieren varias piezas de evidencia coordinadas.

    Ejemplo:
        "PIB per cápita de México" = PIB total + población + cálculo.
    """

    GDP_PER_CAPITA_PATTERNS = [
        r"\b(pib|gdp)\s*(per\s*c[aá]pita|per\s*capita|por\s*persona)\b",
        r"\b(per\s*c[aá]pita|per\s*capita)\b.*\b(pib|gdp)\b",
    ]

    def plan(self, state: HablaState) -> HablaState:
        q = state.question.lower()
        if any(re.search(p, q, flags=re.IGNORECASE) for p in self.GDP_PER_CAPITA_PATTERNS):
            country = self._extract_country_name(state.question) or "pais_no_detectado"
            state.is_compound = True
            state.compound_goal = "calcular_pib_per_capita"
            state.sub_tasks = [
                SubTask(
                    task_id="population",
                    description=f"Recuperar población reciente de {country}",
                    tool_name="population_official",
                    query=f"población reciente de {country}",
                ),
                SubTask(
                    task_id="gdp",
                    description=f"Recuperar PIB nominal reciente de {country}",
                    tool_name="gdp_official",
                    query=f"PIB nominal reciente de {country}",
                ),
                SubTask(
                    task_id="calculate_gdp_per_capita",
                    description="Dividir PIB nominal entre población",
                    tool_name="calculator_internal",
                    query="gdp / population",
                ),
            ]
            state.strategy = "orquestar_subtareas_pib_per_capita"
            state.log(f"PLANNER => pregunta compuesta detectada: {state.compound_goal}, country={country}")
        else:
            state.log("PLANNER => pregunta atómica")
        return state

    def _extract_country_name(self, question: str) -> Optional[str]:
        patterns = [
            r"(?:de|del|para|en)\s+([A-ZÁÉÍÓÚÑÜa-záéíóúñü ]+?)(?:\?|$|\.|,)",
        ]
        for pat in patterns:
            m = re.search(pat, question, flags=re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                candidate = re.sub(r"\b(actual|actualmente|reciente|recientes)\b", "", candidate, flags=re.I).strip()
                # Limpieza de restos frecuentes de la frase.
                candidate = re.sub(r"\b(pib|gdp|per\s*c[aá]pita|per\s*capita|por\s*persona)\b", "", candidate, flags=re.I).strip()
                if candidate:
                    return candidate
        for name in ["México", "Mexico", "Francia", "France", "Colombia", "Estados Unidos", "USA"]:
            if name.lower() in question.lower():
                return name
        return None
