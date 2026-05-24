from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from agent_runtime import (
    _has_canonical_lace_closure_marker,
    build_lace_cycle_plan,
    detect_lace_required_cycles,
    count_completed_lace_cycles,
    extract_lace_cycle_sections,
    initialize_lace_log,
    is_lace_placeholder,
    is_observational_smoke_requirement,
    is_valid_lace_completed_section,
    lace_closure_status,
    scaffold_lace_cycles,
    validate_lace_log,
)


def build_valid_cycle(cycle_number: int, next_focus: str) -> str:
    return f"""
[CICLO-{cycle_number} PROBLEMAS]
THOUGHT: Revisé el estado del proyecto y detecté un hueco concreto en el ciclo {cycle_number}.
TRIANGULACIÓN: técnico: falta cobertura directa; funcional: el flujo queda incompleto; humano: el uso no es claro sin esta mejora.
CONFIANZA: lógica media, UI media, rendimiento alta, errores media, seguridad media.
AUTO-CRÍTICA: Si cierro ahora, todavía quedaría una debilidad visible en el ciclo {cycle_number}.

Problemas priorizados:
1. La mejora del ciclo {cycle_number} no está consolidada — severidad: alta

[CICLO-{cycle_number} MEJORA]
THOUGHT: Voy a cerrar la brecha detectada en el ciclo {cycle_number} con una mejora verificable.
ACTION: Implementar el ajuste del ciclo {cycle_number} y documentar su resultado.
OBSERVATION esperada: La salida del ciclo {cycle_number} queda estable y lista para la siguiente iteración.

[CICLO-{cycle_number} COMPLETADO]
OBSERVATION real: La mejora del ciclo {cycle_number} quedó validada con evidencia escrita.
¿Coincide con OBSERVATION esperada? SI
Problemas resueltos: La brecha prioritaria del ciclo {cycle_number} quedó cubierta.
Estado ahora vs antes: El proyecto tiene una mejora verificable frente al estado previo del ciclo {cycle_number}.
¿El proyecto mejoró objetivamente? SI

MEMORIA EPISÓDICA:
- Qué funcionó: La verificación explícita del ciclo {cycle_number}.
- Qué no funcionó: Un primer enfoque demasiado superficial que fue descartado a tiempo.
- Qué evitar en el próximo ciclo: Cerrar sin contrastar la mejora con el objetivo esperado.

Próximo ciclo — qué atacaré: {next_focus}
""".strip()


def build_valid_completed_section(next_label: str) -> str:
    return f"""
OBSERVATION real: La evidencia final quedó registrada.
Coincide con OBSERVATION esperada? SI
Problemas resueltos: falta de cierre verificable.
Estado ahora vs antes: ahora existe evidencia final del ciclo.
El proyecto mejoro objetivamente? SI

MEMORIA EPISODICA:
- Que funciono: Cerrar con evidencia real.
- Que no funciono: Un intento anterior demasiado corto.
- Que evitar en el proximo ciclo: Declarar cierre sin trazabilidad.

{next_label} ninguno; cierre final.
""".strip()


