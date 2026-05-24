import assert from "node:assert/strict";
import { buildClosureCertificate, compactList } from "./agentClosureCertificate.js";

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

assert.equal(buildClosureCertificate({ status: "running" }), null);
assert.equal(compactList(["a", "b", "c", "d", "e"], 3), "a, b, c +2");

console.log("agentClosureCertificate tests passed");
