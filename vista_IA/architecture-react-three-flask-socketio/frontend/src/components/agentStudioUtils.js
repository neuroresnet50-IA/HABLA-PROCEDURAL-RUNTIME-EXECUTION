export const DEFAULT_AGENT_RUNTIME_MODE = "build";
export const RUNTIME_MODE_PRESETS = [
  {
    value: "smoke",
    label: "Facil",
    detail: "script, prueba rapida o cambio puntual",
  },
  {
    value: "build",
    label: "Medio",
    detail: "producto pequeno con validacion normal",
  },
  {
    value: "medium",
    label: "Dificil",
    detail: "varios modulos, mas tiempo y mas verificacion",
  },
  {
    value: "long-run",
    label: "Extradificil",
    detail: "proyecto grande con LACE y ciclos largos",
  },
];
export const ACTIVE_AGENT_STATUSES = new Set(["queued", "preparing", "starting", "running"]);

export function humanizeAgentError(error) {
  const message = String(error?.message || error || "request_failed");
  if (message === "agent_socket_disconnected") return "socket del agente desconectado";
  if (message === "agent_ack_timeout") return "la instancia no respondio a tiempo";
  if (message === "missing_requirement") return "faltan instrucciones para el agente";
  if (message === "missing_project_name") return "falta el nombre del proyecto";
  if (message === "missing_existing_project") return "selecciona un proyecto existente antes de continuar";
  if (message === "missing_session_id") return "falta el id de la sesion";
  if (message === "session_not_found") return "la sesion ya no existe";
  return message;
}

export function humanizeRuntimeResetError(error) {
  const message = String(error?.message || error || "request_failed");
  if (message === "runtime_reset_endpoint_missing") return "el backend activo no cargo todavia el endpoint de restablecimiento; reinicia una vez la aplicacion";
  if (message === "runtime_reset_failed") return "no fue posible programar el restablecimiento";
  if (message === "blanqueo_confirmation_required") return "el protocolo exige confirmacion humana adicional para blanqueo total en este modo";
  return message;
}

