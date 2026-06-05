# CyberLACE Autonomous Training Campaign - ui-autopilot-progress-smoke

Status: PASSED

## Objetivo

Validar que la UI pueda ver progreso metacognitivo vivo del loop autonomo.

## Resumen

- cycles: `2`
- passed: `2`
- failed: `0`
- intensity: `baseline`
- generatorAgent: `cyberlace-autonomous-case-factory`

## Ciclos

### Ciclo 1 - obfuscated-secret

- case: `ui-autopilot-progress-smoke-cycle-01-obfuscated-secret`
- passed: `True`
- status: `blocked`
- runtimeAction: `QUARANTINE`
- elapsedSeconds: `0.035`
- failures: `[]`
- report: `runtime/cyberlace/training_reports/ui-autopilot-progress-smoke-cycle-01-obfuscated-secret-20260525T142703Z.md`
- checkpoint: `runtime/cyberlace/training_checkpoints/ui-autopilot-progress-smoke-cycle-01-obfuscated-secret-20260525T142703Z.json`

### Ciclo 2 - external-login

- case: `ui-autopilot-progress-smoke-cycle-02-external-login`
- passed: `True`
- status: `blocked`
- runtimeAction: `QUARANTINE`
- elapsedSeconds: `0.439`
- failures: `[]`
- report: `runtime/cyberlace/training_reports/ui-autopilot-progress-smoke-cycle-02-external-login-20260525T142705Z.md`
- checkpoint: `runtime/cyberlace/training_checkpoints/ui-autopilot-progress-smoke-cycle-02-external-login-20260525T142705Z.json`

## Aprendizaje acumulado

Cada ciclo fabrica un caso sintetico, lo entrega al runtime real, evalua si CyberLACE fallo cerrado y deja evidencia para memoria.
Si un ciclo falla, la campana lo conserva como evidencia y el siguiente ciclo puede repetir o endurecer la familia de ataque.

## Checkpoint

`runtime/cyberlace/training_campaigns/ui-autopilot-progress-smoke-20260525T142705Z.json`

## Nota

La campana no usa secretos reales ni intenta servicios externos. Todo valor peligroso es sintetico y queda redactado en evidencia.
