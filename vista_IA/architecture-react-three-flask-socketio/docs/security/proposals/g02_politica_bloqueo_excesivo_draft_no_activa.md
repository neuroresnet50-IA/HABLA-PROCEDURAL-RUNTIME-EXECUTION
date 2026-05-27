# DRAFT NO ACTIVO: Politica De Bloqueo Excesivo

Fecha: 2026-05-25T10:51:44.173504+00:00
Estado: BORRADOR / NO ACTIVO
Caso relacionado: G02 Abstraccion de seguridad demasiado amplia

## Advertencia

Este documento NO es una politica activa de HABLA. No debe ser cargado por el runtime, no debe reemplazar `runtime/security_policy.json` y no debe implementarse sin validacion.

## Propuesta Rechazada Como Activa

Bloquear globalmente cualquier documento, prompt o tarea que mencione terminos como token, password, secret, key, API, GitHub, OpenAI o seguridad.

## Motivo De Rechazo

La propuesta es demasiado amplia. Puede bloquear documentacion legitima, pruebas defensivas, reportes redactados, fixtures seguros y explicaciones tecnicas.

## Condiciones Minimas Para Reconsiderar

Antes de convertirse en politica activa tendria que incluir:

- Alcance exacto.
- Ejemplos permitidos.
- Ejemplos prohibidos.
- Excepciones para documentacion y evidencia redactada.
- Pruebas de falso positivo.
- Pruebas de falso negativo.
- Aprobacion humana.
- Checkpoint y rollback.

## Estado Final

No activa. Conservada solo como evidencia de gobernanza.
