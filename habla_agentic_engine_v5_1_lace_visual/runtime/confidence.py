from .types import HablaState

class ConfidenceScorer:
    def run(self, state: HablaState) -> HablaState:
        if state.knowledge_type == "CALCULO":
            state.confidence.dato = 99
            state.confidence.fecha = 100
            state.confidence.fuente = 100
            state.confidence.calculo = 99
            state.confidence.inferencia = 0
        elif state.knowledge_type == "HECHO_ESTABLE":
            state.confidence.dato = max(state.confidence.dato, 85)
            state.confidence.fecha = max(state.confidence.fecha, 80)
            state.confidence.fuente = max(state.confidence.fuente, 40)
            state.confidence.inferencia = 20
        elif state.knowledge_type == "INFERENCIA_OPINION":
            state.confidence.dato = max(state.confidence.dato, 60)
            state.confidence.fecha = max(state.confidence.fecha, 60)
            state.confidence.fuente = max(state.confidence.fuente, 40)
            state.confidence.inferencia = 70
        else:
            state.confidence.dato = state.confidence.dato or 50
            state.confidence.fecha = state.confidence.fecha or 50
            state.confidence.fuente = state.confidence.fuente or 50
        state.log(f"CONFIDENCE => dato={state.confidence.dato}, fuente={state.confidence.fuente}")
        return state
