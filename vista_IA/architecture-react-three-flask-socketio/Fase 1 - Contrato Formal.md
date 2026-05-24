# Fase 1 - Contrato Formal

Estado: activo

Documento rector asociado:

- `protocolo Arquitectonico.md`

## Proposito

Este documento formaliza la Fase 1 del proyecto.

Su objetivo es definir el contrato minimo que debe respetar todo el sistema antes de seguir creciendo:

- modelo canonico
- tipos de nodo
- tipos de arista
- tipos de issue
- protocolo de eventos del agente

Este documento no describe una implementacion puntual.

Define el marco tecnico que toda implementacion futura debe obedecer.

## Lenguaje Normativo

En este contrato:

- `DEBE` significa obligatorio
- `DEBERIA` significa recomendado salvo justificacion tecnica fuerte
- `PUEDE` significa opcional

## Alcance

Esta fase cubre:

- la representacion interna unificada del sistema
- la semantica de la arquitectura visual
- la semantica de auditoria
- la semantica de operacion del agente

Esta fase no cubre aun:

- parser perfecto por lenguaje
- reparacion automatica completa
- inferencia semantica total de codigo dinamico
- soporte total de todos los lenguajes

## Objetivo Del Contrato

El sistema DEBE poder recibir codigo real y transformarlo en una IR canonica que permita:

- comprender estructura
- comprender dependencias
- comprender flujo interno
- detectar problemas
- operar con un agente de forma trazable

## Modelo Canonico

La unidad oficial del sistema es una IR llamada `ArchitectureIR`.

`ArchitectureIR` DEBE ser independiente del lenguaje fuente y DEBE permitir representar tanto elementos fisicos como elementos virtuales.

### Estructura Raiz

```json
{
  "version": "1.0",
  "project": {},
  "nodes": [],
  "edges": [],
  "issues": [],
  "sessions": [],
  "scenes": [],
  "metadata": {}
}
```

### Campos Raiz Obligatorios

- `version`: version del contrato
- `project`: identidad del proyecto o analisis actual
- `nodes`: entidades del sistema
- `edges`: relaciones entre entidades
- `issues`: hallazgos de auditoria
- `sessions`: sesiones agentic o de analisis asociadas
- `scenes`: agrupaciones visuales
- `metadata`: datos auxiliares y estadisticos

## Entidades Canonicas

### 1. Project

Representa el espacio de trabajo principal.

Campos minimos:

```json
{
  "id": "project:slug",
  "name": "Nombre del proyecto",
  "slug": "project-slug",
  "rootPath": "/ruta/absoluta/o/logica",
  "originType": "workspace|analysis|transcription",
  "sourceLanguageHints": ["python", "javascript"],
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601"
}
```

### 2. Scene

Representa una escena visual aislada.

Campos minimos:

```json
{
  "id": "scene:project-slug/source-mirror/file-a",
  "projectId": "project:slug",
  "key": "project-slug/source-mirror/file-a",
  "label": "Scene label",
  "origin": { "x": 0, "y": 0 },
  "mode": "workspace|analysis|transcription",
  "readOnly": true
}
```

### 3. Node

Representa una entidad del sistema.

Campos minimos:

```json
{
  "id": "node:unique-id",
  "nodeType": "file",
  "name": "launch.py",
  "projectId": "project:slug",
  "sceneId": "scene:project-slug/file",
  "canonicalPath": "workspace/projects/slug/source-mirror/launch.py",
  "sourcePath": "/ruta/original/launch.py",
  "language": "python",
  "layer": "backend",
  "originType": "physical|virtual|analysis|agent",
  "parentId": null,
  "entryPoint": false,
  "readOnly": true,
  "position": { "x": 180, "y": 160 },
  "description": "Descripcion tecnica",
  "metadata": {}
}
```

Campos normativos:

- `nodeType` DEBE pertenecer al catalogo oficial de tipos
- `originType` DEBE indicar si el nodo es fisico o virtual
- `canonicalPath` DEBE ser la ruta logica interna del sistema
- `sourcePath` DEBERIA existir si el nodo viene de un archivo real
- `sceneId` DEBE permitir aislar visualmente el analisis
- `parentId` PUEDE usarse para agrupar jerarquias
- `entryPoint` DEBE marcar puntos de arranque relevantes

### 4. Edge

Representa una relacion entre nodos o entre pasos de flujo.

Campos minimos:

```json
{
  "id": "edge:unique-id",
  "edgeType": "imports",
  "from": "node:source",
  "to": "node:target",
  "projectId": "project:slug",
  "sceneId": "scene:project-slug/file",
  "originType": "physical|virtual|analysis|agent|inference",
  "label": "importa",
  "confidence": 1.0,
  "metadata": {}
}
```

