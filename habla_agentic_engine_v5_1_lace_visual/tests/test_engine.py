import os
from runtime.engine import HablaEngineV4
from connectors.echo_connector import EchoConnector


def test_temporal_question_classifies_and_answers(tmp_path, monkeypatch):
    monkeypatch.setenv("HABLA_USE_OFFLINE_FIXTURES", "1")
    engine = HablaEngineV4(llm=None, memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("Cuanta gente vive en Mexico")
    assert state.knowledge_type == "HECHO_TEMPORAL"
    assert state.safe_to_answer is True
    assert state.confidence.dato >= 70


def test_semantic_population_without_actual_keyword(tmp_path, monkeypatch):
    monkeypatch.setenv("HABLA_USE_OFFLINE_FIXTURES", "1")
    engine = HablaEngineV4(llm=None, memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("Cuántos habitantes tiene Francia?")
    assert state.knowledge_type == "HECHO_TEMPORAL"


def test_calculator(tmp_path):
    engine = HablaEngineV4(llm=None, memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("calcula 2+2")
    assert state.knowledge_type == "CALCULO"
    assert "4" in state.answer


def test_memory_reorders_tools_after_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("HABLA_USE_OFFLINE_FIXTURES", "1")
    mem = tmp_path / "mem.jsonl"
    # Primer run: rag_local falla y luego official/secondary responden.
    engine1 = HablaEngineV4(llm=None, memory_path=str(mem))
    s1 = engine1.run("Cuanta gente vive en Mexico")
    assert any("tool=rag_local" in d for d in s1.debug)

    # Segundo run: la memoria debe aprender y poner herramientas exitosas antes que rag_local.
    engine2 = HablaEngineV4(llm=None, memory_path=str(mem))
    s2 = engine2.run("Cuanta gente vive en Mexico")
    order_lines = [d for d in s2.debug if d.startswith("MEMORY_TOOL_ORDER")]
    assert order_lines
    assert "official_source" in order_lines[0]


def test_echo_connector(tmp_path, monkeypatch):
    monkeypatch.setenv("HABLA_USE_OFFLINE_FIXTURES", "1")
    engine = HablaEngineV4(llm=EchoConnector(), memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("Cuanta gente vive en Mexico")
    assert "ECHO" in state.answer


def test_global_score_ignores_inactive_components():
    from runtime.types import Confidence
    c = Confidence(dato=90, fecha=85, fuente=88, calculo=0, inferencia=0)
    assert round(c.global_score, 1) == 87.7


def test_compound_gdp_per_capita_orchestrates_subtasks(tmp_path, monkeypatch):
    monkeypatch.setenv("HABLA_USE_OFFLINE_FIXTURES", "1")
    engine = HablaEngineV4(llm=None, memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("Cuál es el PIB per cápita de México?")
    assert state.is_compound is True
    assert state.safe_to_answer is True
    assert len(state.sub_tasks) == 3
    assert all(t.status == "ok" for t in state.sub_tasks)
    assert "PIB per cápita" in state.answer
    assert state.confidence.global_score > 85


def test_lace_policy_loads_and_injects_directive(tmp_path, monkeypatch):
    monkeypatch.setenv("HABLA_USE_OFFLINE_FIXTURES", "1")
    from runtime.engine import HablaEngineV5
    lace_path = os.path.join(os.getcwd(), "LACE.md")
    log_path = tmp_path / "LACE_LOG.md"
    engine = HablaEngineV5(llm=None, memory_path=str(tmp_path / "mem.jsonl"), lace_path=lace_path, lace_log_path=str(log_path))
    state = engine.run("Cuanta gente vive en Mexico")
    assert state.lace_policy_loaded is True
    assert "LACE v2.0 ESTA ACTIVO" in state.llm_directive
    assert log_path.exists()


def test_lace_gate_blocks_without_10_completed_cycles(tmp_path):
    from runtime.lace import LaceRuntime
    lace_path = os.path.join(os.getcwd(), "LACE.md")
    log_path = tmp_path / "LACE_LOG.md"
    runtime = LaceRuntime(policy_path=lace_path, log_path=log_path)
    runtime.preflight("Crear un juego en Python")
    can_close, status = runtime.closure_status()
    assert can_close is False
    assert "0/10" in status


def test_lace_scaffold_creates_templates_without_fake_completion(tmp_path):
    from runtime.lace import LaceRuntime
    lace_path = os.path.join(os.getcwd(), "LACE.md")
    log_path = tmp_path / "LACE_LOG.md"
    runtime = LaceRuntime(policy_path=lace_path, log_path=log_path)
    runtime.preflight("Proyecto de prueba")
    runtime.scaffold_cycles()
    text = log_path.read_text(encoding="utf-8")
    assert "[CICLO-10 PROBLEMAS]" in text
    assert "¿El proyecto mejoró objetivamente? SI" not in text


def test_lace_required_cycles_detected_from_md(tmp_path):
    import os
    from runtime.lace import LacePolicy
    lace_path = os.path.join(os.getcwd(), "LACE.md")
    policy = LacePolicy.load(lace_path)
    assert policy.required_cycles == 10


def test_lace_visual_model_contains_gate(tmp_path):
    import os
    from runtime.lace import LaceRuntime
    lace_path = os.path.join(os.getcwd(), "LACE.md")
    log_path = tmp_path / "LACE_LOG.md"
    runtime = LaceRuntime(policy_path=lace_path, log_path=log_path)
    runtime.preflight("Proyecto visual")
    md = runtime.visual_markdown()
    assert "Puerta de calidad" in md
    assert "Ciclos: 0/10" in md


def test_lace_record_cycle_completion_advances_gate(tmp_path):
    import os
    from runtime.lace import LaceRuntime
    lace_path = os.path.join(os.getcwd(), "LACE.md")
    log_path = tmp_path / "LACE_LOG.md"
    runtime = LaceRuntime(policy_path=lace_path, log_path=log_path)
    runtime.preflight("Proyecto con ciclos reales")
    for i in range(10):
        runtime.record_cycle_completion(
            observation=f"observacion {i}",
            resolved=f"resuelto {i}",
            next_focus="continuar",
        )
    can_close, status = runtime.closure_status()
    assert can_close is True
    assert "Puerta LACE superada" in status


def test_lace_next_action_reports_base_then_cycle(tmp_path):
    import os
    from runtime.lace import LaceRuntime
    lace_path = os.path.join(os.getcwd(), "LACE.md")
    log_path = tmp_path / "LACE_LOG.md"
    runtime = LaceRuntime(policy_path=lace_path, log_path=log_path)
    runtime.preflight("Proyecto base")
    assert "PASO 1" in runtime.next_required_action()
    runtime.log.log_base("base lista")
    assert "CICLO 1" in runtime.next_required_action()
