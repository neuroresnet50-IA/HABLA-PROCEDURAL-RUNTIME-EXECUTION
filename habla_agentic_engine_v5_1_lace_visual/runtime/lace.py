from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import List, Optional


REQUIRED_LAYERS = [
    "CAPA 1 — INTERPRETACIÓN",
    "CAPA 2 — CLASIFICACIÓN SEMÁNTICA",
    "CAPA 3 — PLANIFICACIÓN DEL RAZONAMIENTO",
    "CAPA 4 — REACT",
    "CAPA 5 — RECUPERACIÓN Y EVIDENCIA",
    "CAPA 6 — TRIANGULACIÓN",
    "CAPA 7 — CONFIANZA POR COMPONENTE",
    "CAPA 8 — AUTO-CRÍTICA",
    "CAPA 9 — MEMORIA EPISÓDICA",
    "CAPA 10 — RESPUESTA",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class LaceStep:
    """Paso lógico del diagrama LACE.

    Este modelo permite que el runtime explique en terminal o en UI qué etapa
    toca ejecutar, sin depender solo de texto libre.
    """

    index: int
    name: str
    description: str
    required_artifact: str


@dataclass(frozen=True)
class LaceVisualModel:
    """Representación auditable del diagrama LACE."""

    phases: List[LaceStep]

    @classmethod
    def default(cls, required_cycles: int = 10) -> "LaceVisualModel":
        return cls(
            phases=[
                LaceStep(0, "Arranque dirigido por LACE.md", "Leer LACE.md antes de cualquier acción.", "LACE.md"),
                LaceStep(1, "Construcción base", "Crear versión mínima funcional y documentar estado inicial.", "[BASE] en LACE_LOG.md"),
                LaceStep(2, f"Ciclos LACE 1..{required_cycles}", "Ejecutar analizar, criticar, mejorar y validar.", "[CICLO-N COMPLETADO]"),
                LaceStep(3, "Puerta de calidad", "Bloquear cierre si faltan ciclos o criterios.", "closure_status"),
                LaceStep(4, "Entrega", "Entregar proyecto, log y resumen ejecutivo.", "proyecto + LACE_LOG.md"),
            ]
        )

    def as_markdown(self) -> str:
        lines = ["# LACE Visual Model", ""]
        for phase in self.phases:
            lines.append(f"{phase.index}. **{phase.name}**")
            lines.append(f"   - {phase.description}")
            lines.append(f"   - Artefacto: `{phase.required_artifact}`")
        return "\n".join(lines)


@dataclass
class LacePolicy:
    """Política LACE cargada antes de activar LLM, Codex u otro agente."""

    path: Path
    text: str
    required_cycles: int = 10
    loaded_at: str = field(default_factory=_utc_now)

    @classmethod
    def load(cls, path: str | Path = "LACE.md") -> "LacePolicy":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"No existe LACE.md en: {p.resolve()}")
        text = p.read_text(encoding="utf-8")
        missing = [layer for layer in REQUIRED_LAYERS if layer not in text]
        if missing:
            raise ValueError("LACE.md no contiene todas las capas requeridas: " + ", ".join(missing))
        return cls(path=p, text=text, required_cycles=_detect_required_cycles(text))

    def compact_directive(self) -> str:
        return f"""
LACE v2.0 ESTA ACTIVO Y FUE LEIDO ANTES DE ARRANCAR EL AGENTE.
REGLA ABSOLUTA: no declares proyecto terminado hasta completar {self.required_cycles} ciclos documentados en LACE_LOG.md.
Cada ciclo debe usar HABLA por capas: interpretación, clasificación, planificación, ReAct, evidencia, triangulación, confianza, autocrítica, memoria y acción final.
Antes de modificar código, escribe THOUGHT/ACTION/OBSERVATION en LACE_LOG.md.
Antes de cerrar, verifica la puerta de cierre LACE.
""".strip()

    def visual_model(self) -> LaceVisualModel:
        return LaceVisualModel.default(self.required_cycles)


