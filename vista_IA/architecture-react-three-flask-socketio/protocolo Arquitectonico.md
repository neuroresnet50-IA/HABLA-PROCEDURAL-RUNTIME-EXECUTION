# Protocolo Arquitectonico

Estado: activo

Proyecto: `architecture-react-three-flask-socketio`

Tipo de sistema: plataforma de inteligencia artificial para comprension, representacion, auditoria y evolucion de software real.

## Proposito

Este archivo es el contrato rector del proyecto.

Su funcion es fijar:

- que sistema estamos construyendo
- que metas cubre
- que compromisos tecnicos no se pueden romper
- que resultados se consideran validos
- en que orden se deben ejecutar las fases

Toda nueva arquitectura, integracion, refactor o funcionalidad importante debe alinearse con este documento.

La regla principal es esta:

> no se debe seguir improvisando codigo fuera de un contrato de arquitectura, una representacion canonica del sistema y un plan verificable de implementacion y prueba.

## Declaracion Del Producto

Estamos construyendo un sistema de inteligencia artificial para:

- leer codigo fuente real
- modelarlo internamente de forma canonica
- visualizarlo como arquitectura, dependencias, flujo de control y secuencia logica
- auditarlo para encontrar errores y cableado roto
- permitir que un agente lo comprenda, lo repare, lo reorganice y lo extienda

Este producto no es una interfaz visual aislada ni un canvas decorativo.

Es un entorno de:

- comprension
- diseno
- ejecucion asistida por IA
- auditoria tecnica
- evolucion guiada del software

## Que Estamos Buscando

La plataforma debe poder hacer tres trabajos sobre codigo real:

1. Comprender un archivo o un proyecto existente.
2. Representarlo visualmente como mapa conceptual, dependencias, flujo interno y secuencia entre bloques.
3. Operar sobre el con un agente que pueda crear, reparar, reorganizar y extender el sistema.

## Que Queremos

El objetivo real del producto es este:

- cargar cualquier script o proyecto: `python`, `js`, `html`, `css`, `cpp`, y luego mas lenguajes
- convertirlo en una representacion canonica interna
- mostrar:
  - mapa de modulos
  - dependencias
  - funciones
  - clases
  - rutas
  - eventos
  - loops
  - `if/else`
  - flujo de control
  - llamadas entre bloques
- detectar fallas:
  - imports rotos
  - funciones huerfanas
  - ramas sin salida
  - codigo inaccesible
  - errores sintacticos
  - cableado mal conectado
- permitir que un agente:
  - lea ese contexto
  - vea donde falla
  - repare
  - agregue funcionalidad
  - actualice el mapa y el flujo en vivo

## Metas No Negociables

- El sistema debe trabajar sobre codigo real, no sobre demos aisladas.
- El cambio de script, lenguaje o proyecto debe ser un caso normal del producto, no una excepcion.
- La representacion visual debe nacer de un modelo interno estable, no de heuristicas sueltas de UI.
- El agente debe operar con protocolo y trazabilidad, no con comportamiento silencioso o ambiguo.
- Cada avance importante debe quedar documentado, implementado y probado.

## Compromisos Del Proyecto

Nos comprometemos a construir el sistema bajo estas reglas:

1. Toda funcionalidad importante debe estar respaldada por una representacion canonica interna.
2. Ningun cambio grande de arquitectura debe entrar sin quedar reflejado en este archivo.
3. Cada motor nuevo debe tener criterio de entrada, salida y validacion.
4. El runtime agentic no puede quedar en estados mudos o colgados sin error explicito.
5. El editor visual debe soportar nodos fisicos y nodos virtuales sin perder persistencia.
6. Los adaptadores por lenguaje deben separarse por responsabilidad.
7. El producto debe probarse con scripts reales y variados, no solo con un caso fijo.
8. Los errores del sistema deben ser visibles, localizables y accionables.

## Resultados Esperados

Cuando este sistema funcione como se espera, debe permitir:

- cargar un archivo o un proyecto y entender su arquitectura rapidamente
- ver el harness del sistema completo sin inspeccionar archivo por archivo
- detectar visualmente donde se rompio la conectividad logica
- abrir el bloque exacto, ver su codigo y su flujo
- pasar ese contexto a un agente para reparar o extender el sistema
- mantener el mapa, el flujo y el codigo sincronizados

## Arquitectura Objetivo: Cuatro Motores

La solucion correcta no es seguir parchando pantallas.

La solucion es una arquitectura de cuatro motores.

### Motor A: Modelo Canonico

Debe existir una IR unica del sistema, independiente del lenguaje.

Debe representar, como minimo:

- `project`
- `module/file`
- `class`
- `function/method`
- `route`
- `event_handler`
- `dependency`
- `control_flow_step`
- `call_edge`
- `data_edge`
- `issue`

Sin esta capa, todo se rompe cuando cambia el script, el repositorio o el lenguaje.

### Motor B: Ingesta Y Analisis

Debe haber adaptadores por lenguaje que conviertan codigo real a la IR.

Prioridad inicial:

- Python: `AST + CFG + imports + call graph`
- JS/TS: `AST + CFG + imports + call graph`
- HTML/CSS: estructura, scripts embebidos, assets y eventos
- C++ despues: parser y dependencias basicas primero

Este motor no necesita perfeccion total desde el dia uno.

Pero si necesita:

- consistencia
- trazabilidad
- separacion por lenguaje
- resultados suficientemente utiles para visualizacion y auditoria

### Motor C: Orquestacion Visual

El editor no puede depender solo de lo que exista como archivo fisico en disco.

Debe soportar:

- nodos fisicos
- nodos virtuales
- subflujos
- escenas aisladas por analisis
- persistencia exacta del estado visual
- event sourcing del agente

