export const CLOSED_AGENT_STATUSES = new Set(["completed", "failed", "stopped", "blocked"]);

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
    taskId: taskResult.task_id || controlPlane.activeTaskId || "sin tarea final",
    validationLabel: validationPassed ? "validacion pasada" : "validacion pendiente o fallida",
    checkpointPath: checkpoint.path || checkpoint.checkpoint_key || "",
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
    taskId,
    validationLabel: validationRan.length ? "validacion pasada" : "validacion pasada sin comandos listados",
    checkpointPath: status.latest_checkpoint || "",
    foundLabel: compactList(found.length ? found : status.expected_files_found),
    missingLabel: compactList(missing),
    blockerLabel: compactList(blockers),
  };
}
