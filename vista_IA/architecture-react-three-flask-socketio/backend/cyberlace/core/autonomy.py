from cyberlace.core.models import GuardDecision


class AutonomyGovernor:
    LEVELS = {
        0: "solo_responde",
        1: "sugiere_acciones",
        2: "tools_seguras",
        3: "tools_con_monitoreo",
        4: "requiere_aprobacion",
        5: "cuarentena_solo_lectura",
    }

    def evaluate(self, current_level: int, decision: GuardDecision) -> int:
        risk = decision.risk_score
        if risk >= 90:
            return 5
        if risk >= 80:
            return max(current_level, 4)
        if risk >= 60:
            return max(current_level, 3)
        if risk >= 40:
            return max(current_level, 2)
        return current_level
