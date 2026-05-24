import ast
import math
import os
import re
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
    """Registro de herramientas reales e inyectables."""

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
        function = self.tools.get(tool_name)
        if function is None:
            state.log(f"TOOL_ERROR => herramienta no registrada: {tool_name}")
            return []
        try:
            return function(state)
        except Exception as error:
            state.log(f"TOOL_ERROR => {tool_name}: {error}")
            return []

    def calculator(self, question: str) -> List[Evidence]:
        expression = self._extract_math_expression(question)
        if not expression:
            return []
        try:
            value = self._safe_eval(expression)
            return [Evidence(source="calculadora", value=float(value), text=f"Resultado calculado: {value}", confidence_hint=99)]
        except Exception:
            return []

    def rag_local(self, question: str) -> List[Evidence]:
        corpus_dir = os.getenv("HABLA_RAG_CORPUS", "docs/rag_corpus")
        if not os.path.isdir(corpus_dir):
            return []
        terms = [
            term
            for term in re.findall(r"[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]{4,}", question.lower())
            if term not in {"cuanta", "cuanto", "tiene", "sobre", "para"}
        ]
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
        hits.sort(key=lambda evidence: evidence.confidence_hint, reverse=True)
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
        country = self._extract_country_name(question)
        if not country or requests is None:
            return []
        try:
            url = "https://www.wikidata.org/w/api.php"
            params = {"action": "wbsearchentities", "search": country, "language": "es", "format": "json", "limit": 1}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
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
            response = requests.get(url, params={"fields": "name,population"}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if data:
                item = data[0]
                population = float(item.get("population", 0))
                name = item.get("name", {}).get("common", country)
                return [Evidence(source="restcountries_general", value=population, text=f"RestCountries reporta población aproximada para {name}: {int(population):,}.", confidence_hint=70)]
        except Exception:
            return []
        return []

    def _world_bank_indicator(self, iso2: str, indicator: str, source: str, confidence: int, label: str) -> List[Evidence]:
        try:
            url = f"https://api.worldbank.org/v2/country/{iso2}/indicator/{indicator}"
            params = {"format": "json", "per_page": 8, "MRV": 8}
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
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
        aliases = {
            "mexico": "MX",
            "méxico": "MX",
            "francia": "FR",
            "france": "FR",
            "colombia": "CO",
            "estados unidos": "US",
            "usa": "US",
            "united states": "US",
        }
        key = country.lower().strip()
        if key in aliases:
            return aliases[key]
        if requests is None:
            return None
        try:
            url = f"https://restcountries.com/v3.1/name/{country}"
            response = requests.get(url, params={"fields": "cca2,name"}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if data:
                return data[0].get("cca2")
        except Exception:
            return None
        return None

    def _extract_country_name(self, question: str) -> Optional[str]:
        raw_question = question.strip()
        patterns = [
            r"(?:en|de|del país|pais)\s+([A-ZÁÉÍÓÚÑÜa-záéíóúñü ]+?)(?:\?|$|\.|,)",
            r"(?:vive en|viven en|habitantes tiene)\s+([A-ZÁÉÍÓÚÑÜa-záéíóúñü ]+?)(?:\?|$|\.|,)",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_question, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(r"\bactual(?:mente)?\b", "", candidate, flags=re.I).strip()
                if candidate:
                    return candidate
        for name in ["México", "Mexico", "Francia", "France", "Colombia", "Estados Unidos", "USA"]:
            if name.lower() in raw_question.lower():
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
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Num,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Pow,
            ast.USub,
            ast.UAdd,
            ast.Mod,
            ast.FloorDiv,
            ast.Load,
        )
        tree = ast.parse(expr, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError("expresión no permitida")
        return eval(compile(tree, "<calculator>", "eval"), {"__builtins__": {}, "math": math}, {})

    def _extract_number(self, text: str) -> Optional[float]:
        match = re.search(r"([0-9][0-9,\. ]{2,})", text)
        if not match:
            return None
        normalized = match.group(1).replace(" ", "").replace(",", "")
        try:
            return float(normalized)
        except ValueError:
            return None

    def _snippet(self, text: str, terms: List[str], radius: int = 90) -> str:
        lower = text.lower()
        for term in terms:
            index = lower.find(term)
            if index >= 0:
                start = max(0, index - radius)
                end = min(len(text), index + radius)
                return text[start:end].replace("\n", " ").strip()
        return text[: min(len(text), radius * 2)].replace("\n", " ").strip()
