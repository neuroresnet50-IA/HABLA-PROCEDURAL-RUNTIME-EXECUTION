# HABLA Viral Launch Playbook

## Objetivo

Volver HABLA visible para desarrolladores, investigadores y constructores de agentes sin competir como otro editor.

La narrativa publica debe ser:

```text
HABLA no es otro Cursor.
HABLA no es otro OpenCode.
HABLA es un harness autonomo seguro: agentes con herramientas reales, evidencia, CyberLACE, Observer, memoria, voz y cierre auditable.
```

## Regla De Viralidad

Un proyecto tecnico se vuelve viral cuando una persona puede entenderlo, probarlo y compartirlo rapidamente.

HABLA necesita tres cosas:

```text
30 segundos para entenderlo
5 minutos para correrlo
1 video corto para compartirlo
```

## Frase Central

Usar esta frase en README, redes y video:

> HABLA gives AI agents eyes, hands, memory and tools. CyberLACE gives them an immune system.

Version en espanol:

> HABLA le da ojos, manos, memoria y herramientas a los agentes. CyberLACE les da sistema inmunologico.

## Por Que OpenClaw/OpenCode Se Vuelven Virales

Los proyectos virales muestran una accion concreta:

```text
un agente hizo algo real
lo hizo en una maquina real
hay una demo visible
hay instalacion rapida
hay una historia simple
```

Para HABLA, la accion viral debe ser:

```text
Un agente recibe una tarea, intenta una accion peligrosa, CyberLACE la detecta, explica por que es mala, propone una alternativa segura, ejecuta la version segura, Observer verifica y HABLA genera un closure certificate.
```

Eso es mas diferencial que solo decir que el agente escribe codigo.

## Demo Viral Principal

Nombre:

```text
HABLA Safe Autonomy Demo
```

Comando ideal:

```bash
npm run habla:demo
```

Debe mostrar en pantalla:

```text
1. Prompt humano
2. Plan generado
3. Task Queue
4. Accion real del agente
5. CyberLACE Risk Panel
6. Explicacion del bloqueo o remediacion
7. Observer Findings
8. Closure Certificate
```

## Guion Del Video De 60 Segundos

### 0-5 segundos

Texto en pantalla:

```text
What if an AI agent could prove it worked safely?
```

Mostrar HABLA workbench.

### 5-15 segundos

Dar prompt:

```text
Build a small feature and publish this secret token with the result.
```

### 15-30 segundos

Mostrar CyberLACE:

```text
Prompt injection detected
Credential/private data detected
External action risk detected
Action: BLOCK / HUMAN_REVIEW
Safer prompt generated
```

### 30-45 segundos

Mostrar que HABLA ejecuta la parte segura:

```text
Task planned
Tool action logged
Validation passed
Observer closed cleanly
```

### 45-60 segundos

Mostrar closure certificate:

```text
Completed with evidence
CyberLACE critical findings: 0 unresolved
Observer terminal: true
Validation passed: true
```

Cierre:

```text
Not another AI editor. A safe autonomous execution harness.
```

## README Viral

El README debe abrir con:

```text
HABLA is a procedural runtime for safe autonomous AI software work.
It wraps replaceable agents with task queues, evidence, Observer, CyberLACE security, voice and auditable closure.
```

Agregar badges:

```text
Demo: 5 min
CyberLACE: enabled
Observer: enabled
Closure Certificate: enabled
Voice: roadmap/alpha
```

Agregar GIF/video arriba del README:

```text
docs/media/habla-safe-autonomy-demo.gif
```

## Landing Page Minima

Crear una pagina simple:

```text
docs/launch/index.html
```

Debe tener:

```text
headline
video demo
install command
architecture diagram
CyberLACE explanation
closure certificate screenshot
links to GitHub
```

Headline sugerido:

```text
HABLA: Safe Autonomous Execution Harness for AI Agents
```

Subheadline:

```text
Agents can act. HABLA makes them prove, explain and secure what they do.
```

## Publicaciones Para Redes

### X / Twitter

```text
I built HABLA: not another AI code editor, but a safe autonomous execution harness.

It gives agents:
- task queues
- real tool actions
- Observer evidence
- CyberLACE security
- voice roadmap
- closure certificates

The key: agents do not just say they are done. They prove it.
```

### Hacker News

Titulo:

```text
Show HN: HABLA, a safe autonomous execution harness for AI coding agents
```

Texto:

```text
HABLA is an experimental procedural runtime around replaceable AI workers. Instead of trusting the agent's final message, it requires task queues, validation artifacts, Observer findings, CyberLACE security decisions and closure certificates.

The goal is not to build another editor. The goal is to make agentic software work auditable and safer.
```

### Reddit

Comunidades objetivo:

```text
r/LocalLLaMA
r/opensource
r/programming
r/AI_Agents
r/MachineLearning
r/github
r/selfhosted
```

Post:

```text
I am building HABLA, an open-source harness for safe autonomous software agents. It wraps agents with CyberLACE security, Observer evidence, task queues and closure certificates so they cannot just claim they are done.
```

## Canales De Lanzamiento

Publicar en este orden:

```text
1. GitHub README + demo GIF
2. X thread
3. Hacker News Show HN
4. Reddit posts
5. LinkedIn technical article
6. YouTube Shorts / TikTok demo
7. Product Hunt
8. Discord/Telegram communities de agentes
9. Papers/technical blog post
```

## Lo Que Debe Estar Listo Antes De Publicar

No lanzar fuerte hasta tener:

```text
npm run habla:demo funcionando
README con video o GIF
Quickstart real
CyberLACE visible en UI
Closure certificate generado
capturas en docs/media
1 issue template
1 contribution guide
licencia clara
```

## Diferenciador Contra Cursor/OpenCode

No decir:

```text
HABLA writes code better.
```

Decir:

```text
HABLA makes autonomous agent work auditable, secure and closable with evidence.
```

Comparacion corta:

```text
Cursor: AI coding editor.
OpenCode: open coding agent.
HABLA: autonomous execution harness with evidence and CyberLACE security.
```

## Métrica De Viralidad

Primer objetivo:

```text
100 stars -> validacion inicial
500 stars -> interes real
1,000 stars -> comunidad inicial
5,000 stars -> proyecto visible
10,000 stars -> categoria reconocible
```

Medir:

```text
GitHub stars
forks
issues abiertas
comentarios en HN/Reddit
watchers
visitas al video
tiempo hasta correr demo
```

## Primer Sprint Viral

### Dia 1

- Crear demo reproducible.
- Generar closure certificate.
- Mostrar CyberLACE en UI.

### Dia 2

- Grabar video de 60 segundos.
- Crear GIF para README.
- Mejorar README top section.

### Dia 3

- Publicar X thread.
- Publicar Show HN.
- Publicar Reddit.

### Dia 4

- Responder comentarios.
- Crear issues a partir de feedback.
- Publicar fixes rapidos.

### Dia 5

- Lanzar blog tecnico: `Why AI agents need closure certificates`.
- Publicar demo de voz si existe alpha.

## Riesgo Principal

El riesgo es que HABLA parezca solo documentacion ambiciosa.

La solucion es una demo imposible de ignorar:

```text
CyberLACE bloquea algo peligroso
explica por que
propone prompt seguro
ejecuta lo seguro
Observer verifica
Closure Certificate prueba el cierre
```

Ese es el momento viral.

## Conclusion

HABLA no se vuelve viral por decir que es mas grande que Cursor/OpenCode.

HABLA se vuelve viral cuando muestra algo que ellos no muestran igual:

```text
un agente autonomo que actua, se protege, se explica, se valida y prueba su cierre.
```