def _detect_required_cycles(text: str) -> int:
    """Detecta ciclos obligatorios desde LACE.md.

    Prioriza números explícitos cercanos a la palabra ciclos. Si no existe,
    conserva 10 porque LACE v2.0 define 10 ciclos como regla absoluta.
    """

    patterns = [
        r"completado\s+(\d+)\s+ciclos",
        r"completar\s+(\d+)\s+ciclos",
        r"mínimo\s+de\s+(\d+)\s+ciclos",
        r"mínimo\s+(\d+)\s+ciclos",
        r"(\d+)\s+ciclos\s+obligatorios",
        r"CICLOS\s+1\s+AL\s+(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return max(1, int(m.group(1)))
    return 10


@dataclass
class LaceCycle:
    number: int
    analyzed: bool = False
    critiqued: bool = False
    improved: bool = False
    validated: bool = False
    improved_objectively: bool = False

    @property
    def complete(self) -> bool:
        return self.analyzed and self.critiqued and self.improved and self.validated and self.improved_objectively


class LaceLog:
    """Manejo de LACE_LOG.md."""

    def __init__(self, path: str | Path = "LACE_LOG.md"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.path.exists()

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.exists() else ""

    def append(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n\n")

    def initialize(self, project_prompt: str, policy: LacePolicy) -> None:
        if self.exists() and self.read().strip():
            return
        self.append(
            f"""# LACE_LOG.md

[INIT]
Fecha UTC: {_utc_now()}
LACE leído desde: {policy.path}
Regla activa: {policy.required_cycles} ciclos obligatorios antes de cierre.

[COMPRENSIÓN DEL PROYECTO]
{project_prompt.strip()}

[PLAN PARA {policy.required_cycles} CICLOS]
1. Corrección de errores y arranque.
2. Organización de código.
3. Manejo de errores.
4. Seguridad básica y validaciones.
5. Experiencia de usuario.
6. Rendimiento.
7. Documentación.
8. Funcionalidad extra de valor real.
9. Integración con herramientas/LLM.
10. Revisión integral final HABLA+LACE.
"""
        )

    def log_base(self, description: str) -> None:
        self.append(
            f"""[BASE] Construcción inicial completada.
Estado actual: {description}
"""
        )

    def log_cycle_template(self, cycle_number: int, focus: str) -> None:
        self.append(
            f"""[CICLO-{cycle_number} PROBLEMAS]
THOUGHT: analizaré el estado actual enfocado en {focus}.
TRIANGULACIÓN: técnico / funcional / humano.
CONFIANZA: lógica, UI, rendimiento, errores, seguridad.
AUTO-CRÍTICA: buscaré cierre prematuro, parches débiles u omisiones.

Problemas priorizados:
1. Pendiente de análisis real — severidad: media

[CICLO-{cycle_number} MEJORA]
THOUGHT: aplicar mejora concreta sobre {focus}.
ACTION: implementar cambio verificable.
OBSERVATION esperada: el proyecto debe mejorar objetivamente en {focus}.

[CICLO-{cycle_number} COMPLETADO]
OBSERVATION real: pendiente de ejecución.
¿Coincide con OBSERVATION esperada? PENDIENTE
Problemas resueltos: pendiente
Estado ahora vs antes: pendiente
¿El proyecto mejoró objetivamente? PENDIENTE

MEMORIA EPISÓDICA:
- Qué funcionó: pendiente
- Qué no funcionó: pendiente
- Qué evitar en el próximo ciclo: pendiente

Próximo ciclo — qué atacaré: se definirá tras validación.
"""
        )

    def log_cycle_completion(self, cycle_number: int, observation: str, resolved: str, next_focus: str) -> None:
        self.append(
            f"""[CICLO-{cycle_number} COMPLETADO]
OBSERVATION real: {observation}
¿Coincide con OBSERVATION esperada? SI
Problemas resueltos: {resolved}
Estado ahora vs antes: mejora validada en ciclo {cycle_number}.
¿El proyecto mejoró objetivamente? SI

MEMORIA EPISÓDICA:
- Qué funcionó: mejora incremental documentada.
- Qué no funcionó: pendiente de evaluar en siguientes ciclos.
- Qué evitar en el próximo ciclo: cerrar sin evidencia.

Próximo ciclo — qué atacaré: {next_focus}
"""
        )

    def count_completed_cycles(self) -> int:
        text = self.read()
        return text.count("¿El proyecto mejoró objetivamente? SI")

    def next_cycle_number(self) -> int:
        return self.count_completed_cycles() + 1


class LaceGate:
    """Puerta de cierre LACE."""

    def __init__(self, log: LaceLog, required_cycles: int = 10):
        self.log = log
        self.required_cycles = required_cycles

    def can_close(self) -> tuple[bool, str]:
        completed = self.log.count_completed_cycles()
        if completed < self.required_cycles:
            return False, f"Cierre bloqueado por LACE: {completed}/{self.required_cycles} ciclos con mejora objetiva."
        return True, "Puerta LACE superada."


@dataclass(frozen=True)
class LaceRunState:
    completed_cycles: int
    required_cycles: int
    can_close: bool
    status: str
    next_action: str


class LaceRuntime:
    """Orquestador de alto nivel HABLA+LACE."""

    AREAS = [
        "bugs críticos",
        "limpieza y organización",
        "interfaz de usuario",
        "documentación",
        "rendimiento",
        "errores y casos extremos",
        "seguridad básica",
        "funcionalidad adicional de valor real",
        "experiencia de usuario punta a punta",
        "revisión integral final",
    ]

    def __init__(self, policy_path: str | Path = "LACE.md", log_path: str | Path = "LACE_LOG.md"):
        self.policy = LacePolicy.load(policy_path)
        self.log = LaceLog(log_path)
        self.gate = LaceGate(self.log, self.policy.required_cycles)

    def preflight(self, project_prompt: str) -> str:
        self.log.initialize(project_prompt, self.policy)
        return self.policy.compact_directive()

    def scaffold_cycles(self) -> None:
        current = self.log.read()
        if "[CICLO-1 PROBLEMAS]" in current:
            return
        for idx in range(1, self.policy.required_cycles + 1):
            area = self.AREAS[(idx - 1) % len(self.AREAS)]
            self.log.log_cycle_template(idx, area)

    def record_cycle_completion(self, observation: str, resolved: str, next_focus: str = "siguiente prioridad LACE") -> int:
        cycle = self.log.next_cycle_number()
        if cycle > self.policy.required_cycles:
            cycle = self.policy.required_cycles
        self.log.log_cycle_completion(cycle, observation, resolved, next_focus)
        return cycle

    def closure_status(self) -> tuple[bool, str]:
        return self.gate.can_close()

    def next_required_action(self) -> str:
        completed = self.log.count_completed_cycles()
        if not self.log.exists() or not self.log.read().strip():
            return "PASO 0: ejecutar preflight y crear LACE_LOG.md."
        if completed == 0 and "[BASE]" not in self.log.read():
            return "PASO 1: construir versión base y registrar [BASE]."
        if completed < self.policy.required_cycles:
            return f"CICLO {completed + 1}: analizar → criticar → mejorar → validar."
        return "PUERTA DE CALIDAD: ejecutar evaluación final HABLA+LACE."

    def run_state(self) -> LaceRunState:
        can_close, status = self.closure_status()
        return LaceRunState(
            completed_cycles=self.log.count_completed_cycles(),
            required_cycles=self.policy.required_cycles,
            can_close=can_close,
            status=status,
            next_action=self.next_required_action(),
        )

    def visual_markdown(self) -> str:
        state = self.run_state()
        return self.policy.visual_model().as_markdown() + (
            f"\n\n## Estado actual\n\n"
            f"- Ciclos: {state.completed_cycles}/{state.required_cycles}\n"
            f"- Cierre permitido: {state.can_close}\n"
            f"- Estado: {state.status}\n"
            f"- Próxima acción: {state.next_action}\n"
        )