Campos normativos:

- `from` y `to` DEBEN existir en `nodes` o en el contexto de flujo asociado
- `edgeType` DEBE pertenecer al catalogo oficial
- `confidence` DEBERIA expresar certeza cuando una conexion sea inferida
- `originType` DEBE permitir distinguir evidencia real de inferencia

### 5. Issue

Representa una falla, riesgo o ambiguedad detectada.

Campos minimos:

```json
{
  "id": "issue:unique-id",
  "issueType": "unresolved_import",
  "severity": "error",
  "status": "open",
  "projectId": "project:slug",
  "sceneId": "scene:project-slug/file",
  "nodeId": "node:launch.py",
  "edgeId": null,
  "stepId": null,
  "sourcePath": "/ruta/original/launch.py",
  "lineStart": 12,
  "lineEnd": 12,
  "message": "Import no resuelto",
  "evidence": ["import foo"],
  "suggestedAction": "verificar modulo local",
  "metadata": {}
}
```

### 6. Session

Representa una ejecucion agentic o una ejecucion de analisis.

Campos minimos:

```json
{
  "id": "session:agent-123",
  "sessionType": "agent|analysis",
  "projectId": "project:slug",
  "state": "queued|running|completed|failed|stopped",
  "createdAt": "ISO-8601",
  "startedAt": "ISO-8601",
  "endedAt": null,
  "firstVisualEventAt": null,
  "lastHeartbeatAt": null,
  "summary": null,
  "metadata": {}
}
```

## Tipos Oficiales De Nodo

Todo nodo DEBE pertenecer a uno de estos tipos.

### Tipos Estructurales

- `project`
- `package`
- `directory`
- `module`
- `file`
- `class`
- `function`
- `method`
- `entry_point`

### Tipos De Integracion Y Ejecucion

- `route`
- `event_handler`
- `worker`
- `process`
- `service`
- `api_endpoint`
- `queue`
- `data_store`
- `external_dependency`

### Tipos De Representacion Embebida

- `template`
- `style_sheet`
- `script_block`
- `config_asset`

### Tipos De Flujo

- `control_flow_step`
- `decision_step`
- `io_step`
- `loop_step`
- `start_step`
- `end_step`

### Tipos De Sistema Visual

- `virtual_group`
- `analysis_anchor`

## Reglas Para Tipos De Nodo

- Un archivo real DEBERIA entrar como `file` o `module`
- Una funcion top-level DEBERIA entrar como `function`
- Un metodo de clase DEBERIA entrar como `method`
- Una ruta HTTP DEBERIA entrar como `route` o `api_endpoint`
- Un handler de eventos DEBERIA entrar como `event_handler`
- Una dependencia externa DEBERIA entrar como `external_dependency`
- Un bloque HTML embebido DEBERIA entrar como `template`
- Un paso interno de flujo DEBE entrar como alguno de los tipos de flujo

## Tipos Oficiales De Arista

Toda arista DEBE pertenecer a este catalogo.

### Relaciones Estructurales

- `contains`
- `defines`
- `declares`
- `references`

### Relaciones De Dependencia

- `imports`
- `depends_on`
- `links_to_external`

### Relaciones De Ejecucion

- `calls`
- `starts`
- `spawns`
- `handles`
- `emits`
- `routes_to`
- `renders`

### Relaciones De Datos

- `reads_from`
- `writes_to`
- `shares_schema`
- `syncs_to`

### Relaciones De Flujo

- `flows_to`
- `branch_true`
- `branch_false`
- `loops_to`
- `returns_to`

### Relaciones De Auditoria

- `flags_issue`
- `blocks_execution`

## Reglas Para Tipos De Arista

- `contains` DEBE expresar jerarquia
- `imports` DEBE expresar carga estatica o equivalente
- `calls` DEBE expresar invocacion semantica
- `emits` DEBE expresar evento o mensaje emitido
- `handles` DEBE expresar consumo de evento o callback
- `flows_to` DEBE expresar continuidad de algoritmo
- `branch_true` y `branch_false` DEBEN existir cuando haya decision explicita
- `loops_to` DEBE usarse para back-edge de loops

## Tipos Oficiales De Issue

Todo hallazgo DEBE caer en uno de estos tipos.

### Errores De Codigo

- `syntax_error`
- `indentation_error`
- `parse_failure`
- `type_resolution_failure`

### Errores De Dependencia

- `unresolved_import`
- `missing_dependency`
- `broken_external_reference`

### Errores De Cableado

- `orphan_function`
- `orphan_handler`
- `orphan_route`
- `broken_call_edge`
- `broken_event_wiring`
- `broken_data_flow`
- `missing_entrypoint`

### Errores De Flujo

