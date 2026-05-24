from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Evidence:
    source: str
    value: Optional[float]
    text: str
    confidence_hint: int = 0


@dataclass
class Confidence:
    dato: int = 0
    fecha: int = 0
    fuente: int = 0
    calculo: int = 0
    inferencia: int = 0

    @property
    def global_score(self) -> float:
        values = [self.dato, self.fecha, self.fuente, self.calculo, self.inferencia]
        active = [value for value in values if value > 0]
        return sum(active) / len(active) if active else 0.0


@dataclass
class SubTask:
    task_id: str
    description: str
    tool_name: str
    query: str
    status: str = "pending"
    result_value: Optional[float] = None
    result_text: str = ""
    confidence: int = 0


@dataclass
class HablaState:
    question: str
    protocol_text: str = ""
    knowledge_type: str = ""
    tool_required: str = ""
    strategy: str = ""
    attempt: int = 0
    max_attempts: int = 4
    observations: List[Evidence] = field(default_factory=list)
    triangulated_text: str = ""
    confidence: Confidence = field(default_factory=Confidence)
    safe_to_answer: bool = False
    blocked: bool = False
    block_reason: str = ""
    answer: str = ""
    llm_directive: str = ""
    is_compound: bool = False
    compound_goal: str = ""
    sub_tasks: List[SubTask] = field(default_factory=list)
    debug: List[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.debug.append(message)
