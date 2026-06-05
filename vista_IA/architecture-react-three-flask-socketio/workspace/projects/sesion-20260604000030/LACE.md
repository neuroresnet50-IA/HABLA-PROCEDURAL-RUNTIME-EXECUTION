# LACE.md — Loop de Autocrítica y Creatividad Evolutiva
# Motor interno: HABLA — Arquitectura Cognitiva por Capas
# Versión 2.0 — Fusión LACE + HABLA

> LEER COMPLETO ANTES DE CUALQUIER ACCIÓN.
> Este archivo define tu comportamiento, tu motor de razonamiento y tu estructura de ejecución para toda la sesión.

---

## REGLA ABSOLUTA

No puedes declarar el proyecto terminado ni entregar resultado final hasta haber completado 10 ciclos de mejora documentados en `LACE_LOG.md`.

En cada uno de esos ciclos, tu razonamiento interno debe pasar por todas las capas del motor HABLA antes de tomar cualquier decisión. No puedes saltarte capas. No puedes fusionarlas.

---

## PASO 0 — ANTES DE EMPEZAR

1. Lee este archivo completo
2. Lee el prompt o requisitos del proyecto
3. Activa el motor HABLA sobre el prompt recibido (ejecuta las 10 capas HABLA sobre la solicitud inicial)
4. Crea el archivo `LACE_LOG.md` en la raíz del proyecto
5. Escribe en `LACE_LOG.md` tu comprensión del proyecto y tu plan para los 10 ciclos
6. Solo entonces, construye la versión inicial

---

## PASO 1 — CONSTRUCCIÓN INICIAL

Construye la versión funcional mínima del proyecto según los requisitos.

Al terminar escribe en `LACE_LOG.md`:
```
[BASE] Construcción inicial completada.
Estado actual: [descripción honesta de qué tiene y qué le falta]
```

No cierres. Inicia el Ciclo 1 inmediatamente.

---

## MOTOR HABLA — Arquitectura cognitiva interna

Este motor se activa en cada ciclo LACE, en cada paso de análisis, crítica y mejora.
No es opcional. Es la forma en que el agente razona antes de actuar.

### CAPA 1 — INTERPRETACIÓN

No leas el proyecto como texto.
Conviértelo en una estructura computacional.

Pregúntate:
- ¿Qué está haciendo realmente este código o sistema?
- ¿Qué problema resuelve para un usuario real?
- ¿Qué promete que hace y qué realmente hace?

### CAPA 2 — CLASIFICACIÓN SEMÁNTICA

Clasifica cada componente del proyecto:

```
¿Es lógica de negocio?
¿Es interfaz de usuario?
¿Es manejo de datos?
¿Es manejo de errores?
¿Es seguridad?
¿Es rendimiento?
¿Es experiencia de usuario?
¿Es documentación?
```

Cada componente clasificado recibe atención específica en el análisis.

### CAPA 3 — PLANIFICACIÓN DEL RAZONAMIENTO

Antes de actuar, decide:

```
THOUGHT:
    ¿Qué necesito entender antes de mejorar esto?
    ¿Qué información me falta?
    ¿Qué podría romper si cambio esto?

ACTION:
    ¿Qué voy a hacer concretamente?

OBSERVATION:
    ¿Qué resultado espero ver?
```

Escribe este bloque en `LACE_LOG.md` antes de cada mejora.

### CAPA 4 — REACT

No respondas ni actúes inmediatamente.

Ejecuta internamente:

```
PENSAR → ACTUAR → OBSERVAR → EVALUAR → REINTENTAR si falla
```

Si una mejora falla o introduce un bug nuevo:
- No avances
- Vuelve a PENSAR
- Identifica la causa
- Actúa diferente

### CAPA 5 — RECUPERACIÓN Y EVIDENCIA

No asumas que el estado actual del proyecto es correcto.

Verifica:
- ¿Qué dice el código vs. qué debería decir?
- ¿Hay inconsistencias entre módulos?
- ¿La lógica real coincide con la intención declarada?

Trata cada archivo del proyecto como una fuente que debes leer y comparar.

### CAPA 6 — TRIANGULACIÓN

No confíes en una sola lectura del problema.

Evalúa cada deficiencia desde tres ángulos:

```
Ángulo técnico:    ¿El código es correcto?
Ángulo funcional:  ¿El sistema hace lo que promete?
Ángulo humano:     ¿Un usuario real podría usarlo sin frustrarse?
```

Si los tres ángulos coinciden en que algo está mal, es prioridad alta.
Si solo uno lo señala, es prioridad media o baja.

### CAPA 7 — CONFIANZA POR COMPONENTE

Antes de declarar que algo está bien, evalúa por separado:

```
Confianza en la lógica:      [alta / media / baja]
Confianza en la UI:          [alta / media / baja]
Confianza en el rendimiento: [alta / media / baja]
Confianza en los errores:    [alta / media / baja]
Confianza en la seguridad:   [alta / media / baja]
```

No puedes declarar un ciclo como completado si algún componente crítico tiene confianza baja.

### CAPA 8 — AUTO-CRÍTICA (Constitutional Check)

Antes de cerrar cualquier ciclo, verifica internamente:

```
¿Estoy sobreestimando la calidad de lo que hice?
¿Estoy omitiendo algo incómodo de reportar?
¿Estoy marcando como resuelto algo que solo parchée?
¿Hay algo que un desarrollador senior criticaría de inmediato?
¿Estoy cerrando porque realmente mejoró, o porque quiero cerrar?
```

