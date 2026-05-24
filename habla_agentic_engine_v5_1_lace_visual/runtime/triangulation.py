from statistics import mean
from .types import HablaState

class Triangulator:
    def run(self, state: HablaState) -> HablaState:
        values = [e.value for e in state.observations if e.value is not None]
        if not values:
            state.triangulated_text = "No hay valores numéricos para triangular."
            state.log("TRIANGULATE => sin valores")
            return state
        if len(values) == 1:
            state.triangulated_text = f"Una sola fuente indica aproximadamente {values[0]:,.0f}."
            state.confidence.dato = max(state.confidence.dato, 85)
            state.confidence.fecha = max(state.confidence.fecha, 75)
            state.confidence.fuente = max(state.confidence.fuente, state.observations[0].confidence_hint)
            state.log("TRIANGULATE => una fuente")
            return state

        avg = mean(values)
        spread = max(values) - min(values)
        state.triangulated_text = f"Las fuentes se agrupan alrededor de {avg:,.0f}, con rango {min(values):,.0f}–{max(values):,.0f}."
        if spread <= 2_000_000:
            state.confidence.dato = 95
            state.confidence.fecha = 85
            state.confidence.fuente = 90
            state.log("TRIANGULATE => consistentes")
        elif spread <= 5_000_000:
            state.confidence.dato = 80
            state.confidence.fecha = 75
            state.confidence.fuente = 75
            state.log("TRIANGULATE => parcialmente consistentes")
        else:
            state.confidence.dato = 55
            state.confidence.fecha = 60
            state.confidence.fuente = 60
            state.log("TRIANGULATE => contradicción")
        return state
