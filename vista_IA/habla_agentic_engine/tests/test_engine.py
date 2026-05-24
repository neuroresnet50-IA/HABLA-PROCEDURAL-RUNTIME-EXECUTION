from runtime.engine import HablaEngineV4
from connectors.echo_connector import EchoConnector


def test_temporal_question_classifies_and_answers(tmp_path):
    engine = HablaEngineV4(llm=None, memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("Cuanta gente vive en Mexico")
    assert state.knowledge_type == "HECHO_TEMPORAL"
    assert state.safe_to_answer is True
    assert state.confidence.dato >= 70


def test_calculator(tmp_path):
    engine = HablaEngineV4(llm=None, memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("calcula 2+2")
    assert state.knowledge_type == "CALCULO"
    assert "4" in state.answer


def test_echo_connector(tmp_path):
    engine = HablaEngineV4(llm=EchoConnector(), memory_path=str(tmp_path / "mem.jsonl"))
    state = engine.run("Cuanta gente vive en Mexico")
    assert "ECHO" in state.answer