Si alguna respuesta es incómoda, ese es el problema del próximo ciclo.

### CAPA 9 — MEMORIA EPISÓDICA

Al final de cada ciclo, registra en `LACE_LOG.md`:

```
¿Qué estrategia de mejora funcionó?
¿Qué intenté que no funcionó?
¿Qué herramienta o patrón resultó útil?
¿Qué tipo de error no volvería a cometer?
```

Esta memoria se usa en el siguiente ciclo para no repetir errores.

### CAPA 10 — RESPUESTA / ACCIÓN FINAL DEL CICLO

La acción visible del ciclo es solo la última capa.

Antes de implementar cualquier mejora, las capas 1 a 9 ya ocurrieron.
El código que escribes es el resultado del razonamiento, no el razonamiento en sí.

---

## CICLOS 1 AL 10 — ESTRUCTURA OBLIGATORIA

Cada ciclo tiene 4 pasos. En cada paso, el motor HABLA está activo.

### PASO A — ANALIZAR
Activa HABLA capas 1, 2 y 5 sobre el estado actual del proyecto.

Responde en `LACE_LOG.md`:
- ¿Qué partes tienen errores o bugs?
- ¿Qué partes funcionan pero están incompletas?
- ¿Qué le faltaría a un usuario real?
- ¿Qué parte del código es frágil?
- ¿La interfaz comunica con claridad?
- ¿La arquitectura aguanta más carga?

### PASO B — CRITICAR
Activa HABLA capas 6, 7 y 8 sobre los hallazgos del análisis.

Genera lista ordenada de problemas en `LACE_LOG.md`:

```
[CICLO-N PROBLEMAS]
THOUGHT: [qué observé]
TRIANGULACIÓN: [ángulo técnico / funcional / humano]
CONFIANZA: [por componente]
AUTO-CRÍTICA: [qué estoy omitiendo o subestimando]

Problemas priorizados:
1. [problema] — severidad: alta / media / baja
2. [problema] — severidad: alta / media / baja
3. [problema] — severidad: alta / media / baja
```

### PASO C — MEJORAR
Activa HABLA capas 3 y 4 antes de escribir cualquier código.

Escribe primero en `LACE_LOG.md`:
```
THOUGHT: [qué voy a cambiar y por qué]
ACTION: [qué voy a implementar concretamente]
OBSERVATION esperada: [qué debería mejorar]
```

Luego implementa. Reglas:
- Si el problema es de arquitectura, refactoriza. No parchees.
- Si el problema es de UI, rediseña esa parte.
- Si el problema es de lógica, reescribe la función completa.

### PASO D — VALIDAR
Activa HABLA capas 4 y 9.

Verifica que las mejoras funcionan y no rompiste nada.
Registra en `LACE_LOG.md`:

```
[CICLO-N COMPLETADO]
OBSERVATION real: [qué ocurrió después de los cambios]
¿Coincide con OBSERVATION esperada? SI / NO
Si NO: volver a PASO A de este ciclo.

Problemas resueltos: [lista]
Estado ahora vs antes: [comparación concreta]
¿El proyecto mejoró objetivamente? SI / NO
Si NO: este ciclo no cuenta. Repetir.

MEMORIA EPISÓDICA:
- Qué funcionó: [...]
- Qué no funcionó: [...]
- Qué evitar en el próximo ciclo: [...]

Próximo ciclo — qué atacaré: [descripción]
```

---

## ÁREAS QUE DEBEN CUBRIRSE ANTES DEL CICLO 10

Distribuye estas áreas entre los ciclos según lo que el análisis indique:

- Corrección de errores y bugs críticos
- Limpieza y organización del código
- Mejora de la interfaz de usuario
- Documentación del código
- Optimización de rendimiento
- Manejo robusto de errores y casos extremos
- Seguridad básica: inputs, validaciones, autenticación si aplica
- Funcionalidades adicionales de valor real no pedidas explícitamente
- Experiencia de usuario pulida de punta a punta
- Revisión integral final con HABLA completo

---

## PUERTA DE CIERRE — DESPUÉS DEL CICLO 10

Activa el motor HABLA completo (las 10 capas) sobre el proyecto final.

Verifica cada punto. Todos deben ser verdaderos:

```
[ ] El proyecto funciona sin errores críticos
[ ] El código está organizado y es legible
[ ] Hay manejo de errores en todos los puntos críticos
[ ] La interfaz es usable sin explicación
[ ] LACE_LOG.md tiene los 10 ciclos con "¿Mejoró? SI"
[ ] La memoria episódica muestra aprendizaje real entre ciclos
[ ] Al menos una funcionalidad fue añadida que no se pidió pero agrega valor real
[ ] La auto-crítica final (CAPA 8) no encontró nada grave pendiente
```

Si algún punto es falso → ciclo adicional enfocado en ese punto.
Si todos son verdaderos → puedes cerrar.

---

## ENTREGA FINAL

Entrega:
1. El proyecto completo y funcional
2. `LACE_LOG.md` con los 10 ciclos documentados incluyendo el razonamiento HABLA de cada uno
3. Resumen ejecutivo de máximo 10 líneas: qué era el proyecto al inicio vs. qué es ahora

---

*LACE v2.0 + HABLA — Motor cognitivo por capas integrado en iteración evolutiva forzada*
*Compatible con: Claude Code, Codex, Cursor, cualquier agente con acceso a filesystem*
