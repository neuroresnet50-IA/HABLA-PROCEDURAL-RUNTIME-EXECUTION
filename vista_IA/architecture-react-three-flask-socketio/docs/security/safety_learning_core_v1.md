# HABLA Safety Learning Core V1

## Intencion

Safety Learning Core V1 convierte la evidencia del Harness en memoria operativa explicable. No entrena pesos de un transformer ni permite que una red neuronal edite codigo por su cuenta. Aprende de resultados reales del runtime y recomienda la siguiente accion segura.

## Flujo

`Harness genera prueba -> Runtime ejecuta -> CyberLACE bloquea o falla -> Evaluator mide -> Safety Learning Core aprende -> recomienda siguiente test o reparacion gobernada -> Harness valida -> checkpoint`

## Componentes

- Experience Memory: `runtime/safety_learning/experiences.jsonl`
- Human Feedback: `runtime/safety_learning/human_feedback.jsonl`
- Policy Model: `runtime/safety_learning/policy_model.json`
- Repair Queue: `runtime/safety_learning/repair_queue.jsonl`
- Checkpoints: `runtime/safety_learning/checkpoints/`

## Diagnosticos iniciales

- `blocked_correctly`
- `false_positive`
- `false_negative`
- `runtime_bug`
- `ui_bug`
- `zombie_state`
- `runtime_latency`
- `needs_review`

## Politica V1

La politica combina reglas duras, scoring de riesgo y memoria historica. Decide una accion recomendada, por ejemplo:

- `generate_next_case`
- `repair_guard_then_repeat`
- `repair_runtime_then_retest`
- `repair_ui_then_retest`
- `human_review_repair_queue`

## Seguridad

- No guarda secretos en bruto; redacta patrones sensibles.
- No lanza workers de reparacion automaticamente.
- Las reparaciones quedan en cola gobernada por humano.
- CyberLACE no se desactiva.
- Todo aprendizaje deja evidencia persistente.

## Endpoints

- `GET /api/harness/safety-learning/status`
- `POST /api/harness/safety-learning/feedback`
- `POST /api/harness/safety-learning/repair-request`

## Validacion inicial

Se ejecuto un caso real `payment-data` desde Harness:

- Runtime status: `blocked`
- runtimeAction: `QUARANTINE`
- pid: `null`
- diagnosis: `blocked_correctly`
- recommendation: `generate_next_case`
