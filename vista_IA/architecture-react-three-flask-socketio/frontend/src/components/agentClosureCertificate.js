export const CLOSED_AGENT_STATUSES = new Set(["completed", "failed", "stopped", "blocked"]);

export const CLOSURE_CERTIFICATE_TIMING_MS = Object.freeze({
  successDismiss: 120000,
  failureMinimize: 180000,
  autonomousRepair: 240000,
});


export function formatAgentStatus(status) {
  return {
    queued: "En cola",
    preparing: "Preparando",
    starting: "Arrancando",
    running: "Ejecutando",
    completed: "Completado",
    failed: "Fallido",
    stopped: "Detenido",
    blocked: "Bloqueado",
  }[status] || "Listo";
}

function getProgressLabel(session) {
  return String(session?.progressLabel || "").trim() || "Esperando instrucciones";
}

export function compactList(items, limit = 4) {
  const values = (items || []).map((item) => String(item || "").trim()).filter(Boolean);
  if (!values.length) return "sin registros";
  if (values.length <= limit) return values.join(", ");
  return `${values.slice(0, limit).join(", ")} +${values.length - limit}`;
}

function certificateField(value, fallback = "sin registros") {
  const clean = String(value || "").trim();
  return clean || fallback;
}

function certificateList(values, label) {
  if (Array.isArray(values)) {
    const cleanValues = values.map((item) => String(item || "").trim()).filter(Boolean);
    return cleanValues.length ? cleanValues.join(", ") : "sin registros";
  }
  return certificateField(label);
}

function redactRepairText(value) {
  return String(value || "")
    .replace(/\b(copiar|copy|clonar|duplicar|extraer|exportar|transportar|exponer|reconstruir|procesar)\b/gi, "[accion_restringida]")
    .replace(/\b(secret|secreto|token|password|contrase(?:n|ñ)a|cvv|pin|pan|tarjeta|cuenta bancaria)\b/gi, "[dato_sensible]")
    .replace(/\[(?:REDACTED|redacted)[^\]]*\]/g, "[redactado]");
}

export function buildClosureEvidenceText(certificate) {
  if (!certificate) return "";
  return [
    "Certificado del runtime",
    certificateField(certificate.title, "Cierre sin titulo"),
    certificateField(certificate.message, "sin mensaje"),
    "",
    `Estado: ${certificateField(certificate.statusLabel)}`,
    `Proyecto: ${certificateField(certificate.project)}`,
    `Project slug: ${certificateField(certificate.projectSlug || certificate.project)}`,
    `Tarea final: ${certificateField(certificate.taskId)}`,
    `Validacion: ${certificateField(certificate.validationLabel)}`,
    `Evidencia encontrada: ${certificateList(certificate.foundEvidence, certificate.foundLabel)}`,
    `Evidencia faltante: ${certificateList(certificate.missingEvidence, certificate.missingLabel)}`,
    `Checkpoint: ${certificateField(certificate.checkpointPath, "sin checkpoint final registrado")}`,
    `Bloqueo: ${certificateList(certificate.blockers, certificate.blockerLabel)}`,
  ].join("\n");
}

export function buildClosureRepairPrompt(certificate) {
  const evidence = redactRepairText(buildClosureEvidenceText(certificate));
  if (!evidence) return "";
  return [
    "REPARACION_CONTROLADA_DE_CIERRE_RUNTIME",
    "",
    "Objetivo:",
    "Diagnosticar y reparar el cierre bloqueado usando solo evidencia real del runtime. No declares completed=true si falta validator OK, scanner OK, sandbox OK, integridad limpia o checkpoint persistido.",
    "",
    "Reglas:",
    "- Lee el estado persistido del proyecto, task_queue, task_history, failures, checkpoints y artifacts.",
    "- Repara solo bloqueos verificables y seguros.",
    "- Si el proyecto esta bloqueado por integrity/scanner/sandbox/LACE, deja el bloqueo claro y crea tareas de reparacion acotadas.",
    "- No borres evidencia historica ni fuerces cierre.",
    "- Al final reporta archivos modificados, validaciones ejecutadas, evidencia encontrada, evidencia faltante y siguiente recomendacion.",
    "",
    "Evidencia resumida del certificado:",
    evidence,
  ].join("\n");
}

export function isZombieClosureCertificate(certificate) {
  if (!certificate || certificate.completed) return false;
  const haystack = [
    certificate.title,
    certificate.message,
    certificate.statusLabel,
    certificate.validationLabel,
    certificate.blockerLabel,
    ...(Array.isArray(certificate.blockers) ? certificate.blockers : []),
  ].map((item) => String(item || "").toLowerCase()).join(" ");
  return (
    haystack.includes("backend ya no tiene worker activo")
    || haystack.includes("pid=null")
    || haystack.includes("runtime session reported running")
    || haystack.includes("runtime_zombie")
    || haystack.includes("zombie")
  );
}