- `unreachable_code`
- `dead_branch`
- `missing_branch`
- `missing_loop_back_edge`
- `incomplete_control_flow`

### Riesgos O Ambiguedades

- `inference_gap`
- `confidence_low`
- `runtime_contract_gap`

## Severidad Oficial De Issues

- `info`
- `warning`
- `error`
- `critical`

## Estado Oficial De Issues

- `open`
- `confirmed`
- `ignored`
- `resolved`

## Protocolo De Eventos Del Agente

El agente DEBE emitir eventos con un sobre comun.

### Envelope Canonico

```json
{
  "version": "1.0",
  "eventId": "evt-0001",
  "eventType": "upsert_node",
  "sessionId": "session:agent-123",
  "projectId": "project:slug",
  "sceneId": "scene:project-slug/file-a",
  "timestamp": "ISO-8601",
  "sequence": 1,
  "source": "agent",
  "payload": {}
}
```

Campos normativos:

- `eventId` DEBE ser unico por sesion
- `sequence` DEBE ser monotona creciente
- `eventType` DEBE pertenecer al catalogo oficial
- `payload` DEBE respetar el contrato del tipo de evento

## Tipos Oficiales De Evento

### Eventos De Ciclo De Vida

- `session_start`
- `phase`
- `heartbeat`
- `session_complete`
- `session_failed`
- `session_stopped`

### Eventos Visuales

- `upsert_node`
- `upsert_edge`
- `focus_node`
- `upsert_flow_step`
- `upsert_flow_edge`
- `sync_file`

### Eventos De Auditoria

- `report_issue`
- `audit_summary`

## Contrato Por Evento

### 1. `session_start`

Uso:

- declarar inicio real de sesion

Payload minimo:

```json
{
  "sessionType": "agent",
  "projectSlug": "slug",
  "mode": "transcription|generation|repair|analysis"
}
```

### 2. `phase`

Uso:

- marcar la fase actual de trabajo

Payload minimo:

```json
{
  "label": "plan|map|flow|sync|audit|complete",
  "message": "Descripcion humana"
}
```

### 3. `heartbeat`

Uso:

- demostrar que la sesion sigue viva aunque no este escribiendo nodos

Payload minimo:

```json
{
  "state": "running",
  "message": "heartbeat"
}
```

### 4. `upsert_node`

Uso:

- crear o actualizar nodos en el mapa

Payload minimo:

```json
{
  "node": {
    "id": "node:id",
    "nodeType": "file",
    "canonicalPath": "workspace/projects/slug/source-mirror/a.py",
    "sourcePath": "/ruta/original/a.py",
    "name": "a.py",
    "language": "python",
    "layer": "backend",
    "originType": "agent"
  }
}
```

### 5. `upsert_edge`

Uso:

- crear o actualizar relaciones de arquitectura

Payload minimo:

```json
{
  "edge": {
    "id": "edge:id",
    "edgeType": "imports",
    "from": "node:a",
    "to": "node:b",
    "originType": "agent"
  }
}
```

### 6. `focus_node`

Uso:

- indicar a la UI que nodo debe enfocarse

Payload minimo:

```json
{
  "nodeId": "node:id"
}
```

### 7. `upsert_flow_step`

Uso:

- crear o actualizar pasos internos del algoritmo

Payload minimo:

```json
{
  "nodeId": "node:file-a",
  "step": {
    "id": "step:start",
    "nodeType": "start_step",
    "label": "Inicio",
    "x": 300,
    "y": 70
  }
}
```

### 8. `upsert_flow_edge`

Uso:

- conectar pasos del flujo interno

Payload minimo:

```json
{
  "nodeId": "node:file-a",
  "edge": {
    "id": "edge:flow-1",
    "edgeType": "flows_to",
    "from": "step:start",
    "to": "step:load"
  }
}
```

### 9. `sync_file`

Uso:

- sincronizar el codigo real con el inspector

Payload minimo:

```json
{
  "nodeId": "node:file-a",
  "canonicalPath": "workspace/projects/slug/source-mirror/a.py",
  "sourcePath": "/ruta/original/a.py",
  "language": "python",
  "description": "Mirror exacto"
}
```

### 10. `report_issue`

Uso:

- publicar un issue localizado

Payload minimo:

```json
{
  "issue": {
    "id": "issue:1",
    "issueType": "unresolved_import",
    "severity": "error",
    "nodeId": "node:file-a",
    "lineStart": 12,
    "lineEnd": 12,
    "message": "Import no resuelto"
  }
}
```

### 11. `audit_summary`

Uso:

- publicar resumen final de hallazgos

Payload minimo:

```json
{
  "counts": {
    "info": 0,
    "warning": 1,
    "error": 2,
    "critical": 0
  }
}
```

