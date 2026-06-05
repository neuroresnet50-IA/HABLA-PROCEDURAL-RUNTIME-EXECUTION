import assert from "node:assert/strict";
import { CLOSURE_CERTIFICATE_TIMING_MS, buildClosureCertificate, buildClosureEvidenceText, buildClosureRepairPrompt, compactList, getClosureCertificateAutoPolicy, isSecurityClosureCertificate, isZombieClosureCertificate } from "./agentClosureCertificate.js";

const success = buildClosureCertificate({
  sessionId: "agent-ok",
  status: "completed",
  endedAt: "2026-05-18T06:00:00.000Z",
  projectName: "demo-cierre",
  controlPlane: {
    taskResult: {
      task_id: "TASK-OK",
      completed: true,
      validation_passed: true,
    },
    validation: {
      validation: {
        validation_passed: true,
        evidence: {
          found: ["frontend/index.html", "frontend/app.js", "frontend/styles.css", "LACE_LOG.md", "README.md"],
          missing: [],
        },
      },
    },
    checkpoint: {
      path: "runtime/checkpoints/final.json",
    },
  },
});

assert.equal(success.completed, true);
assert.equal(success.title, "Cierre definitivo certificado");
assert.equal(success.statusLabel, "Completado");
assert.equal(success.project, "demo-cierre");
assert.equal(success.taskId, "TASK-OK");
assert.equal(success.validationLabel, "validacion pasada");
assert.equal(success.missingLabel, "sin registros");
assert.equal(success.checkpointPath, "runtime/checkpoints/final.json");
assert.equal(success.foundLabel, "frontend/index.html, frontend/app.js, frontend/styles.css, LACE_LOG.md +1");

const failure = buildClosureCertificate({
  sessionId: "agent-fail",
  status: "failed",
  endedAt: "2026-05-18T06:05:00.000Z",
  projectSlug: "demo-fallo",
  errorMessage: "timeout del worker",
  controlPlane: {
    activeTaskId: "TASK-FAIL",
    taskResult: {
      validation_passed: false,
      blockers: ["worker excedio 900s", "sin cierre certificado"],
    },
    validation: {
      validation_passed: false,
      evidence: {
        found: ["frontend/index.html"],
        missing: ["frontend/app.js", "frontend/styles.css"],
      },
    },
  },
});

assert.equal(failure.completed, false);
assert.equal(failure.title, "Cierre no certificado");
assert.equal(failure.statusLabel, "Fallido");
assert.equal(failure.project, "demo-fallo");
assert.equal(failure.taskId, "TASK-FAIL");
assert.equal(failure.validationLabel, "validacion pendiente o fallida");
assert.equal(failure.message, "timeout del worker");
assert.equal(failure.foundLabel, "frontend/index.html");
assert.equal(failure.missingLabel, "frontend/app.js, frontend/styles.css");
assert.equal(failure.blockerLabel, "worker excedio 900s, sin cierre certificado");

const failurePollingUpdate = buildClosureCertificate({
  sessionId: "agent-fail",
  status: "failed",
  updatedAt: "2026-05-18T06:05:30.000Z",
  projectSlug: "demo-fallo",
  errorMessage: "timeout del worker",
  controlPlane: {
    activeTaskId: "TASK-FAIL",
    taskResult: {
      validation_passed: false,
      blockers: ["worker excedio 900s", "sin cierre certificado"],
    },
    validation: {
      validation_passed: false,
      evidence: {
        found: ["frontend/index.html"],
        missing: ["frontend/app.js", "frontend/styles.css"],
      },
    },
  },
});

assert.equal(failurePollingUpdate.key, failure.key);
assert.equal(CLOSURE_CERTIFICATE_TIMING_MS.autonomousRepair, 30000);

const evidenceText = buildClosureEvidenceText(failure);
assert.match(evidenceText, /Certificado del runtime/);
assert.match(evidenceText, /Proyecto: demo-fallo/);
assert.match(evidenceText, /Project slug: demo-fallo/);
assert.match(evidenceText, /Evidencia encontrada: frontend\/index\.html/);
assert.match(evidenceText, /Evidencia faltante: frontend\/app\.js, frontend\/styles\.css/);
assert.match(evidenceText, /Bloqueo: worker excedio 900s, sin cierre certificado/);

