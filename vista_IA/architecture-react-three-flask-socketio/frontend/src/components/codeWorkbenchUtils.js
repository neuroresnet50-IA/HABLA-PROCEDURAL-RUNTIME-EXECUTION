export const EMPTY_LOCK = {
  locked: false,
  reason: "idle",
  message: "Proyecto sin agente activo: edicion humana habilitada.",
  projectStatus: "idle",
  currentTaskId: null,
};
export const HABLA_OBSERVER_LOGO_SRC = "/assets/img/HABLA_Observer_IA_ojo_random_giro_guino_parpadeo.gif";

export const PREFERRED_FILES = [
  "frontend/app.js",
  "frontend/index.html",
  "src/main.js",
  "src/crm.js",
  "src/erp.js",
  "src/analytics.js",
  "README.md",
];

export const ACTIVE_RUNTIME_STATUSES = new Set(["queued", "preparing", "starting", "running"]);
export const LIVE_WRITER_INTERVAL_MS = 8;
export const LIVE_WRITER_TARGET_FRAMES = 80;
export const LIVE_WRITER_MIN_CHARS_PER_FRAME = 24;
export const LIVE_WRITER_DONE_DELAY_MS = 220;
export const CODE_SCANNER_TICK_MS = 10;
export const CODE_SCANNER_MAX_LINE_TICKS = 3;
export const CODE_SCANNER_VISUAL_FILE_LIMIT = 12;
export const CODE_SCANNER_VISUAL_LINE_LIMIT = 900;
export const CODE_SCANNER_WATCHDOG_MS = 45000;
export const CODE_SCANNER_CHAR_WIDTH_PX = 7.8;
export const CODE_SCANNER_LINE_HEIGHT_PX = 20.15;
export const CODE_SCANNER_SCROLL_MARGIN_ROWS = 4;
export const CODE_SCANNER_FOCUS_DELAY_MS = 80;
export const INTEGRITY_MARKER_LIMIT = 220;
export const INTEGRITY_REPORT_REFRESH_MS = 12000;
export const FINAL_SEQUENCE_UNLOCK_RETRIES = 14;
export const FINAL_SEQUENCE_UNLOCK_DELAY_MS = 650;

export const FINAL_SEQUENCE_OPS = new Set([
  "session_complete",
  "session_completed",
  "session_completed_with_warnings",
  "session_blocked",
  "session_failed",
  "session_stopped",
]);
export const FINAL_SEQUENCE_TERMINAL_STATUSES = new Set(["completed", "idle", "blocked", "failed", "stopped"]);

export function buildApiUrl(socketUrl, path) {
  return `${String(socketUrl || "").replace(/\/$/, "")}${path}`;
}

export function sortProjects(projects) {
  return [...(projects || [])].sort((left, right) => {
    const rightDate = Date.parse(right.updatedAt || right.createdAt || "") || 0;
    const leftDate = Date.parse(left.updatedAt || left.createdAt || "") || 0;
    if (rightDate !== leftDate) return rightDate - leftDate;
    return String(right.slug || "").localeCompare(String(left.slug || ""));
  });
}

export function chooseInitialFile(files) {
  if (!files?.length) return "";
  for (const preferredPath of PREFERRED_FILES) {
    const match = files.find((file) => file.path === preferredPath);
    if (match) return match.path;
  }
  return files[0].path;
}

export function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatClock(value) {
  if (!value) return "sin fecha";
  try {
    return new Intl.DateTimeFormat("es", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(value));
  } catch {
    return "actualizado";
  }
}

export function fileGlyph(path) {
  const extension = String(path || "").split(".").pop()?.toLowerCase();
  if (extension === "js" || extension === "jsx") return "JS";
  if (extension === "json") return "{}";
  if (extension === "html") return "<>";
  if (extension === "css") return "#";
  if (extension === "md") return "MD";
  if (extension === "py") return "PY";
  return "--";
}

export function statusLabel(lock) {
  if (lock?.locked) return "solo lectura";
  return "editable";
}

export function isRuntimeActive(lock) {
  const projectStatus = String(lock?.projectStatus || "").toLowerCase();
  return Boolean(lock?.locked || ACTIVE_RUNTIME_STATUSES.has(projectStatus));
}

export function fileSignature(entry) {
  if (!entry?.path) return "";
  return `${entry.modifiedAt || ""}:${entry.size || 0}`;
}

export function newestFileEntry(entries) {
  return [...(entries || [])].sort((left, right) => {
    const rightDate = Date.parse(right.modifiedAt || "") || 0;
    const leftDate = Date.parse(left.modifiedAt || "") || 0;
    if (rightDate !== leftDate) return rightDate - leftDate;
    return String(right.path || "").localeCompare(String(left.path || ""));
  })[0] || null;
}

export function orderedFinalFiles(entries) {
  return [...(entries || [])].sort((left, right) => {
    const leftDate = Date.parse(left.modifiedAt || "") || 0;
    const rightDate = Date.parse(right.modifiedAt || "") || 0;
    if (leftDate !== rightDate) return leftDate - rightDate;
    return String(left.path || "").localeCompare(String(right.path || ""));
  });
}