### 12. `session_complete`

Uso:

- marcar final exitoso

Payload minimo:

```json
{
  "state": "completed",
  "summary": "Resumen de trabajo"
}
```

### 13. `session_failed`

Uso:

- marcar final fallido

Payload minimo:

```json
{
  "state": "failed",
  "errorCode": "bridge_timeout",
  "message": "No hubo primer evento visual"
}
```

## Reglas De Orden Del Protocolo Agentic

El runtime agentic DEBE respetar este orden logico:

1. `session_start`
2. `phase(plan)`
3. primer evento visual util
4. eventos de construccion de mapa
5. eventos de construccion de flujo
6. `sync_file`
7. `report_issue` o `audit_summary`
8. `session_complete` o `session_failed`

Reglas:

- una sesion NO DEBE terminar en `completed` si nunca emitio un evento visual util
- `upsert_flow_step` NO DEBE apuntar a un nodo inexistente
- `upsert_edge` NO DEBE conectar nodos inexistentes
- `sync_file` DEBERIA ocurrir despues de que el nodo base exista
- `report_issue` DEBERIA incluir `nodeId`, `sourcePath` y localizacion si existe

## Evento Visual Util

Para este contrato, un evento visual util es cualquiera de estos:

- `upsert_node`
- `upsert_edge`
- `upsert_flow_step`
- `upsert_flow_edge`
- `sync_file`

`phase` y `heartbeat` no cuentan como evidencia visual suficiente.

## Guard Rails Definidos Por Contrato

Aunque su implementacion completa pertenece a la Fase 2, desde ahora quedan definidos:

- `T_first_visual`: tiempo maximo para que aparezca el primer evento visual util
- `T_heartbeat`: tiempo maximo entre heartbeats si no hay mutaciones visuales
- `T_session_idle`: tiempo maximo de silencio antes de marcar sesion fallida

Valores iniciales propuestos:

- `T_first_visual = 10s`
- `T_heartbeat = 5s`
- `T_session_idle = 20s`

Estos valores PUEDEN ajustarse, pero el contrato de existencia del guard rail no puede desaparecer.

## Reglas De Persistencia

- Los nodos virtuales DEBEN persistir aunque no existan como archivos fisicos
- Las escenas DEBEN aislar analisis y transcripciones entre si
- El rescan NO DEBE destruir nodos virtuales emitidos por el agente
- Los nodos `functions`, `routes`, `embedded` y `deps` DEBERIAN vivir en la misma escena logica del archivo que representan

## Reglas De Fidelidad

La transcripcion de un archivo real se considera fiel solo si:

- el codigo sincronizado corresponde a la fuente real
- el mapa refleja modulos, rutas, handlers y dependencias relevantes
- el flujo representa el script completo o el entrypoint completo
- las inferencias quedan marcadas como inferencias
- las incoherencias reales quedan reportadas como issues o observaciones de auditoria

## Reglas De Implementacion Para Adaptadores

Todo adaptador por lenguaje DEBE producir:

- nodos canonicos
- aristas canonicas
- issues canonicos
- metadatos de confianza

Todo adaptador por lenguaje DEBERIA declarar:

- lenguaje
- version del parser
- limitaciones conocidas
- zonas de inferencia

## Reglas De Implementacion Para La UI

La UI DEBE:

- renderizar nodos y aristas de la IR
- renderizar issues localizados
- distinguir nodos fisicos de nodos virtuales
- mostrar estado de sesion agentic
- mostrar cuando una sesion falla por timeout o silencio

La UI NO DEBE inventar semantica que no exista en la IR.

## Criterios De Aceptacion De Fase 1

La Fase 1 se considera cumplida cuando:

1. existe este contrato formal
2. existe un catalogo oficial de nodos
3. existe un catalogo oficial de aristas
4. existe un catalogo oficial de issues
5. existe un protocolo formal de eventos del agente
6. las siguientes fases pueden implementarse contra este documento sin improvisar nombres o estructuras

## Matriz De Validacion Minima Para Fases Posteriores

La implementacion futura DEBERA poder validarse al menos contra estos casos:

- un script Python simple
- un archivo Python con loops y `if/else`
- un proyecto Python multiarchivo
- un archivo JS/TS con imports y funciones
- un HTML con JS embebido
- una transcripcion con nodos virtuales
- una sesion agentic que falle por no emitir eventos visuales

## Resultado Esperado De Esta Fase

Al cerrar esta fase, el equipo ya no deberia preguntarse:

- como se llama un nodo
- como se llama una arista
- que cuenta como issue
- que evento debe emitir el agente
- cuando una sesion debe fallar

Si esas preguntas siguen ambiguas, la Fase 1 no esta cerrada.