const repairPrompt = buildClosureRepairPrompt(failure);
assert.match(repairPrompt, /REPARACION_CONTROLADA_DE_CIERRE_RUNTIME/);
assert.match(repairPrompt, /No declares completed=true/);
assert.match(repairPrompt, /Evidencia resumida del certificado/);
assert.match(repairPrompt, /Tarea final: TASK-FAIL/);


const zombie = buildClosureCertificate({
  sessionId: "agent-zombie",
  status: "stopped",
  endedAt: "2026-06-03T18:45:00.000Z",
  projectSlug: "continuity-mixed-pf-010",
  errorMessage: "La UI tenia una sesion viva, pero el backend ya no tiene worker activo.",
  controlPlane: {
    activeTaskId: "RUNTIME-20260603184509-001",
    taskResult: {
      validation_passed: false,
      blockers: [],
    },
    validation: {
      validation_passed: false,
      evidence: { found: [], missing: [] },
    },
  },
});

assert.equal(isZombieClosureCertificate(zombie), true);
assert.deepEqual(getClosureCertificateAutoPolicy(success, { autonomousMode: true }), {
  action: "dismiss",
  delayMs: CLOSURE_CERTIFICATE_TIMING_MS.successDismiss,
  tone: "success",
  message: "Cierre certificado: se cerrara automaticamente para liberar la pantalla.",
});
assert.deepEqual(getClosureCertificateAutoPolicy(failure, { autonomousMode: true }), {
  action: "repair",
  delayMs: CLOSURE_CERTIFICATE_TIMING_MS.autonomousRepair,
  tone: "repair",
  message: "Modo autonomo: si nadie interviene en 30 segundos, el certificado enviara la evidencia al agente reparador y liberara la pantalla.",
});
assert.deepEqual(getClosureCertificateAutoPolicy(failure, { autonomousMode: false }), {
  action: "minimize",
  delayMs: CLOSURE_CERTIFICATE_TIMING_MS.failureMinimize,
  tone: "failure",
  message: "Cierre no certificado: se minimizara automaticamente para dejar pasar la siguiente tarea.",
});
assert.deepEqual(getClosureCertificateAutoPolicy(zombie, { autonomousMode: true }), {
  action: "repair",
  delayMs: CLOSURE_CERTIFICATE_TIMING_MS.autonomousRepair,
  tone: "repair",
  message: "Modo autonomo: si nadie interviene en 30 segundos, el certificado enviara la evidencia al agente reparador y liberara la pantalla.",
});
assert.equal(getClosureCertificateAutoPolicy(zombie, { autonomousMode: false }).action, "minimize");

const cyberlaceBlocked = buildClosureCertificate({
  sessionId: "agent-security",
  status: "blocked",
  endedAt: "2026-06-05T17:59:00.000Z",
  projectSlug: "demo-cyberlace",
  errorCode: "cyberlace_document_blocked",
  errorMessage: "PELIGRO: accion financiera insegura negada por CyberLACE. Continuar solo con P_safe.",
  controlPlane: {
    activeTaskId: "SECURITY-001",
    taskResult: {
      validation_passed: false,
      blockers: ["CyberLACE QUARANTINE", "prompt original sigue bloqueado"],
    },
    validation: {
      validation_passed: false,
      evidence: { found: [], missing: [] },
    },
  },
});

assert.equal(isSecurityClosureCertificate(cyberlaceBlocked), true);
assert.deepEqual(getClosureCertificateAutoPolicy(cyberlaceBlocked, { autonomousMode: true }), {
  action: "minimize",
  delayMs: CLOSURE_CERTIFICATE_TIMING_MS.failureMinimize,
  tone: "failure",
  message: "CyberLACE ya bloqueo esta orden por seguridad: no se reenviara al reparador para evitar un bucle. Se minimizara y continuara por P_safe.",
});

assert.equal(buildClosureCertificate({ status: "running" }), null);
assert.equal(compactList(["a", "b", "c", "d", "e"], 3), "a, b, c +2");

console.log("agentClosureCertificate tests passed");