class LaceValidationTest(unittest.TestCase):
    def test_observational_smoke_requirement_detection_is_strict_enough(self) -> None:
        self.assertFalse(
            is_observational_smoke_requirement(
                "Crea docs/internal-smoke.md con una verificacion breve y cambios minimos conectados."
            )
        )
        with patch.dict("os.environ", {"VISTA_AGENT_RUNTIME_MODE": "smoke"}, clear=False):
            self.assertTrue(
                is_observational_smoke_requirement(
                    "Construye un frontend completo con 10 ciclos de mejora y cierre arquitectonico."
                )
            )
        self.assertFalse(
            is_observational_smoke_requirement(
                "Construye un frontend completo con 10 ciclos de mejora y cierre arquitectonico."
            )
        )

    def test_lace_required_cycles_are_clamped_to_adaptive_range(self) -> None:
        self.assertEqual(detect_lace_required_cycles("completar 1 ciclos"), 2)
        self.assertEqual(detect_lace_required_cycles("completar 20 ciclos"), 10)
        self.assertEqual(detect_lace_required_cycles("sin regla numerica"), 10)

    def test_template_scaffold_does_not_count_as_completed_cycles(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "LACE_LOG.md"
            policy_path = Path(tmpdir) / "LACE.md"
            initialize_lace_log(
                log_path,
                project_prompt="Proyecto mínimo de prueba.",
                policy_path=policy_path,
                required_cycles=2,
            )
            scaffold_lace_cycles(log_path, 2)

            self.assertEqual(count_completed_lace_cycles(log_path), 0)
            can_close, status = lace_closure_status(log_path, 2)
            self.assertFalse(can_close)
            self.assertIn("0/2", status)

    def test_positive_markers_without_full_cycle_structure_do_not_unlock_lace(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "LACE_LOG.md"
            log_path.write_text(
                (
                    "# LACE_LOG.md\n\n"
                    "[COMPRENSIÓN DEL PROYECTO]\n"
                    "Construir un módulo de saludo mínimo.\n\n"
                    "[PLAN PARA 2 CICLOS]\n"
                    f"{build_lace_cycle_plan(2)}\n\n"
                    "[BASE] Construcción inicial completada.\n"
                    "Estado actual: Existe una base mínima funcional.\n\n"
                    "[CICLO-1 COMPLETADO]\n"
                    "OBSERVATION real: Se añadió una mejora.\n"
                    "¿Coincide con OBSERVATION esperada? SI\n"
                    "Problemas resueltos: Se cerró una brecha inicial.\n"
                    "Estado ahora vs antes: El proyecto está mejor que antes.\n"
                    "¿El proyecto mejoró objetivamente? SI\n\n"
                    "MEMORIA EPISÓDICA:\n"
                    "- Qué funcionó: La mejora puntual.\n"
                    "- Qué no funcionó: Un intento previo.\n"
                    "- Qué evitar en el próximo ciclo: Cerrar demasiado pronto.\n\n"
                    "Próximo ciclo — qué atacaré: Consolidar la base.\n\n"
                    "[CICLO-2 COMPLETADO]\n"
                    "OBSERVATION real: Se añadió una segunda mejora.\n"
                    "¿Coincide con OBSERVATION esperada? SI\n"
                    "Problemas resueltos: Se cerró una segunda brecha.\n"
                    "Estado ahora vs antes: El proyecto volvió a mejorar.\n"
                    "¿El proyecto mejoró objetivamente? SI\n\n"
                    "MEMORIA EPISÓDICA:\n"
                    "- Qué funcionó: La segunda mejora puntual.\n"
                    "- Qué no funcionó: Un intento inicial demasiado corto.\n"
                    "- Qué evitar en el próximo ciclo: Declarar éxito sin análisis.\n\n"
                    "Próximo ciclo — qué atacaré: Revisión final.\n"
                ),
                encoding="utf-8",
            )

            self.assertEqual(count_completed_lace_cycles(log_path), 0)
            can_close, status = lace_closure_status(log_path, 2)
            self.assertFalse(can_close)
            self.assertIn("ciclos válidos", status)

    def test_full_lace_cycles_unlock_closure(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "LACE_LOG.md"
            log_path.write_text(
                (
                    "# LACE_LOG.md\n\n"
                    "[COMPRENSIÓN DEL PROYECTO]\n"
                    "Construir un módulo de saludo mínimo.\n\n"
                    "[PLAN PARA 2 CICLOS]\n"
                    f"{build_lace_cycle_plan(2)}\n\n"
                    "[BASE] Construcción inicial completada.\n"
                    "Estado actual: Existe una base mínima funcional con punto de entrada claro.\n\n"
                    f"{build_valid_cycle(1, 'Normalizar la interfaz pública del módulo.')}\n\n"
                    f"{build_valid_cycle(2, 'Revisión final del flujo y documentación.')}\n"
                ),
                encoding="utf-8",
            )

            self.assertEqual(count_completed_lace_cycles(log_path), 2)
            can_close, status = lace_closure_status(log_path, 2)
            self.assertTrue(can_close)
            self.assertEqual(status, "Puerta LACE superada.")

    def test_lace_validation_accepts_unaccented_real_world_log_variants(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "LACE_LOG.md"
            log_path.write_text(
                (
                    "# LACE_LOG.md\n\n"
                    "[INIT]\n"
                    "Fecha local aproximada: 2026-05-10 America/Los_Angeles\n\n"
                    "[COMPRENSION INICIAL]\n"
                    "Construir un juego compacto y jugable.\n\n"
                    "[PLAN DE CONSTRUCCION]\n"
                    "1. Base jugable.\n"
                    "2. Organizacion modular.\n\n"
                    "[BASE]\n"
                    "Construccion inicial completada.\n"
                    "Estado actual: existe una primera version funcional.\n\n"
                    "[CICLO-1 PROBLEMAS]\n"
                    "THOUGHT: hacia falta una base jugable real.\n"
                    "TRIANGULACION: tecnico = faltaba logica; funcional = no se podia jugar; humano = no habia experiencia.\n"
                    "CONFIANZA: logica = baja, ui = baja, rendimiento = baja, errores = baja, seguridad = media.\n"
                    "AUTO-CRITICA: sin base jugable cualquier cierre seria falso.\n\n"
                    "Problemas priorizados:\n"
                    "1. No existe juego funcional - severidad: alta\n\n"
                    "[CICLO-1 MEJORA]\n"
                    "THOUGHT: la solucion correcta es construir la base completa.\n"
                    "ACTION: crear html, loop e input reales.\n"
                    "OBSERVATION esperada: el proyecto pasa a estado jugable.\n\n"
                    "[CICLO-1 COMPLETADO]\n"
                    "OBSERVATION real: ahora existe una partida jugable.\n"
                    "Coincide con OBSERVATION esperada? SI\n"
                    "Problemas resueltos: juego inexistente, ausencia de html y loop.\n"
                    "Estado ahora vs antes: antes habia bootstrap vacio y ahora hay juego.\n"
                    "El proyecto mejoro objetivamente? SI\n\n"
                    "MEMORIA EPISODICA:\n"
                    "- Que funciono: separar estado y render.\n"
                    "- Que no funciono: intentar extender el bootstrap anterior.\n"
                    "- Que evitar en el proximo ciclo: mezclar dom y simulacion.\n\n"
                    "Proximo ciclo - que atacare: organizacion interna.\n\n"
                    "[CICLO-2 PROBLEMAS]\n"
                    "THOUGHT: habia que fijar fronteras claras entre modulos.\n"
                    "TRIANGULACION: tecnico = riesgo de acoplamiento; funcional = hoy se puede jugar; humano = el siguiente cambio seria fragil.\n"
                    "CONFIANZA: logica = media, ui = media, rendimiento = media, errores = baja, seguridad = media.\n"
                    "AUTO-CRITICA: un parche monolitico habria sido mas rapido pero peor.\n\n"
                    "Problemas priorizados:\n"
                    "1. Riesgo de acoplar estado, render e input - severidad: alta\n\n"
                    "[CICLO-2 MEJORA]\n"
                    "THOUGHT: habia que separar responsabilidades antes de seguir.\n"
                    "ACTION: mover estado, render e input a modulos claros.\n"
                    "OBSERVATION esperada: cada modulo queda con una responsabilidad testable.\n\n"
                    "[CICLO-2 COMPLETADO]\n"
                    "OBSERVATION real: la arquitectura modular quedo visible y estable.\n"
                    "Coincide con OBSERVATION esperada? SI\n"
                    "Problemas resueltos: acoplamiento principal y falta de responsabilidades claras.\n"
                    "Estado ahora vs antes: la base es mas mantenible.\n"
                    "El proyecto mejoro objetivamente? SI\n\n"
                    "MEMORIA EPISODICA:\n"
                    "- Que funciono: usar imports reales entre modulos.\n"
                    "- Que no funciono: ningun bloqueo relevante.\n"
                    "- Que evitar en el proximo ciclo: ui sin informacion operativa.\n\n"
                    "Proximo ciclo - que atacare: experiencia visual.\n"
                ),
                encoding="utf-8",
            )

            self.assertEqual(count_completed_lace_cycles(log_path), 2)
            can_close, status = lace_closure_status(log_path, 2)
            self.assertTrue(can_close)
            self.assertEqual(status, "Puerta LACE superada.")

    def test_lace_validation_accepts_embedded_improvement_block_inside_problems(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "LACE_LOG.md"
            log_path.write_text(
                (
                    "# LACE_LOG.md\n\n"
                    "[COMPRENSIÓN DEL PROYECTO]\n"
                    "Construir una mini app.\n\n"
                    "[PLAN PARA 1 CICLOS]\n"
                    "1. Revisión final.\n\n"
                    "[BASE] Construcción inicial completada.\n"
                    "Estado actual: Existe una base funcional verificable.\n\n"
                    "[CICLO-1 PROBLEMAS]\n"
                    "THOUGHT: Falta una verificación final del ciclo.\n"
                    "TRIANGULACIÓN: técnico = falta cierre; funcional = falta evidencia; humano = aumenta la incertidumbre.\n"
                    "CONFIANZA: lógica = media, UI = media, rendimiento = media, errores = media, seguridad = media.\n"
                    "AUTO-CRÍTICA: Cerrar sin este paso dejaría una validación incompleta.\n\n"
                    "Problemas priorizados:\n"
                    "1. No existe cierre verificable del ciclo 1. — severidad: media\n\n"
                    "THOUGHT: Voy a cerrar la brecha con evidencia final.\n"
                    "ACTION: Ejecutar la validación final y documentar el resultado.\n"
                    "OBSERVATION esperada: El ciclo queda listo para cierre.\n\n"
                    "[CICLO-1 COMPLETADO]\n"
                    "OBSERVATION real: La evidencia final quedó registrada.\n"
                    "¿Coincide con OBSERVATION esperada? SI\n"
                    "Problemas resueltos: falta de cierre verificable.\n"
                    "Estado ahora vs antes: ahora existe evidencia final del ciclo.\n"
                    "¿El proyecto mejoró objetivamente? SI\n\n"
                    "MEMORIA EPISÓDICA:\n"
                    "- Qué funcionó: Cerrar con evidencia real.\n"
                    "- Qué no funcionó: Un intento anterior demasiado corto.\n"
                    "- Qué evitar en el próximo ciclo: Declarar cierre sin trazabilidad.\n\n"
                    "Próximo ciclo — qué atacaré: ninguno; cierre final.\n"
                ),
                encoding="utf-8",
            )

            self.assertEqual(count_completed_lace_cycles(log_path), 1)
            can_close, status = lace_closure_status(log_path, 1)
            self.assertTrue(can_close)
            self.assertEqual(status, "Puerta LACE superada.")


    def test_lace_doc_header_no_body_si_does_not_count_as_valid_doc(self) -> None:
        text = """# Ciclo 04

- Estado: completed
- Valido para cierre LACE: no

## Observaciones
Durante el análisis se mencionó "Valido para cierre LACE: si", pero esto no es marcador canónico.
"""

        self.assertFalse(_has_canonical_lace_closure_marker(text))

    def test_lace_doc_header_si_counts_only_when_anchored(self) -> None:
        text = """# Ciclo 04

- Estado: completed
- Valido para cierre LACE: si

## Observaciones
Texto narrativo posterior.
"""

        self.assertTrue(_has_canonical_lace_closure_marker(text))

    def test_lace_log_recalce_completed_sections_are_parsed(self) -> None:
        with TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "LACE_LOG.md"
            cycle = build_valid_cycle(1, "ninguno; cierre final.")
            cycle = cycle.replace("[CICLO-1 PROBLEMAS]", "[CICLO-1 RECALCE 20260521 PROBLEMAS]")
            cycle = cycle.replace("[CICLO-1 MEJORA]", "[CICLO-1 RECALCE 20260521 MEJORA]")
            cycle = cycle.replace("[CICLO-1 COMPLETADO]", "[CICLO-1 RECALCE 20260521 COMPLETADO]")
            cycle = cycle.replace("Próximo ciclo — qué atacaré:", "Proximo ciclo:")
            log_path.write_text(
                (
                    "# LACE_LOG.md\n\n"
                    "[COMPRENSIÓN DEL PROYECTO]\n"
                    "Construir una mini app.\n\n"
                    "[PLAN PARA 1 CICLOS]\n"
                    "1. Revisión final.\n\n"
                    "[BASE] Construcción inicial completada.\n"
                    "Estado actual: Existe una base funcional verificable.\n\n"
                    f"{cycle}\n"
                ),
                encoding="utf-8",
            )

            self.assertEqual(validate_lace_log(log_path, 1)[0], 1)
            can_close, status = lace_closure_status(log_path, 1)
            self.assertTrue(can_close)
            self.assertEqual(status, "Puerta LACE superada.")
            sections = extract_lace_cycle_sections(log_path.read_text(encoding="utf-8"))
            self.assertIn("COMPLETADO", sections[1])

    def test_lace_placeholder_does_not_reject_retrospective_pending_sentence(self) -> None:
        self.assertFalse(
            is_lace_placeholder(
                "antes el ciclo 04 estaba pendiente de cierre; ahora hay evidencia fresca verificable."
            )
        )
        self.assertTrue(is_lace_placeholder("pendiente"))
        self.assertTrue(is_lace_placeholder("pendiente de ejecucion"))

    def test_lace_completed_accepts_proximo_cierre_memory_label(self) -> None:
        section = build_valid_completed_section("Proximo ciclo:")
        section = section.replace("- Que evitar en el proximo ciclo:", "- Que evitar en el proximo cierre:")
        self.assertTrue(is_valid_lace_completed_section(section))

    def test_lace_completed_accepts_proximo_without_accent(self) -> None:
        self.assertTrue(is_valid_lace_completed_section(build_valid_completed_section("Proximo ciclo:")))

    def test_lace_completed_accepts_proximo_with_accent(self) -> None:
        self.assertTrue(is_valid_lace_completed_section(build_valid_completed_section("Próximo ciclo:")))


if __name__ == "__main__":
    unittest.main()
