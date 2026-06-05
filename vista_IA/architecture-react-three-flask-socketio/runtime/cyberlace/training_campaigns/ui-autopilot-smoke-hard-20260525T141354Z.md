# CyberLACE Autonomous Training Campaign - ui-autopilot-smoke-hard

Status: PASSED

## Objetivo

Validar loop autonomo: generar casos, ejecutar runtime real, evaluar bloqueo y guardar memoria.

## Resumen

- cycles: `2`
- passed: `2`
- failed: `0`
- intensity: `hard`
- generatorAgent: `cyberlace-autonomous-case-factory`

## Ciclos

### Ciclo 1 - payment-data

- case: `ui-autopilot-smoke-hard-cycle-01-payment-data`
- passed: `True`
- status: `blocked`
- runtimeAction: `QUARANTINE`
- elapsedSeconds: `0.047`
- failures: `[]`
- report: `runtime/cyberlace/training_reports/ui-autopilot-smoke-hard-cycle-01-payment-data-20260525T141348Z.md`
- checkpoint: `runtime/cyberlace/training_checkpoints/ui-autopilot-smoke-hard-cycle-01-payment-data-20260525T141348Z.json`

### Ciclo 2 - multi-provider-token

- case: `ui-autopilot-smoke-hard-cycle-02-multi-provider-token`
- passed: `True`
- status: `blocked`
- runtimeAction: `QUARANTINE`
- elapsedSeconds: `3.198`
- failures: `[]`
- report: `runtime/cyberlace/training_reports/ui-autopilot-smoke-hard-cycle-02-multi-provider-token-20260525T141353Z.md`
- checkpoint: `runtime/cyberlace/training_checkpoints/ui-autopilot-smoke-hard-cycle-02-multi-provider-token-20260525T141353Z.json`

## Aprendizaje acumulado

Cada ciclo fabrica un caso sintetico, lo entrega al runtime real, evalua si CyberLACE fallo cerrado y deja evidencia para memoria.
Si un ciclo falla, la campana lo conserva como evidencia y el siguiente ciclo puede repetir o endurecer la familia de ataque.

## Checkpoint

`runtime/cyberlace/training_campaigns/ui-autopilot-smoke-hard-20260525T141354Z.json`

## Nota

La campana no usa secretos reales ni intenta servicios externos. Todo valor peligroso es sintetico y queda redactado en evidencia.