export function getClosureCertificateAutoPolicy(certificate, { autonomousMode = false } = {}) {
  if (!certificate) return null;
  if (certificate.completed) {
    return {
      action: "dismiss",
      delayMs: CLOSURE_CERTIFICATE_TIMING_MS.successDismiss,
      tone: "success",
      message: "Cierre certificado: se cerrara automaticamente para liberar la pantalla.",
    };
  }
  if (autonomousMode && isZombieClosureCertificate(certificate)) {
    return {
      action: "repair",
      delayMs: CLOSURE_CERTIFICATE_TIMING_MS.autonomousRepair,
      tone: "repair",
      message: "Modo autonomo: si nadie interviene, el certificado enviara la evidencia al agente reparador.",
    };
  }
  return {
    action: "minimize",
    delayMs: CLOSURE_CERTIFICATE_TIMING_MS.failureMinimize,
    tone: "failure",
    message: "Cierre no certificado: se minimizara automaticamente para dejar pasar la siguiente tarea.",
  };
}

export function buildClosureCertificate(session) {
  if (!session || !CLOSED_AGENT_STATUSES.has(session.status)) return null;
  const controlPlane = session.controlPlane || {};
  const taskResult = controlPlane.taskResult || {};
  const validation = controlPlane.validation || {};
  const validationBody = validation.validation || validation;
  const evidence = validationBody.evidence || {};
  const checkpoint = controlPlane.checkpoint || {};
  const blockers = Array.isArray(taskResult.blockers) ? taskResult.blockers : [];
  const hasValidationSignal = taskResult.validation_passed != null || validationBody.validation_passed != null;
  const validationPassed = hasValidationSignal
    ? taskResult.validation_passed === true || validationBody.validation_passed === true
    : session.status === "completed";
  const completed = session.status === "completed" && taskResult.completed !== false && validationPassed && !session.errorCode;
  const missing = evidence.missing || [];
  const found = evidence.found || [];
  const message = completed
    ? "Cierre definitivo certificado: la cola termino, la evidencia existe en disco y la validacion asociada paso."
    : (session.errorMessage || blockers.join("; ") || getProgressLabel(session) || "La sesion cerro sin certificado de completitud.");

  return {
    key: [
      session.sessionId,
      session.status,
      session.endedAt || session.updatedAt,
      taskResult.task_id || controlPlane.activeTaskId || "",
      String(validationPassed),
      session.errorCode || "",
    ].join("|"),
    completed,
    title: completed ? "Cierre definitivo certificado" : "Cierre no certificado",
    message,
    statusLabel: formatAgentStatus(session.status),
    project: session.projectName || session.projectSlug || "sin proyecto",
    projectSlug: session.projectSlug || session.projectName || "",
    taskId: taskResult.task_id || controlPlane.activeTaskId || "sin tarea final",
    validationLabel: validationPassed ? "validacion pasada" : "validacion pendiente o fallida",
    checkpointPath: checkpoint.path || checkpoint.checkpoint_key || "",
    foundEvidence: found,
    missingEvidence: missing,
    blockers,
    foundLabel: compactList(found),
    missingLabel: compactList(missing),
    blockerLabel: compactList(blockers),
  };
}


function queueHasNoActiveWork(status) {
  const counts = status?.queue_counts || {};
  const active = Number(counts.running || 0) + Number(counts.pending || 0) + Number(counts.blocked || 0);
  const total = Number(status?.tasks_total || 0);
  return total > 0 && active === 0;
}

export function buildRuntimeClosureCertificate(status, project = {}) {
  if (!status || !queueHasNoActiveWork(status)) return null;
  const latestHistory = status.latest_history || {};
  const taskResult = latestHistory.result || {};
  const blockers = Array.isArray(taskResult.blockers) ? taskResult.blockers : [];
  const validationRan = Array.isArray(taskResult.validation_ran) ? taskResult.validation_ran : [];
  const completed = taskResult.completed === true && taskResult.validation_passed === true && blockers.length === 0;
  if (!completed) return null;

  const taskId = taskResult.task_id || status.current_task_id || "sin tarea final";
  const projectLabel = project.projectName || project.name || status.project_id || project.projectSlug || "sin proyecto";
  const found = [
    ...(Array.isArray(taskResult.files_created) ? taskResult.files_created : []),
    ...(Array.isArray(taskResult.files_modified) ? taskResult.files_modified : []),
  ];
  const missing = Array.isArray(status.expected_files_missing) ? status.expected_files_missing : [];

  return {
    key: ["runtime", status.project_id || project.projectSlug || "project", taskId, latestHistory.recorded_at || "", "passed"].join("|"),
    completed: true,
    title: "Cierre definitivo certificado",
    message: "Cierre definitivo certificado desde runtime persistido: la cola no tiene trabajo activo y la ultima validacion registrada paso.",
    statusLabel: "Completado",
    project: projectLabel,
    projectSlug: status.project_id || project.projectSlug || project.slug || projectLabel,
    taskId,
    validationLabel: validationRan.length ? "validacion pasada" : "validacion pasada sin comandos listados",
    checkpointPath: status.latest_checkpoint || "",
    foundEvidence: found.length ? found : status.expected_files_found,
    missingEvidence: missing,
    blockers,
    foundLabel: compactList(found.length ? found : status.expected_files_found),
    missingLabel: compactList(missing),
    blockerLabel: compactList(blockers),
  };
}