Este motor es responsable de que el mapa conceptual, los diagramas de flujo y los paneles de codigo representen lo mismo y no se contradigan entre si.

### Motor D: Runtime Agentic

El agente no puede ser libre y silencioso.

Debe seguir un protocolo rigido y verificable.

Secuencia minima obligatoria:

1. `session_start`
2. `phase(plan)`
3. `upsert_node` inicial
4. `upsert_edge`
5. `upsert_flow_step`
6. `sync_file`
7. `audit`
8. `session_complete`

Si no emite el primer evento visual en cierto tiempo:

- la sesion se marca como fallida
- se informa el error
- no puede quedar colgada en estado de espera indefinida

## Donde Estamos Atorados De Verdad

El cuello de botella principal no es "leer scripts".

El cuello de botella actual es este:

- el agente a veces arranca
- pero no garantiza emitir eventos visuales
- entonces la UI queda sin mapa aunque el proceso siga vivo

Eso no es un problema de concepto.

Es un problema de protocolo de ejecucion agentic.

## Metodo De Trabajo Correcto

El trabajo debe avanzar en este orden:

1. Definir el contrato del sistema.
2. Cerrar el runtime del agente.
3. Formalizar reverse engineering.
4. Separar por lenguaje.
5. Usar al agente como operador del sistema, no como parche improvisado.

Esto significa que:

- primero se define el modelo
- luego se obliga al runtime a comportarse correctamente
- luego se formaliza la ingesta
- luego se expanden lenguajes
- luego se endurece la operacion del agente sobre esa base

## Definicion Corta Del Producto

> Un sistema de inteligencia artificial para leer, modelar, visualizar, auditar y evolucionar software real a partir de codigo fuente y requerimientos en lenguaje natural.

## Regla De Gobernanza

Este archivo gobierna la evolucion del proyecto.

Por lo tanto:

- toda fase nueva debe quedar declarada aqui
- todo cambio mayor de arquitectura debe justificar como encaja aqui
- toda funcionalidad nueva importante debe indicar que motor toca
- toda prueba relevante debe mapearse a una meta de este protocolo

Artefacto normativo asociado a la Fase 1:

- `Fase 1 - Contrato Formal.md`

## Regla De Implementacion

Ninguna solucion importante debe considerarse valida si no cumple las tres capas:

1. Documentacion
2. Codigo
3. Prueba o verificacion

Si falta una de las tres, el avance no esta completo.

## Regla De Pruebas

Cada capacidad principal debe poder comprobarse contra entradas reales.

El sistema debe poder ser probado, como minimo, con:

- scripts Python sueltos
- proyectos Python multiarchivo
- scripts JS/TS
- HTML con JS embebido
- CSS relacionado a una UI real
- archivos C++ en fases posteriores

La meta no es pasar una demo unica.

La meta es soportar variacion real de codigo y estructura.

## Restricciones De Calidad

No se considera aceptable:

- que el agente quede corriendo sin producir eventos visuales
- que el mapa muestre una arquitectura que no corresponde al codigo
- que el flujo muestre solo una fraccion irrelevante del script
- que los nodos virtuales se pierdan por el rescan
- que cambiar de lenguaje o script rompa el modelo base
- que el sistema dependa de una sola heuristica para todo

## Fases Aprobadas

### Fase 1: Contrato Formal

Entregables obligatorios:

- modelo canonico
- tipos de nodo
- tipos de arista
- tipos de issue
- protocolo de eventos del agente

Estado de fase:

- aprobada para ejecucion
- documentacion formal requerida en `Fase 1 - Contrato Formal.md`
- toda implementacion posterior debe citar este contrato

### Fase 2: Guard Rails Del Runtime Agentic

Entregables obligatorios:

- timeout de primer evento visual
- heartbeat de sesion
- error explicito si el agente no entra al bridge
- criterio de sesion fallida visible en UI y backend

### Fase 3: Pipeline Formal De Reverse Engineering

Entregables obligatorios:

- entrada uniforme `archivo -> adaptador -> IR -> mapa -> flujo -> issues`
- escenas de solo lectura separadas del editor manual
- persistencia estable del analisis

### Fase 4: Adaptadores Por Lenguaje

Entregables obligatorios:

- adaptador Python
- adaptador JS/TS
- adaptador HTML/CSS
- base futura para C++

### Fase 5: Operacion Agentic Sobre La IR

Entregables obligatorios:

- el agente debe leer la IR y no solo improvisar visualizaciones
- el agente debe usar el bridge con protocolo validado
- el agente debe poder reparar a partir de issues localizados

## Definition Of Done Para Cambios Grandes

Un cambio grande solo se considera terminado si:

- esta alineado con este protocolo
- actualiza este documento si cambia arquitectura o alcance
- deja trazabilidad en codigo
- deja verificacion ejecutable o comprobable
- no introduce estados mudos del agente
- no rompe la coherencia entre codigo, mapa y flujo

## Proxima Ejecucion Inmediata

La siguiente fase a implementar es:

### Fase 1: Contrato Formal

Debe producir:

- modelo canonico formal del sistema
- tipos de nodo
- tipos de arista
- tipos de issue
- protocolo de eventos del agente

Ese trabajo debe hacerse usando este archivo como base y sin salir del marco aqui definido.

## Cierre De Fase 1

La Fase 1 solo se considera cerrada cuando exista:

- contrato formal escrito
- vocabulario canonico estable
- semantica minima de nodos, aristas, issues y eventos
- criterio de aceptacion verificable para fases posteriores

Sin eso, ninguna implementacion de runtime, parser, visualizacion o agente se considera arquitectura estable.
