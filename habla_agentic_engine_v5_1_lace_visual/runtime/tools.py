import ast
import math
import os
import re
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from .types import Evidence, HablaState

@dataclass
class ToolResult:
    evidence: List[Evidence]
    ok: bool = True
    error: str = ""

class ToolRegistry:
    """Registro de herramientas reales e inyectables.

    - calculator: cálculo seguro con AST.
    - rag_local: búsqueda simple en docs locales (carpeta docs/rag_corpus opcional).
    - official_source: API pública real para población de países usando REST Countries + World Bank.
    - secondary_source/general_source: APIs/fuentes alternativas cuando estén disponibles.

    Para pruebas offline puedes activar fixtures:
        HABLA_USE_OFFLINE_FIXTURES=1
    """

    def __init__(self, extra_tools: Optional[Dict[str, Callable[[HablaState], List[Evidence]]]] = None, timeout: int = 12):
        self.timeout = timeout
        self.tools: Dict[str, Callable[[HablaState], List[Evidence]]] = {
            "calculator": lambda state: self.calculator(state.question),
            "rag_local": lambda state: self.rag_local(state.question),
            "official_source": lambda state: self.official_source(state.question),
            "population_official": lambda state: self.official_source(state.question),
            "gdp_official": lambda state: self.gdp_official(state.question),
            "secondary_source": lambda state: self.secondary_source(state.question),
            "general_source": lambda state: self.general_source(state.question),
            "memory_optional": lambda state: [Evidence(source="memoria_llm", value=None, text="Conocimiento estable recuperado desde memoria interna.", confidence_hint=40)],
        }
        if extra_tools:
            self.tools.update(extra_tools)

    def register(self, name: str, fn: Callable[[HablaState], List[Evidence]]) -> None:
        self.tools[name] = fn

    def run(self, state: HablaState, tool_name: str) -> List[Evidence]:
        fn = self.tools.get(tool_name)
        if fn is None:
            state.log(f"TOOL_ERROR => herramienta no registrada: {tool_name}")
            return []
        try:
            return fn(state)
        except Exception as exc:
            state.log(f"TOOL_ERROR => {tool_name}: {exc}")
            return []

    def calculator(self, question: str) -> List[Evidence]:
        expr = self._extract_math_expression(question)
        if not expr:
            return []
        try:
            value = self._safe_eval(expr)
            return [Evidence(source="calculadora", value=float(value), text=f"Resultado calculado: {value}", confidence_hint=99)]
        except Exception:
            return []

    def rag_local(self, question: str) -> List[Evidence]:
        corpus_dir = os.getenv("HABLA_RAG_CORPUS", "docs/rag_corpus")
        if not os.path.isdir(corpus_dir):
            return []
        terms = [t for t in re.findall(r"[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]{4,}", question.lower()) if t not in {"cuanta", "cuanto", "tiene", "sobre", "para"}]
        hits: List[Evidence] = []
        for root, _, files in os.walk(corpus_dir):
            for name in files:
                if not name.lower().endswith((".txt", ".md", ".json")):
                    continue
                path = os.path.join(root, name)
                try:
                    text = open(path, "r", encoding="utf-8", errors="ignore").read()[:50000]
                except Exception:
                    continue
                lower = text.lower()
                score = sum(1 for term in terms if term in lower)
                if score > 0:
                    snippet = self._snippet(text, terms)
                    hits.append(Evidence(source=f"rag_local:{name}", value=self._extract_number(snippet), text=snippet, confidence_hint=min(80, 45 + score * 10)))
        hits.sort(key=lambda e: e.confidence_hint, reverse=True)
        return hits[:3]

    def official_source(self, question: str) -> List[Evidence]:
        if self._offline_fixtures_enabled():
            return self._fixture_population(question, "fuente_oficial", 129_000_000, 95)
        country = self._extract_country_name(question)
        if not country or requests is None:
            return []
        code = self._country_to_iso2(country)
        if not code:
            return []
        return self._world_bank_population(code, source="worldbank_official", confidence=95)


    def gdp_official(self, question: str) -> List[Evidence]:
        """Recupera PIB nominal reciente.

        Implementación real: World Bank NY.GDP.MKTP.CD.
        Fixture offline: permite tests sin internet.
        """
        if self._offline_fixtures_enabled():
            country = self._extract_country_name(question)
            if not country:
                return []
            value = self._fixture_gdp_value(country)
            return [Evidence(source="worldbank_gdp_fixture", value=value, text=f"Fixture offline: PIB nominal estimado recuperado: {int(value):,} USD.", confidence_hint=92)]
        country = self._extract_country_name(question)
        if not country or requests is None:
            return []
        code = self._country_to_iso2(country)
        if not code:
            return []
        return self._world_bank_indicator(code, indicator="NY.GDP.MKTP.CD", source="worldbank_gdp_official", confidence=94, label="PIB nominal")

    def secondary_source(self, question: str) -> List[Evidence]:
        if self._offline_fixtures_enabled():
            return self._fixture_population(question, "fuente_secundaria", 128_500_000, 82)
        # Wikidata SPARQL requiere internet. Se deja como herramienta real opcional.
        country = self._extract_country_name(question)
        if not country or requests is None:
            return []
        try:
            url = "https://www.wikidata.org/w/api.php"
            params = {"action": "wbsearchentities", "search": country, "language": "es", "format": "json", "limit": 1}
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if data.get("search"):
                label = data["search"][0].get("label", country)
                return [Evidence(source="wikidata_lookup", value=None, text=f"Wikidata encontró entidad candidata para {label}. Requiere consulta detallada para valor numérico.", confidence_hint=72)]
        except Exception:
            return []
        return []

    def general_source(self, question: str) -> List[Evidence]:
        if self._offline_fixtures_enabled():
            return self._fixture_population(question, "fuente_general", 130_000_000, 70)
        country = self._extract_country_name(question)
        if not country or requests is None:
            return []
        try:
            url = f"https://restcountries.com/v3.1/name/{country}"
            r = requests.get(url, params={"fields": "name,population"}, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if data:
                item = data[0]
                pop = float(item.get("population", 0))
                name = item.get("name", {}).get("common", country)
                return [Evidence(source="restcountries_general", value=pop, text=f"RestCountries reporta población aproximada para {name}: {int(pop):,}.", confidence_hint=70)]
        except Exception:
            return []
        return []


    def _world_bank_indicator(self, iso2: str, indicator: str, source: str, confidence: int, label: str) -> List[Evidence]:
        try:
            url = f"https://api.worldbank.org/v2/country/{iso2}/indicator/{indicator}"
            params = {"format": "json", "per_page": 8, "MRV": 8}
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            payload = r.json()
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            for row in rows:
                if row.get("value") is not None:
                    value = float(row["value"])
                    date = row.get("date", "año reciente")
                    country = row.get("country", {}).get("value", iso2)
                    return [Evidence(source=source, value=value, text=f"World Bank reporta {label} de {country} en {date}: {value:,.0f}.", confidence_hint=confidence)]
        except Exception:
            return []
        return []

    def _world_bank_population(self, iso2: str, source: str, confidence: int) -> List[Evidence]:
        return self._world_bank_indicator(iso2, indicator="SP.POP.TOTL", source=source, confidence=confidence, label="población")

    def _country_to_iso2(self, country: str) -> Optional[str]:
        # Primero API real; luego alias mínimos para seguir funcionando si el resolvedor falla.
        aliases = {"mexico": "MX", "méxico": "MX", "francia": "FR", "france": "FR", "colombia": "CO", "estados unidos": "US", "usa": "US", "united states": "US"}
        key = country.lower().strip()
        if key in aliases:
            return aliases[key]
        if requests is None:
            return None
        try:
            url = f"https://restcountries.com/v3.1/name/{country}"
            r = requests.get(url, params={"fields": "cca2,name"}, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if data:
                return data[0].get("cca2")
        except Exception:
            return None
        return None

    def _extract_country_name(self, question: str) -> Optional[str]:
        q = question.strip()
        patterns = [
            r"(?:en|de|del país|pais)\s+([A-ZÁÉÍÓÚÑÜa-záéíóúñü ]+?)(?:\?|$|\.|,)",
            r"(?:vive en|viven en|habitantes tiene)\s+([A-ZÁÉÍÓÚÑÜa-záéíóúñü ]+?)(?:\?|$|\.|,)",
        ]
        for pat in patterns:
            m = re.search(pat, q, flags=re.IGNORECASE)
            if m:
                candidate = m.group(1).strip()
                candidate = re.sub(r"\bactual(?:mente)?\b", "", candidate, flags=re.I).strip()
                if candidate:
                    return candidate
        # Último recurso: nombres conocidos sin amarrar la herramienta a un solo país.
        for name in ["México", "Mexico", "Francia", "France", "Colombia", "Estados Unidos", "USA"]:
            if name.lower() in q.lower():
                return name
        return None

    def _fixture_population(self, question: str, source: str, value: float, confidence: int) -> List[Evidence]:
        if self._extract_country_name(question):
            return [Evidence(source=source, value=value, text=f"Fixture offline: población estimada recuperada: {int(value):,}.", confidence_hint=confidence)]
        return []


    def _fixture_gdp_value(self, country: str) -> float:
        key = country.lower().strip()
        if "mex" in key or "méx" in key:
            return 1_790_000_000_000.0
        if "fran" in key or "france" in key:
            return 3_030_000_000_000.0
        if "colom" in key:
            return 363_000_000_000.0
        return 1_000_000_000_000.0

    def _offline_fixtures_enabled(self) -> bool:
        return os.getenv("HABLA_USE_OFFLINE_FIXTURES", "0") == "1"

    def _extract_math_expression(self, question: str) -> str:
        match = re.search(r"([0-9][0-9+\-*/().\s]+[0-9])", question)
        return match.group(1) if match else ""

    def _safe_eval(self, expr: str):
        allowed_nodes = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd, ast.Mod, ast.FloorDiv, ast.Load)
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError("expresión no permitida")
        return eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}, "math": math}, {})

    def _extract_number(self, text: str) -> Optional[float]:
        m = re.search(r"([0-9][0-9,\. ]{2,})", text)
        if not m:
            return None
        raw = m.group(1).replace(",", "").replace(" ", "")
        try:
            return float(raw)
        except ValueError:
            return None

    def _snippet(self, text: str, terms: List[str]) -> str:
        lower = text.lower()
        positions = [lower.find(t) for t in terms if lower.find(t) >= 0]
        start = max(0, min(positions) - 160) if positions else 0
        return text[start:start + 600].replace("\n", " ").strip()
