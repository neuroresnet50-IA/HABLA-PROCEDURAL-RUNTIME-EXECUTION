from .types import HablaState

class ConstitutionalChecker:
    def run(self, state: HablaState) -> HablaState:
        if state.blocked:
            state.safe_to_answer = False
            return state
        if state.knowledge_type == "HECHO_TEMPORAL":
            if state.confidence.dato < 70:
                state.blocked = True
                state.block_reason = "Dato temporal con confianza insuficiente."
            elif state.confidence.fuente < 70:
                state.blocked = True
                state.block_reason = "Fuente insuficiente para dato temporal."
        state.safe_to_answer = not state.blocked
        state.log(f"CONSTITUTIONAL => safe={state.safe_to_answer}, reason={state.block_reason}")
        return state
