from typing import Dict, Callable, List, Optional
from .types import HablaState, Evidence
from .classifier import SemanticClassifier
from .tools import ToolRegistry
from .triangulation import Triangulator
from .confidence import ConfidenceScorer
from .constitutional import ConstitutionalChecker
from .memory import EpisodicMemory
from .planner import CompoundPlanner
from .prompt_converter import convert_to_habla
from .lace import LacePolicy, LaceLog
from pathlib import Path

class HablaEngineV5:
    """Motor HABLA V5.0 con LACE embebido.

    Base V4.2 + LACE:
    - Clasificador semántico LLM-first, reglas como fallback.
    - ToolRegistry con herramientas reales e inyectables.
    - Memoria episódica que reordena herramientas según experiencias previas.
    """

    def __init__(self, llm=None, memory_path: str = "memory/episodic_memory.jsonl", tools: Optional[Dict[str, Callable[[HablaState], List[Evidence]]]] = None, lace_path: str = "LACE.md", lace_log_path: str = "LACE_LOG.md", lace_enabled: bool = True):
        self.llm = llm
        self.lace_enabled = lace_enabled
        self.lace_policy = None
        self.lace_log = None
        if lace_enabled:
            try:
                self.lace_policy = LacePolicy.load(lace_path)
                self.lace_log = LaceLog(lace_log_path)
            except FileNotFoundError:
                # Permite usar el motor como librería atómica si no hay LACE.md en cwd.
                self.lace_enabled = False
        self.classifier = SemanticClassifier(llm=llm)
        self.tools = ToolRegistry(extra_tools=tools)
        self.triangulator = Triangulator()
        self.scorer = ConfidenceScorer()
        self.checker = ConstitutionalChecker()
        self.memory = EpisodicMemory(memory_path)
        self.planner = CompoundPlanner()

    def run(self, question: str) -> HablaState:
        state = HablaState(question=question)
        state = self._apply_lace_preflight(state)
        state.protocol_text = convert_to_habla(question)
        state = self.classifier.classify(state)
        state = self.planner.plan(state)

        if state.is_compound:
            state = self._run_compound_plan(state)
            state.llm_directive = self._build_llm_directive(state)
            state.answer = self._answer_with_llm_or_template(state)
            self.memory.save(state)
            return state

        if state.blocked:
            state = self.checker.run(state)
            state.llm_directive = self._build_llm_directive(state)
            state.answer = self._answer_with_llm_or_template(state)
            self.memory.save(state)
            return state

        tool_order = self._tool_order_for_state(state)
        state.log(f"MEMORY_TOOL_ORDER => {tool_order}")

        for attempt in range(1, state.max_attempts + 1):
            state.attempt = attempt
            tool_name = tool_order[min(attempt - 1, len(tool_order) - 1)] if tool_order else self._select_tool(state, attempt)
            state.log(f"THOUGHT => intento={attempt}, tool={tool_name}")
            evidence = self.tools.run(state, tool_name)
            if not evidence:
                state.log(f"OBSERVATION => vacío con {tool_name}")
                continue
            state.observations.extend(evidence)
            state.log(f"OBSERVATION => {len(evidence)} evidencia(s) desde {tool_name}")

            # Para HECHO_TEMPORAL buscamos al menos 2 fuentes si el orden aún ofrece alternativas.
            if state.knowledge_type == "HECHO_TEMPORAL" and len(state.observations) < 2 and attempt < min(state.max_attempts, len(tool_order)):
                state.log("LOOP => evidencia única, intentando segunda fuente para triangulación")
                continue
            break
        else:
            state.blocked = True
            state.block_reason = "No se obtuvo evidencia suficiente después de los intentos."

        state = self.triangulator.run(state)
        state = self.scorer.run(state)
        state = self.checker.run(state)
        state.llm_directive = self._build_llm_directive(state)
        state.answer = self._answer_with_llm_or_template(state)
        self.memory.save(state)
        return state

    def _apply_lace_preflight(self, state: HablaState) -> HablaState:
        """Lee LACE.md antes de cualquier LLM/agente y prepara LACE_LOG.md.

        Esto cumple la regla del documento: LACE debe leerse completo antes
        de arrancar el proceso. Aquí no se falsifican ciclos; solo se
        inicializa el control y se inyecta la directiva al LLM/Codex.
        """
        if not self.lace_enabled or self.lace_policy is None:
            state.log("LACE => desactivado o LACE.md no encontrado")
            return state
        state.lace_policy_loaded = True
        state.lace_directive = self.lace_policy.compact_directive()
        if self.lace_log is not None:
            self.lace_log.initialize(state.question, self.lace_policy)
            state.lace_log_path = str(self.lace_log.path)
        state.log(f"LACE => política cargada desde {self.lace_policy.path}")
        return state


    def _run_compound_plan(self, state: HablaState) -> HablaState:
        """Ejecuta un plan compuesto coordinando subtareas.

        Caso inicial soportado: PIB per cápita = PIB nominal / población.
        La idea es que este método sea el orquestador superior; el motor V4
        atómico sigue existiendo para preguntas simples.
        """
        state.log("COMPOUND => ejecutando subtareas coordinadas")
        values = {}
        for task in state.sub_tasks:
            if task.tool_name == "calculator_internal":
                gdp = values.get("gdp")
                population = values.get("population")
                if gdp is None or population in (None, 0):
                    task.status = "failed"
                    task.result_text = "No se puede calcular: falta PIB o población."
                    task.confidence = 0
                    state.blocked = True
                    state.block_reason = "Faltan subtareas requeridas para cálculo compuesto."
                    state.log("COMPOUND_FAIL => faltan valores para calculadora interna")
                    continue
                result = gdp / population
                task.status = "ok"
                task.result_value = result
                task.result_text = f"PIB per cápita calculado: {result:,.2f} USD por persona."
                task.confidence = min(
                    [t.confidence for t in state.sub_tasks if t.task_id in {"gdp", "population"}] or [85]
                )
                values[task.task_id] = result
                state.observations.append(Evidence(source="calculator_internal", value=result, text=task.result_text, confidence_hint=task.confidence))
                continue

            evidence = self.tools.run(HablaState(question=task.query), task.tool_name)
            if not evidence:
                task.status = "failed"
                task.result_text = f"No se obtuvo evidencia para {task.task_id}."
                task.confidence = 0
                state.log(f"COMPOUND_FAIL => {task.task_id} sin evidencia")
                continue
            best = max(evidence, key=lambda e: e.confidence_hint)
            task.status = "ok"
            task.result_value = best.value
            task.result_text = best.text
            task.confidence = best.confidence_hint
            if best.value is not None:
                values[task.task_id] = best.value
            state.observations.append(best)
            state.log(f"COMPOUND_OK => {task.task_id}={best.value} via {best.source}")

        failed = [t for t in state.sub_tasks if t.status != "ok"]
        if failed:
            state.blocked = True
            state.block_reason = "Una o más subtareas compuestas fallaron: " + ", ".join(t.task_id for t in failed)
            state.safe_to_answer = False
            state.confidence.dato = 0
            return state

        calc = next((t for t in state.sub_tasks if t.task_id == "calculate_gdp_per_capita"), None)
        if calc and calc.result_value is not None:
            state.triangulated_text = (
                f"PIB per cápita estimado: {calc.result_value:,.2f} USD por persona, "
                "calculado como PIB nominal reciente dividido entre población reciente."
            )
            state.confidence.dato = min(t.confidence for t in state.sub_tasks if t.task_id in {"gdp", "population"})
            state.confidence.fecha = 85
            state.confidence.fuente = min(t.confidence for t in state.sub_tasks if t.task_id in {"gdp", "population"})
            state.confidence.calculo = 99
            state.confidence.inferencia = 0
            state.safe_to_answer = True
            state.blocked = False
            state.log("COMPOUND_DONE => respuesta compuesta lista")
        return state

    def _tool_order_for_state(self, state: HablaState) -> List[str]:
        if state.knowledge_type == "CALCULO":
            base = ["calculator"]
        elif state.knowledge_type == "HECHO_TEMPORAL":
            base = ["rag_local", "official_source", "secondary_source", "general_source"]
        elif state.knowledge_type in {"HECHO_ESTABLE", "INFERENCIA_OPINION"}:
            base = ["memory_optional", "rag_local"]
        else:
            base = ["memory_optional"]
        return self.memory.recommend_tool_order(base, state.knowledge_type)

    def _select_tool(self, state: HablaState, attempt: int) -> str:
        if state.knowledge_type == "CALCULO":
            return "calculator"
        if state.knowledge_type == "HECHO_TEMPORAL":
            return ["rag_local", "official_source", "secondary_source", "general_source"][min(attempt - 1, 3)]
        if state.knowledge_type in {"HECHO_ESTABLE", "INFERENCIA_OPINION"}:
            return "memory_optional"
        return "memory_optional"

    def _build_llm_directive(self, state: HablaState) -> str:
        evidence_lines = "\n".join([f"- {e.source}: {e.text} (valor={e.value})" for e in state.observations]) or "- Sin evidencia externa útil."
        lace_block = (state.lace_directive + "\n\n") if state.lace_directive else ""
        return f"""
{lace_block}PROTOCOLO DE RESPUESTA CONTROLADA POR HABLA V5.0 + LACE

PREGUNTA HUMANA:
{state.question}

TIPO DE CONOCIMIENTO:
{state.knowledge_type}

EVIDENCIA:
{evidence_lines}

SUBTAREAS COMPUESTAS:
{self._format_subtasks(state)}

TRIANGULACION:
{state.triangulated_text}

CONFIANZA POR COMPONENTE:
- dato: {state.confidence.dato}
- fecha: {state.confidence.fecha}
- fuente: {state.confidence.fuente}
- calculo: {state.confidence.calculo}
- inferencia: {state.confidence.inferencia}
- global: {state.confidence.global_score:.1f}

REGLAS OBLIGATORIAS:
1. No inventes datos.
2. No ocultes incertidumbre.
3. Separa hecho, cálculo e inferencia.
4. Si es estimación, dilo explícitamente.
5. Si la evidencia es insuficiente, declara el límite.

ESTADO CONSTITUCIONAL:
- safe_to_answer: {state.safe_to_answer}
- blocked: {state.blocked}
- block_reason: {state.block_reason}

INSTRUCCION:
Responde al usuario en español, como chat natural, pero respetando todas las reglas anteriores.
""".strip()


    def _format_subtasks(self, state: HablaState) -> str:
        if not state.sub_tasks:
            return "- No aplica."
        return "\n".join(
            f"- {t.task_id}: {t.status}; tool={t.tool_name}; value={t.result_value}; confidence={t.confidence}; {t.result_text}"
            for t in state.sub_tasks
        )

    def _answer_with_llm_or_template(self, state: HablaState) -> str:
        if state.blocked or not state.safe_to_answer:
            return f"No puedo responder con seguridad suficiente. Causa: {state.block_reason or 'evidencia insuficiente.'}"
        if self.llm is not None:
            out = self.llm.generate(state.llm_directive)
            if out and not out.startswith("[ERROR"):
                return out
        return self._template_answer(state)

    def _template_answer(self, state: HablaState) -> str:
        if state.is_compound:
            return (
                f"{state.triangulated_text} "
                f"Confianza del dato: {state.confidence.dato}/100; "
                f"fuente: {state.confidence.fuente}/100; cálculo: {state.confidence.calculo}/100. "
                "Límite: el resultado depende de que PIB y población correspondan a periodos compatibles."
            )
        if state.knowledge_type == "HECHO_TEMPORAL":
            return (
                f"Según la evidencia recuperada, {state.triangulated_text} "
                f"Confianza del dato: {state.confidence.dato}/100; fuente: {state.confidence.fuente}/100. "
                "Límite: esto debe tratarse como una estimación, no como un conteo exacto absoluto."
            )
        if state.knowledge_type == "CALCULO":
            return state.observations[0].text if state.observations else "No pude calcular el resultado."
        return "Respuesta generada bajo control HABLA: separaré hecho, inferencia y límites de conocimiento."


# Compatibilidad hacia atrás
HablaEngineV4 = HablaEngineV5