export function normalizeShortConfirmation(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function buildGeneratedProjectName() {
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  return `sesion-${stamp}`;
}

export function looksLikeProjectName(value) {
  const trimmed = String(value || "").trim();
  const slug = slugify(trimmed);
  if (!slug) return false;
  if (trimmed.length > 80) return false;
  if (/[.?!]$/.test(trimmed)) return false;
  return slug.length >= 3;
}

export function parseInlineProjectPrompt(value) {
  const source = String(value || "").trim();
  if (!source) return { projectName: "", requirement: "" };

  const lines = source.split(/\r?\n/);
  const firstIndex = lines.findIndex((line) => line.trim());
  if (firstIndex === -1) return { projectName: "", requirement: source };

  const projectCandidate = lines[firstIndex].trim();
  const markerIndex = lines.findIndex((line, index) => index > firstIndex && line.trim());
  if (markerIndex === -1) return { projectName: "", requirement: source };

  const marker = lines[markerIndex].trim().toLowerCase();
  if (!looksLikeProjectName(projectCandidate)) return { projectName: "", requirement: source };
  if (!/^(y\s+este\s+prompt|este\s+prompt|prompt)/i.test(marker)) return { projectName: "", requirement: source };

  const requirement = lines.slice(markerIndex + 1).join("\n").trim();
  if (!requirement) return { projectName: "", requirement: source };

  return {
    projectName: projectCandidate,
    requirement,
  };
}

export function getProgressPercent(session) {
  const raw = Number(session?.progressPercent ?? 0);
  if (!Number.isFinite(raw)) return 0;
  return Math.max(0, Math.min(100, Math.round(raw)));
}

export function getProgressLabel(session) {
  return String(session?.progressLabel || "").trim() || "Esperando instrucciones";
}

export function describeVisualState(visualState) {
  if (!visualState) return "";
  if (visualState.message) {
    return visualState.phase ? `${visualState.phase}: ${visualState.message}` : visualState.message;
  }
  if (visualState.focusPath) {
    return `Foco visual en ${visualState.focusPath}`;
  }
  if (visualState.op) {
    return `Evento visual: ${visualState.op}`;
  }
  return "";
}

export function booleanLabel(value) {
  if (value === true) return "si";
  if (value === false) return "no";
  return "desconocido";
}

export function getLaceProgress(session) {
  const required = Number(session?.laceRequiredCycles || 0);
  const completed = Number(session?.laceCompletedCycles || 0);
  if (!required) return "LACE inactivo";
  return `${completed}/${required} ciclos`;
}

export function formatDuration(seconds) {
  const value = Math.max(0, Math.round(Number(seconds || 0)));
  const minutes = Math.floor(value / 60);
  const rest = value % 60;
  if (minutes < 60) return `${minutes}:${String(rest).padStart(2, "0")} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}:${String(minutes % 60).padStart(2, "0")}:${String(rest).padStart(2, "0")} h`;
}

export function parseTimestamp(value) {
  const parsed = Date.parse(value || "");
  return Number.isFinite(parsed) ? parsed : null;
}

export function getSessionElapsedSeconds(session, nowMs = Date.now()) {
  if (!session) return 0;
  const start = parseTimestamp(session.startedAt) || parseTimestamp(session.createdAt) || nowMs;
  const end = ACTIVE_AGENT_STATUSES.has(session.status) ? nowMs : parseTimestamp(session.endedAt) || nowMs;
  return Math.max(0, Math.floor((end - start) / 1000));
}

export function isAgentActive(session) {
  return Boolean(session && ACTIVE_AGENT_STATUSES.has(session.status));
}

export function getLiveStage(session) {
  if (!session) return "idle";
  if (session.status === "failed" || session.status === "stopped") return "danger";
  if (session.status === "completed") return "final";
  const progress = getProgressPercent(session);
  if (session.status === "starting" || progress < 18) return "initial";
  if (progress >= 82) return "final";
  return "middle";
}

export function getLiveStageLabel(stage) {
  return {
    idle: "Sin pulso activo",
    initial: "Etapa inicial",
    middle: "Etapa media",
    final: "Etapa final",
    danger: "Atencion requerida",
  }[stage] || "Pulso runtime";
}

export function sameReviewerScope(event, session, projectSlug) {
  if (!event) return false;
  if (session?.sessionId && event.session_id === session.sessionId) return true;
  if (projectSlug && event.project_id === projectSlug) return true;
  return false;
}

export function mergeReviewerEvents(current, incoming) {
  const rows = [...current];
  const seen = new Set(rows.map((event) => `${event.timestamp}|${event.type}|${event.message}`));
  for (const event of incoming || []) {
    const key = `${event.timestamp}|${event.type}|${event.message}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push(event);
  }
  rows.sort((left, right) => String(left.timestamp || "").localeCompare(String(right.timestamp || "")));
  return rows.slice(-500);
}

export function mergeHumanAlignmentReviewList(current, review) {
  if (!review?.id) return current;
  return [...current.filter((item) => item?.id !== review.id), review];
}

export function flattenDetectedStack(detectedStack) {
  if (!detectedStack || typeof detectedStack !== "object") return [];
  return Object.entries(detectedStack).flatMap(([category, values]) => (
    Array.isArray(values)
      ? values.map((value) => ({ category, value }))
      : []
  ));
}

export function emitWithAck(socket, event, payload, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    if (!socket?.connected) {
      reject(new Error("agent_socket_disconnected"));
      return;
    }

    const timer = window.setTimeout(() => {
      reject(new Error("agent_ack_timeout"));
    }, timeoutMs);

    socket.emit(event, payload, (response) => {
      window.clearTimeout(timer);
      if (response?.ok === false) {
        reject(new Error(response.error || "request_failed"));
        return;
      }
      resolve(response || { ok: true });
    });
  });
}