export function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function workspaceTargetFromPath(rawPath, fallbackProject = "") {
  const normalizedPath = String(rawPath || "").replace(/\\/g, "/").replace(/^\/+/, "");
  const workspaceMatch = normalizedPath.match(/(?:^|\/)workspace\/projects\/([^/]+)\/(.+)$/);
  if (workspaceMatch) {
    return {
      projectId: workspaceMatch[1],
      path: workspaceMatch[2],
    };
  }
  if (fallbackProject && normalizedPath && !normalizedPath.startsWith("workspace/") && !normalizedPath.startsWith("analysis/")) {
    return {
      projectId: fallbackProject,
      path: normalizedPath,
    };
  }
  return null;
}

export function normalizeWorkbenchRelativePath(rawPath) {
  const normalizedPath = String(rawPath || "").replace(/\\/g, "/").replace(/^\/+/, "");
  const workspaceMatch = normalizedPath.match(/(?:^|\/)workspace\/projects\/[^/]+\/(.+)$/);
  return workspaceMatch ? workspaceMatch[1] : normalizedPath;
}

export function integrityFindingClass(finding) {
  const type = String(finding?.type || "");
  if (type === "file_deleted") return "is-deleted";
  if (type === "untracked_file") return "is-untracked";
  if (type.startsWith("char_")) return "is-char";
  return "is-file";
}

export function integrityFindingLabel(finding) {
  const type = String(finding?.type || "external_file_change");
  if (type === "file_deleted") return "archivo eliminado";
  if (type === "untracked_file") return "archivo no registrado";
  if (type.startsWith("char_")) return "caracter alterado";
  return "cambio externo";
}

export function integrityFindingToTarget(finding, fallbackProject = "") {
  const path = normalizeWorkbenchRelativePath(finding?.path || finding?.focusPath || "");
  if (!path || !fallbackProject) return null;
  const line = Math.max(1, Number(finding?.line || 1) || 1);
  const type = String(finding?.type || "external_file_change");
  const label = integrityFindingLabel(finding);
  return {
    projectId: fallbackProject,
    path,
    line,
    message: finding?.message || `Observer detecto ${label}.`,
    code: type,
    severity: "error",
    hint: "Cambio externo no registrado contra la baseline sellada. Revisa la evidencia antes de aceptar baseline.",
    evidence: {
      source: "integrity",
      finding,
    },
    source: "integrity",
  };
}

export function lineRange(content, line) {
  const targetLine = Math.max(1, Number(line || 1));
  let start = 0;
  let currentLine = 1;
  while (currentLine < targetLine && start < content.length) {
    const nextBreak = content.indexOf("\n", start);
    if (nextBreak === -1) return [content.length, content.length];
    start = nextBreak + 1;
    currentLine += 1;
  }
  const endBreak = content.indexOf("\n", start);
  return [start, endBreak === -1 ? content.length : endBreak];
}

export function paneLabel(pane) {
  return {
    explorer: "Explorer",
    problems: "Problems",
    runtime: "Runtime",
    tests: "Tests",
  }[pane] || "Explorer";
}

export function buildRepairPrompt(target, extraInstruction = "") {
  const line = Math.max(1, Number(target?.line || 1) || 1);
  const isIntegrityFinding = target?.source === "integrity";
  return [
    isIntegrityFinding
      ? "Repara este hallazgo de integridad dentro del proyecto existente. No aceptes baseline ni ocultes la evidencia."
      : "Repara este hallazgo visual dentro del proyecto existente. No crees un proyecto nuevo.",
    "",
    `Proyecto: ${target?.projectId || ""}`,
    `Archivo: ${target?.path || ""}`,
    `Linea reportada: ${line}`,
    `Severidad: ${target?.severity || "warning"}`,
    `Codigo del hallazgo: ${target?.code || "visual_issue"}`,
    `Mensaje: ${target?.message || "Hallazgo visual seleccionado desde el editor."}`,
    target?.hint ? `Hint: ${target.hint}` : "",
    "",
    "Instrucciones obligatorias:",
    "- Inspecciona el archivo indicado alrededor de la linea reportada y los archivos relacionados.",
    isIntegrityFinding
      ? "- Corrige/restaura el contenido corrupto usando la evidencia y la baseline; no marques el cambio como valido sin autorizacion humana."
      : "- Corrige la causa real del punto rojo, no solo el texto del aviso.",
    "- Si es una desconexion del mapa o del flujo, conecta el algoritmo/dependencia con evidencia real en disco.",
    "- Mantén el cambio acotado al proyecto y al problema seleccionado.",
    "- Ejecuta validaciones concretas relacionadas con los archivos tocados.",
    "- Deja en el resultado los archivos modificados, validaciones ejecutadas y si el punto rojo deberia desaparecer al reauditar.",
    "",
    extraInstruction ? `Instruccion humana adicional: ${extraInstruction}` : "Instruccion humana adicional: repara este error en esta linea y deja evidencia de validacion.",
  ].filter(Boolean).join("\n");
}

export function buildRepairStructureLabel(target) {
  if (!target) return "estructura seleccionada";
  const line = Math.max(1, Number(target.line || 1) || 1);
  const code = target.code ? ` · ${target.code}` : "";
  return `${target.path || "archivo"}:${line}${code}`;
}
