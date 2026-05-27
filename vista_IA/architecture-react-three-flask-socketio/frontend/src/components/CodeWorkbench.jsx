import { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";
import CodeWorkbenchActions from "./CodeWorkbenchActions.jsx";
import CodeWorkbenchActivityBar from "./CodeWorkbenchActivityBar.jsx";
import CodeWorkbenchAgentChat from "./CodeWorkbenchAgentChat.jsx";
import CodeWorkbenchEditorHeader from "./CodeWorkbenchEditorHeader.jsx";
import CodeWorkbenchEditorOverlays from "./CodeWorkbenchEditorOverlays.jsx";
import CodeWorkbenchGutter from "./CodeWorkbenchGutter.jsx";
import CodeWorkbenchRepairBubble from "./CodeWorkbenchRepairBubble.jsx";
import CodeWorkbenchSandboxModal from "./CodeWorkbenchSandboxModal.jsx";
import CodeWorkbenchSidebar from "./CodeWorkbenchSidebar.jsx";
import CodeWorkbenchTerminal from "./CodeWorkbenchTerminal.jsx";
import CodeWorkbenchTextarea from "./CodeWorkbenchTextarea.jsx";
import CodeWorkbenchTopMenu from "./CodeWorkbenchTopMenu.jsx";

import {
  CODE_SCANNER_CHAR_WIDTH_PX,
  CODE_SCANNER_FOCUS_DELAY_MS,
  CODE_SCANNER_LINE_HEIGHT_PX,
  CODE_SCANNER_MAX_LINE_TICKS,
  CODE_SCANNER_SCROLL_MARGIN_ROWS,
  CODE_SCANNER_TICK_MS,
  CODE_SCANNER_VISUAL_FILE_LIMIT,
  CODE_SCANNER_VISUAL_LINE_LIMIT,
  CODE_SCANNER_WATCHDOG_MS,
  EMPTY_LOCK,
  FINAL_SEQUENCE_OPS,
  FINAL_SEQUENCE_TERMINAL_STATUSES,
  FINAL_SEQUENCE_UNLOCK_DELAY_MS,
  FINAL_SEQUENCE_UNLOCK_RETRIES,
  INTEGRITY_MARKER_LIMIT,
  INTEGRITY_REPORT_REFRESH_MS,
  LIVE_WRITER_DONE_DELAY_MS,
  LIVE_WRITER_INTERVAL_MS,
  LIVE_WRITER_MIN_CHARS_PER_FRAME,
  LIVE_WRITER_TARGET_FRAMES,
  buildApiUrl,
  buildRepairPrompt,
  buildRepairStructureLabel,
  chooseInitialFile,
  fileSignature,
  integrityFindingClass,
  integrityFindingLabel,
  integrityFindingToTarget,
  isRuntimeActive,
  lineRange,
  newestFileEntry,
  normalizeWorkbenchRelativePath,
  orderedFinalFiles,
  sleep,
  sortProjects,
  statusLabel,
  workspaceTargetFromPath,
} from "./codeWorkbenchUtils.js";

function formatTruthAge(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value)) return "sin evidencia";
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${Math.round(value / 3600)}h ${Math.round((value % 3600) / 60)}m`;
}

function runtimeTruthLabel(truth) {
  const verdict = String(truth?.verdict || "unknown");
  if (verdict === "zombie") return "ZOMBIE: no hay agente vivo";
  if (verdict === "live") return "vivo: agente/worker detectado";
  if (verdict === "unverified_running") return "running sin verificar";
  if (verdict === "idle") return "idle verificable";
  return "sin diagnostico";
}

function runtimeTruthClass(truth) {
  const verdict = String(truth?.verdict || "unknown");
  if (verdict === "zombie") return "is-zombie";
  if (verdict === "live") return "is-live";
  if (verdict === "idle") return "is-idle";
  return "is-unverified";
}

export default function CodeWorkbench({ socketUrl, focusedProject, jumpTarget, expanded = false, onRepairPresenceStart }) {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState("");
  const [files, setFiles] = useState([]);
  const [selectedPath, setSelectedPath] = useState("");
  const [file, setFile] = useState(null);
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [lock, setLock] = useState(EMPTY_LOCK);
  const [activePane, setActivePane] = useState("explorer");
  const [fileFilter, setFileFilter] = useState("");
  const [problems, setProblems] = useState([]);
  const [loadingProblems, setLoadingProblems] = useState(false);
  const [targetLine, setTargetLine] = useState(null);
  const [jumpNotice, setJumpNotice] = useState("");
  const [activeIssueTarget, setActiveIssueTarget] = useState(null);
  const [repairOpen, setRepairOpen] = useState(false);
  const [repairInstruction, setRepairInstruction] = useState("Repara este error en esta linea y valida que el punto rojo desaparezca.");
  const [repairSending, setRepairSending] = useState(false);
  const [repairStatus, setRepairStatus] = useState("");
  const [repairProgress, setRepairProgress] = useState({
    active: false,
    percent: 0,
    label: "reparando codigo",
    detail: "",
    messages: [],
  });
  const [liveWriter, setLiveWriter] = useState({ active: false, path: "", message: "" });
  const [finalSequence, setFinalSequence] = useState({
    active: false,
    phase: "idle",
    index: 0,
    total: 0,
    path: "",
    message: "",
  });
  const [codeScanner, setCodeScanner] = useState({
    active: false,
    passed: null,
    percent: 0,
    fileIndex: 0,
    totalFiles: 0,
    path: "",
    line: 0,
    totalLines: 0,
    column: 0,
    visibleRow: 0,
    message: "",
    artifactPath: "",
  });
  const [sandbox, setSandbox] = useState({ status: "idle", running: false, url: "", port: null, technology: null, logs: [] });
  const [sandboxPreviewOpen, setSandboxPreviewOpen] = useState(false);
  const [sandboxBusy, setSandboxBusy] = useState(false);
  const [integrityReport, setIntegrityReport] = useState(null);
  const [integrityBusy, setIntegrityBusy] = useState(false);
  const [integrityActionStatus, setIntegrityActionStatus] = useState("");
  const [editorScrollTop, setEditorScrollTop] = useState(0);
  const [editorScrollLeft, setEditorScrollLeft] = useState(0);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState("Editor listo.");
  const [error, setError] = useState("");
  const [agentChatDraft, setAgentChatDraft] = useState("");
  const [agentChatMessages, setAgentChatMessages] = useState([]);
  const [agentChatEvents, setAgentChatEvents] = useState([]);
  const [agentChatSending, setAgentChatSending] = useState(false);
  const [agentChatOpen, setAgentChatOpen] = useState(true);
  const [agentChatPilot, setAgentChatPilot] = useState({ active: false, phase: "idle", label: "", progress: 0 });
  const [runtimeTruth, setRuntimeTruth] = useState(null);
  const [runtimeTruthBusy, setRuntimeTruthBusy] = useState(false);
  const [agentChangedPaths, setAgentChangedPaths] = useState(new Set());
  const [agentChangeTrace, setAgentChangeTrace] = useState({ active: false, path: "", line: null, message: "" });
  const [sidebarWidth, setSidebarWidth] = useState(340);
  const gutterRef = useRef(null);
  const editorRef = useRef(null);
  const writerTimerRef = useRef(null);
  const writerFrameRef = useRef(null);
  const writerDoneTimerRef = useRef(null);
  const writerResolveRef = useRef(null);
  const scannerTimerRef = useRef(null);
  const scannerWatchdogRef = useRef(null);
  const scannerFocusFrameRef = useRef(null);
  const scannerFocusTimerRef = useRef(null);
  const repairCompletionTimerRef = useRef(null);
  const selectedProjectRef = useRef("");
  const selectedPathRef = useRef("");
  const filesRef = useRef([]);
  const lockRef = useRef(EMPTY_LOCK);
  const dirtyRef = useRef(false);
  const draftRef = useRef("");
  const liveWriterRef = useRef(liveWriter);
  const finalSequenceRef = useRef(finalSequence);
  const finalSequenceRunningRef = useRef(false);
  const runtimeActiveProjectsRef = useRef(new Set());
  const finalSequenceCompletedProjectsRef = useRef(new Set());
  const codeScannerRef = useRef(codeScanner);
  const integrityScanInFlightRef = useRef(false);
  const lastIntegrityAutoScanKeyRef = useRef("");
  const lastIntegrityReportRefreshAtRef = useRef(0);
  const lastRuntimeTruthRefreshAtRef = useRef(0);
  const fileSignaturesByProjectRef = useRef(new Map());
  const lastAutoWriterKeyRef = useRef("");
  const skipNextAutoLoadRef = useRef("");
  const agentChatPilotTimersRef = useRef([]);
  const agentChatPilotActiveRef = useRef(false);
  const agentChangeTraceTimerRef = useRef(null);

  const sortedProjects = useMemo(() => sortProjects(projects), [projects]);
  const selectedProjectMeta = useMemo(
    () => projects.find((project) => project.slug === selectedProject) || null,
    [projects, selectedProject]
  );
  const selectedFileMeta = useMemo(
    () => files.find((entry) => entry.path === selectedPath) || null,
    [files, selectedPath]
  );
  const lineNumbers = useMemo(() => {
    const count = Math.max(1, draft.split("\n").length);
    return Array.from({ length: count }, (_, index) => index + 1);
  }, [draft]);
  const filteredFiles = useMemo(() => {
    const needle = fileFilter.trim().toLowerCase();
    if (!needle) return files;
    return files.filter((entry) => `${entry.path} ${entry.name}`.toLowerCase().includes(needle));
  }, [fileFilter, files]);
  const testFiles = useMemo(
    () => files.filter((entry) => entry.path.startsWith("tests/") || /\.test\./.test(entry.path) || /smoke/i.test(entry.path)),
    [files]
  );
  const integrityFindings = useMemo(
    () => (Array.isArray(integrityReport?.findings) ? integrityReport.findings : []),
    [integrityReport]
  );
  const visibleIntegrityFindings = useMemo(() => {
    const currentPath = normalizeWorkbenchRelativePath(selectedPath);
    if (!currentPath) return [];
    return integrityFindings
      .filter((finding) => normalizeWorkbenchRelativePath(finding.path || finding.focusPath) === currentPath)
      .slice(0, INTEGRITY_MARKER_LIMIT);
  }, [integrityFindings, selectedPath]);
  const visibleIntegrityLines = useMemo(() => {
    const lines = new Set();
    visibleIntegrityFindings.forEach((finding) => {
      lines.add(Math.max(1, Number(finding.line || 1) || 1));
    });
    return lines;
  }, [visibleIntegrityFindings]);
  const visibleIntegrityMarkers = useMemo(
    () => visibleIntegrityFindings.map((finding, index) => {
      const line = Math.max(1, Number(finding.line || 1) || 1);
      const column = Math.max(1, Number(finding.column || 1) || 1);
      const expectedText = String(finding.expectedText || "");
      const actualText = String(finding.actualText || "");
      const textLength = Math.max(expectedText.length, actualText.length, 1);
      const isCharacterFinding = String(finding.type || "").startsWith("char_");
      const markerWidth = isCharacterFinding
        ? Math.min(340, Math.max(CODE_SCANNER_CHAR_WIDTH_PX * textLength, CODE_SCANNER_CHAR_WIDTH_PX * 1.35))
        : Math.min(560, Math.max(180, CODE_SCANNER_CHAR_WIDTH_PX * textLength));
      return {
        id: `${finding.type || "integrity"}-${finding.path || selectedPath}-${line}-${column}-${index}`,
        className: integrityFindingClass(finding),
        label: integrityFindingLabel(finding),
        line,
        column,
        message: finding.message || "Cambio externo no registrado.",
        x: 16 + (column - 1) * CODE_SCANNER_CHAR_WIDTH_PX - editorScrollLeft,
        y: 14 + (line - 1) * CODE_SCANNER_LINE_HEIGHT_PX - editorScrollTop,
        width: markerWidth,
      };
    }),
    [editorScrollLeft, editorScrollTop, selectedPath, visibleIntegrityFindings]
  );
  const visibleAgentChangeMarker = useMemo(() => {
    if (!agentChangeTrace.active || normalizeWorkbenchRelativePath(agentChangeTrace.path) !== normalizeWorkbenchRelativePath(selectedPath)) return null;
    const line = Math.max(1, Number(agentChangeTrace.line || 1) || 1);
    return {
      line,
      y: 14 + (line - 1) * CODE_SCANNER_LINE_HEIGHT_PX - editorScrollTop,
      message: agentChangeTrace.message || "Cambio aplicado por agente.",
    };
  }, [agentChangeTrace, editorScrollTop, selectedPath]);
  const problemRows = useMemo(() => {
    const integrityRows = integrityFindings.map((finding, index) => {
      const target = integrityFindingToTarget(finding, selectedProject);
      const line = Math.max(1, Number(finding?.line || 1) || 1);
      const path = normalizeWorkbenchRelativePath(finding?.path || finding?.focusPath || "");
      const code = String(finding?.type || "external_file_change");
      return {
        id: `integrity-${code}-${path}-${line}-${Number(finding?.column || 0)}-${index}`,
        severity: "error",
        message: finding?.message || `Observer detecto ${integrityFindingLabel(finding)}.`,
        path,
        line,
        code,
        source: "integrity",
        target,
      };
    });
    const visualRows = problems.map((problem, index) => {
      const target = workspaceTargetFromPath(problem.path, selectedProject);
      const line = Math.max(1, Number(problem?.line || 1) || 1);
      return {
        id: `problem-${problem.code || "issue"}-${problem.path || "sin-ruta"}-${line}-${index}`,
        severity: problem.severity || "info",
        message: problem.message,
        path: problem.path || "",
        line: problem.line || null,
        code: problem.code,
        source: problem.source || "problems",
        target: target ? {
          ...target,
          line,
          message: problem.message,
          code: problem.code,
          severity: problem.severity,
          hint: problem.hint,
          evidence: problem.evidence,
          source: problem.source,
        } : null,
      };
    });
    return [...integrityRows, ...visualRows];
  }, [integrityFindings, problems, selectedProject]);
  const repairStructureLabel = buildRepairStructureLabel(activeIssueTarget);
  const repairProgressVisible = repairSending || repairProgress.active || repairProgress.percent > 0;
  const canSave = Boolean(selectedProject && selectedPath && dirty && !lock.locked && !liveWriter.active && !finalSequence.active && !codeScanner.active && !saving);

  function setVisibleIntegrityStatus(message) {
    const nextMessage = String(message || "");
    setIntegrityActionStatus(nextMessage);
    if (nextMessage) setStatus(nextMessage);
  }

  function integrityBlockedReason(actionLabel = "accion de integridad") {
    if (!selectedProject) return `Selecciona un proyecto antes de ejecutar ${actionLabel}.`;
    if (integrityBusy) return `Espera: ${actionLabel} ya esta en ejecucion.`;
    if (liveWriter.active) return "Espera a que termine la escritura en vivo antes de tocar integridad.";
    if (finalSequence.active) return "Espera a que termine el typewriter final antes de tocar integridad.";
    if (dirty) return "Guarda o recarga el archivo humano antes de tocar integridad.";
    if (lock.locked) return lock.message || "El runtime tiene un agente activo; espera o detenlo antes de tocar integridad.";
    return "";
  }

  function repairBlockedReason() {
    if (!activeIssueTarget) return "Selecciona una huella o hallazgo con Ver antes de lanzar el agente reparador.";
    if (repairSending) return "El agente reparador ya se esta lanzando.";
    if (lock.locked) return lock.message || "El runtime tiene un agente activo; espera antes de lanzar otro reparador.";
    if (dirty) return "Guarda o recarga tus cambios humanos antes de lanzar un agente reparador.";
    if (finalSequence.active) return "Espera a que termine el typewriter final antes de lanzar el reparador.";
    if (codeScanner.active) return "Espera a que termine el scanner final antes de lanzar el reparador.";
    return "";
  }

  function openRepairPanel() {
    if (!activeIssueTarget && integrityFindings.length) {
      focusIntegrityFinding(integrityFindings[0], { openRepair: true });
      return;
    }
    const blocker = !activeIssueTarget ? repairBlockedReason() : "";
    if (blocker) {
      setRepairStatus(blocker);
      setStatus(blocker);
      return;
    }
    setRepairOpen(true);
  }

  async function fetchJson(path, options = {}) {
    const response = await fetch(buildApiUrl(socketUrl, path), options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload?.ok === false) {
      const message = payload?.lock?.message || payload?.message || payload?.error || `request_failed_${response.status}`;
      const error = new Error(message);
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    return payload;
  }


  function makeAgentChatId(prefix = "chat") {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  function appendAgentChatMessage(message) {
    const text = String(message?.text || "").trim();
    if (!text) return;
    setAgentChatMessages((current) => [
      ...current.slice(-11),
      {
        id: message.id || makeAgentChatId(message.role || "message"),
        role: message.role || "assistant",
        text,
        at: message.at || new Date().toISOString(),
      },
    ]);
  }

  function classifyAgentEvent(payload = {}) {
    const op = String(payload.op || "").toLowerCase();
    const phase = String(payload.phase || payload.status || "").toLowerCase();
    const message = String(payload.message || "").toLowerCase();
    if (op.includes("sync_file") || op.includes("write") || message.includes("escrib")) return { kind: "change", label: "Aplicando cambio" };
    if (op.includes("complete") || phase.includes("complete")) return { kind: "done", label: "Completado" };
    if (op.includes("failed") || op.includes("blocked") || phase.includes("failed") || phase.includes("blocked")) return { kind: "blocked", label: "Bloqueado" };
    if (op.includes("tool") || op.includes("terminal") || message.includes("comando") || message.includes("tool")) return { kind: "tool", label: "Usando herramienta" };
    if (phase.includes("validation") || message.includes("valid")) return { kind: "validate", label: "Validando" };
    if (phase.includes("plan") || message.includes("plan")) return { kind: "think", label: "Thinking" };
    if (message.includes("read") || message.includes("leyendo") || message.includes("archivo")) return { kind: "read", label: "Leyendo" };
    if (message.includes("cod") || message.includes("patch") || message.includes("cambio")) return { kind: "code", label: "Codificando" };
    return { kind: "working", label: payload.phase ? `Bridge ${payload.phase}` : "Trabajando" };
  }

  function appendAgentChatEvent(payload = {}) {
    const message = String(payload.message || payload.relativePath || payload.focusPath || payload.op || "").trim();
    if (!message) return;
    const eventType = classifyAgentEvent(payload);
    const path = String(payload.relativePath || payload.focusPath || "").replace(/^\/+/, "");
    const idBase = `${payload.sessionId || "monitor"}:${payload.op || eventType.kind}:${path}:${message}`;
    setAgentChatEvents((current) => {
      if (current.some((item) => item.key === idBase)) return current;
      return [
        ...current.slice(-23),
        {
          id: makeAgentChatId(eventType.kind),
          key: idBase,
          kind: eventType.kind,
          label: eventType.label,
          message,
          path,
          at: new Date().toISOString(),
        },
      ];
    });
  }

  function firstChangedLine(previousContent, nextContent) {
    const previousLines = String(previousContent || "").split("\n");
    const nextLines = String(nextContent || "").split("\n");
    const total = Math.max(previousLines.length, nextLines.length, 1);
    for (let index = 0; index < total; index += 1) {
      if ((previousLines[index] || "") !== (nextLines[index] || "")) return index + 1;
    }
    return 1;
  }

  function markAgentChangedFile(path, message = "Cambio aplicado por agente.", line = 1) {
    const cleanPath = normalizeWorkbenchRelativePath(path);
    if (!cleanPath) return;
    const safeLine = Math.max(1, Number(line || 1) || 1);
    setAgentChangedPaths((current) => {
      const next = new Set(current);
      next.add(cleanPath);
      return next;
    });
    setAgentChangeTrace({ active: true, path: cleanPath, line: safeLine, message });
    if (agentChangeTraceTimerRef.current) window.clearTimeout(agentChangeTraceTimerRef.current);
    agentChangeTraceTimerRef.current = window.setTimeout(() => {
      setAgentChangeTrace((current) => ({ ...current, active: false }));
      agentChangeTraceTimerRef.current = null;
    }, 9000);
  }

  function clearAgentChat() {
    clearAgentChatPilotTimers();
    setAgentChatPilot({ active: false, phase: "idle", label: "", progress: 0 });
    setAgentChatMessages([]);
    setAgentChatEvents([]);
    setAgentChatDraft("");
  }

  function clearAgentChatPilotTimers() {
    agentChatPilotActiveRef.current = false;
    for (const timerId of agentChatPilotTimersRef.current || []) {
      window.clearTimeout(timerId);
    }
    agentChatPilotTimersRef.current = [];
  }

  function scheduleAgentChatPilot(delayMs, callback) {
    const timerId = window.setTimeout(() => {
      if (!agentChatPilotActiveRef.current) return;
      callback();
    }, delayMs);
    agentChatPilotTimersRef.current = [...agentChatPilotTimersRef.current, timerId];
  }

  function defaultDelegatedAgentPrompt() {
    const target = selectedPath ? `el archivo abierto ${selectedPath}` : `el proyecto ${selectedProject || "activo"}`;
    return `Monitor verde: revisa ${target}, el runtime, la cola, la sesion activa y dime en lenguaje natural que esta pasando y si hay bloqueo real.`;
  }

  function runVisibleAgentDelegation(promptText = "") {
    if (agentChatPilotActiveRef.current || agentChatSending) return;
    const visiblePrompt = String(promptText || agentChatDraft || defaultDelegatedAgentPrompt()).trim();
    if (!visiblePrompt) return;
    if (!selectedProject) {
      appendAgentChatMessage({ role: "assistant", text: "Selecciona un proyecto antes de delegar al agente ayudante." });
      return;
    }
    clearAgentChatPilotTimers();
    agentChatPilotActiveRef.current = true;
    setAgentChatOpen(true);
    setAgentChatDraft("");
    appendAgentChatEvent({ op: "monitor_cursor", message: "Monitor verde mueve el cursor al chat", phase: "tool" });
    setAgentChatPilot({ active: true, phase: "cursor", label: "Monitor moviendo mouse al chat", progress: 0 });

    scheduleAgentChatPilot(520, () => {
      appendAgentChatEvent({ op: "monitor_focus", message: "Monitor verde enfoca la caja de texto", phase: "tool" });
      setAgentChatPilot({ active: true, phase: "focus", label: "Monitor enfoca Preguntar", progress: 2 });
    });

    const typeStartMs = 860;
    const typeIntervalMs = Math.max(8, visiblePrompt.length > 180 ? 10 : 16);
    for (let index = 0; index < visiblePrompt.length; index += 1) {
      scheduleAgentChatPilot(typeStartMs + index * typeIntervalMs, () => {
        const nextText = visiblePrompt.slice(0, index + 1);
        setAgentChatDraft(nextText);
        setAgentChatPilot({
          active: true,
          phase: "type",
          label: "Monitor escribiendo en tiempo real",
          progress: Math.round(((index + 1) / visiblePrompt.length) * 88),
        });
      });
    }

    const submitAtMs = typeStartMs + visiblePrompt.length * typeIntervalMs + 520;
    scheduleAgentChatPilot(submitAtMs, () => {
      appendAgentChatEvent({ op: "monitor_submit", message: "Monitor verde oprime Preguntar", phase: "tool" });
      setAgentChatPilot({ active: true, phase: "submit", label: "Monitor oprime Preguntar", progress: 96 });
    });
    scheduleAgentChatPilot(submitAtMs + 420, () => {
      void handleAgentChatSubmit(null, {
        delegated: true,
        actor: "green-runtime-monitor",
        promptOverride: visiblePrompt,
      }).finally(() => {
        clearAgentChatPilotTimers();
        setAgentChatPilot({ active: false, phase: "idle", label: "", progress: 0 });
      });
    });
  }


  function clampSidebarWidth(value) {
    return Math.min(620, Math.max(260, Number(value) || 340));
  }

  function startSidebarResize(event) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = sidebarWidth;
    document.body.classList.add("is-workbench-resizing");
    function handleMove(moveEvent) {
      setSidebarWidth(clampSidebarWidth(startWidth + moveEvent.clientX - startX));
    }
    function handleDone() {
      document.body.classList.remove("is-workbench-resizing");
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleDone);
      window.removeEventListener("pointercancel", handleDone);
    }
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleDone);
    window.addEventListener("pointercancel", handleDone);
  }

  function handleSidebarResizeKey(event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 24 : -24;
    setSidebarWidth((current) => clampSidebarWidth(current + delta));
  }

  async function handleAgentChatSubmit(event, options = {}) {
    event?.preventDefault?.();
    const delegated = Boolean(options.delegated);
    const userPrompt = String(options.promptOverride ?? agentChatDraft).trim();
    if (!userPrompt) return;
    if (!selectedProject) {
      appendAgentChatMessage({ role: "assistant", text: "Selecciona un proyecto antes de consultar el monitor." });
      return;
    }

    appendAgentChatMessage({ role: delegated ? "delegate" : "user", text: userPrompt });
    appendAgentChatEvent({ op: delegated ? "monitor_auto_submit" : "monitor_submit", message: "Consultando runtime", phase: "monitor" });
    setAgentChatDraft("");
    setAgentChatSending(true);
    setError("");
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(selectedProject)}/runtime-monitor/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userPrompt,
          selectedPath,
          source: delegated ? "green_monitor_auto" : "green_monitor_manual",
        }),
      });
      appendAgentChatMessage({ role: "assistant", text: payload.answer || "Monitor verde no devolvio respuesta." });
      appendAgentChatEvent({
        op: "runtime_monitor_answer",
        message: payload.issues?.length ? payload.issues.join("; ") : "Monitor respondio con evidencia del runtime",
        phase: payload.issues?.length ? "blocked" : "complete",
      });
      setStatus("Monitor verde consulto el runtime sin lanzar worker.");
    } catch (chatError) {
      const message = chatError.message || "No fue posible consultar el monitor verde.";
      appendAgentChatMessage({ role: "assistant", text: message });
      appendAgentChatEvent({ op: "runtime_monitor_failed", message, status: "failed" });
      setError(message);
    } finally {
      setAgentChatSending(false);
    }
  }

  useEffect(() => () => clearAgentChatPilotTimers(), []);

  useEffect(() => {
    function handleExternalDelegation(event) {
      const detail = event?.detail || {};
      const targetProject = String(detail.projectSlug || detail.project || "").trim();
      if (targetProject && selectedProject && targetProject !== selectedProject) return;
      runVisibleAgentDelegation(detail.prompt || detail.requirement || detail.message || "");
    }
    window.addEventListener("code-workbench:delegate-agent-chat", handleExternalDelegation);
    return () => window.removeEventListener("code-workbench:delegate-agent-chat", handleExternalDelegation);
  }, [selectedProject, selectedPath, agentChatDraft, agentChatSending]);

  async function loadProjects({ silent = false } = {}) {
    if (!silent) {
      setLoadingProjects(true);
      setError("");
    }
    try {
      const payload = await fetchJson("/api/agent/projects");
      setProjects(payload.projects || []);
      if (!silent) setStatus("Proyectos del runtime cargados.");
    } catch (loadError) {
      if (!silent) setError(loadError.message || "No fue posible cargar proyectos.");
    } finally {
      if (!silent) setLoadingProjects(false);
    }
  }

  async function loadProjectFiles(projectId, { silent = false } = {}) {
    if (!projectId) return;
    if (!silent) {
      setLoadingFile(true);
      setError("");
    }
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/files`);
      const nextFiles = payload.files || [];
      const nextLock = payload.lock || EMPTY_LOCK;
      const changedFiles = rememberFileSignatures(projectId, nextFiles, { detect: silent });
      filesRef.current = nextFiles;
      lockRef.current = nextLock;
      if (isRuntimeActive(nextLock)) {
        runtimeActiveProjectsRef.current.add(projectId);
        finalSequenceCompletedProjectsRef.current.delete(projectId);
      }
      setFiles(nextFiles);
      setLock(nextLock);
      setSelectedPath((current) => {
        if (current && nextFiles.some((entry) => entry.path === current)) return current;
        return chooseInitialFile(nextFiles);
      });
      if (silent && isRuntimeActive(nextLock) && changedFiles.length && !finalSequenceRunningRef.current && !codeScannerRef.current.active) {
        const changedFile = newestFileEntry(changedFiles);
        if (changedFile) {
          await openLiveWriterFile(projectId, changedFile, `IA escribiendo ${changedFile.path}`);
        }
      }
      if (!silent) {
        setStatus(`${nextFiles.length} archivos visibles. Estado: ${statusLabel(nextLock)}.`);
      }
      return { changedFiles, files: nextFiles, lock: nextLock };
    } catch (loadError) {
      if (!silent) setError(loadError.message || "No fue posible cargar archivos.");
      return { changedFiles: [], files: [], lock: EMPTY_LOCK };
    } finally {
      if (!silent) setLoadingFile(false);
    }
  }

  function updateRepairProgress({ active = true, percent, minPercent, label, detail, message } = {}) {
    if (repairCompletionTimerRef.current) {
      window.clearTimeout(repairCompletionTimerRef.current);
      repairCompletionTimerRef.current = null;
    }
    setRepairProgress((current) => {
      const basePercent = Number.isFinite(Number(percent)) ? Number(percent) : current.percent;
      const nextPercent = Math.max(
        0,
        Math.min(99, Number.isFinite(Number(minPercent)) ? Math.max(basePercent, Number(minPercent)) : basePercent)
      );
      const nextMessages = message
        ? [{ id: `${Date.now()}-${current.messages.length}`, text: message }, ...current.messages].slice(0, 4)
        : current.messages;
      return {
        active,
        percent: nextPercent,
        label: label || current.label || "reparando codigo",
        detail: detail || current.detail,
        messages: nextMessages,
      };
    });
  }

  function finishRepairProgress(message, { failed = false } = {}) {
    if (repairCompletionTimerRef.current) {
      window.clearTimeout(repairCompletionTimerRef.current);
      repairCompletionTimerRef.current = null;
    }
    setRepairProgress((current) => ({
      active: false,
      percent: failed ? Math.max(current.percent, 1) : 100,
      label: failed ? "reparacion bloqueada" : "reparacion completada",
      detail: message || current.detail,
      messages: message
        ? [{ id: `${Date.now()}-${current.messages.length}`, text: message }, ...current.messages].slice(0, 4)
        : current.messages,
    }));
    repairCompletionTimerRef.current = window.setTimeout(() => {
      setRepairProgress({
        active: false,
        percent: 0,
        label: "reparando codigo",
        detail: "",
        messages: [],
      });
      repairCompletionTimerRef.current = null;
    }, 6500);
  }

  function stopLiveWriter(message = "") {
    if (writerTimerRef.current) {
      window.clearInterval(writerTimerRef.current);
      writerTimerRef.current = null;
    }
    if (writerDoneTimerRef.current) {
      window.clearTimeout(writerDoneTimerRef.current);
      writerDoneTimerRef.current = null;
    }
    if (writerResolveRef.current) {
      writerResolveRef.current(false);
      writerResolveRef.current = null;
    }
    if (writerFrameRef.current) {
      window.cancelAnimationFrame(writerFrameRef.current);
      writerFrameRef.current = null;
    }
    setLiveWriter((current) => {
      if (!current.active && !message) return current;
      return { active: false, path: current.path, message: message || current.message };
    });
  }

  function focusWriterAtStart() {
    const editor = editorRef.current;
    if (!editor) return;
    editor.focus();
    editor.setSelectionRange(0, 0);
    editor.scrollTop = 0;
    editor.scrollLeft = 0;
    setEditorScrollTop(0);
    setEditorScrollLeft(0);
    if (gutterRef.current) {
      gutterRef.current.scrollTop = 0;
    }
  }

  function scheduleWriterScroll({ keepAtTop = false } = {}) {
    if (!editorRef.current) return;
    if (writerFrameRef.current) {
      window.cancelAnimationFrame(writerFrameRef.current);
    }
    writerFrameRef.current = window.requestAnimationFrame(() => {
      const editor = editorRef.current;
      if (!editor) return;
      editor.scrollTop = keepAtTop ? 0 : editor.scrollHeight;
      setEditorScrollTop(editor.scrollTop);
      setEditorScrollLeft(editor.scrollLeft);
      if (gutterRef.current) {
        gutterRef.current.scrollTop = editor.scrollTop;
      }
      if (keepAtTop) {
        editor.focus();
        editor.setSelectionRange(0, 0);
      }
      writerFrameRef.current = null;
    });
  }

  function typewriteContent(nextContent, path, message = "", { forceFromStart = false, keepAtTop = false } = {}) {
    if (writerResolveRef.current) {
      writerResolveRef.current(false);
      writerResolveRef.current = null;
    }
    if (writerTimerRef.current) {
      window.clearInterval(writerTimerRef.current);
      writerTimerRef.current = null;
    }
    if (writerDoneTimerRef.current) {
      window.clearTimeout(writerDoneTimerRef.current);
      writerDoneTimerRef.current = null;
    }
    return new Promise((resolve) => {
      writerResolveRef.current = resolve;
      const fullContent = String(nextContent || "");
      const previous = forceFromStart ? "" : selectedPathRef.current === path ? draftRef.current : "";
      const maxPrefix = Math.min(previous.length, fullContent.length);
      let prefixLength = 0;
      while (prefixLength < maxPrefix && previous[prefixLength] === fullContent[prefixLength]) {
        prefixLength += 1;
      }
      let cursor = prefixLength;
      const total = fullContent.length;
      const step = Math.max(
        LIVE_WRITER_MIN_CHARS_PER_FRAME,
        Math.ceil(Math.max(1, total - prefixLength) / LIVE_WRITER_TARGET_FRAMES)
      );
      setDraft(fullContent.slice(0, cursor));
      if (keepAtTop) {
        setTargetLine(1);
        focusWriterAtStart();
      }
      setLiveWriter({
        active: true,
        path,
        message: message || `IA escribiendo ${path}`,
      });
      scheduleWriterScroll({ keepAtTop });
      if (cursor >= total) {
        writerDoneTimerRef.current = window.setTimeout(() => {
          writerDoneTimerRef.current = null;
          setLiveWriter({ active: false, path, message: `Writer completo: ${path}` });
          if (writerResolveRef.current) {
            writerResolveRef.current(true);
            writerResolveRef.current = null;
          }
        }, LIVE_WRITER_DONE_DELAY_MS);
        return;
      }
      writerTimerRef.current = window.setInterval(() => {
        cursor = Math.min(total, cursor + step);
        setDraft(fullContent.slice(0, cursor));
        scheduleWriterScroll({ keepAtTop });
        if (cursor >= total) {
          window.clearInterval(writerTimerRef.current);
          writerTimerRef.current = null;
          setDraft(fullContent);
          setLiveWriter({ active: false, path, message: `Writer completo: ${path}` });
          if (writerResolveRef.current) {
            writerResolveRef.current(true);
            writerResolveRef.current = null;
          }
        }
      }, LIVE_WRITER_INTERVAL_MS);
    });
  }

  async function loadProjectFile(projectId, path, { silent = false, preserveDirty = false, animate = false, writerMessage = "" } = {}) {
    if (!projectId || !path) return;
    if (preserveDirty && dirty) return;
    if (!silent) {
      setLoadingFile(true);
      setError("");
    }
    try {
      const payload = await fetchJson(
        `/api/projects/${encodeURIComponent(projectId)}/file?path=${encodeURIComponent(path)}`
      );
      const nextFile = payload.file || null;
      const nextContent = String(nextFile?.content || "");
      setFile(nextFile);
      if (animate && !dirty) {
        typewriteContent(nextContent, path, writerMessage);
      } else {
        setDraft(nextContent);
      }
      setDirty(false);
      setLock(payload.lock || EMPTY_LOCK);
      if (!silent) setStatus(`Archivo cargado: ${path}`);
      return nextFile;
    } catch (loadError) {
      if (!silent) setError(loadError.message || "No fue posible cargar el archivo.");
      return null;
    } finally {
      if (!silent) setLoadingFile(false);
    }
  }

  function stopCodeScanner(message = "") {
    if (scannerTimerRef.current) {
      window.clearInterval(scannerTimerRef.current);
      scannerTimerRef.current = null;
    }
    if (scannerWatchdogRef.current) {
      window.clearTimeout(scannerWatchdogRef.current);
      scannerWatchdogRef.current = null;
    }
    clearScannerFocusTimers();
    setCodeScanner((current) => ({
      ...current,
      active: false,
      message: message || current.message,
    }));
    if (message) setStatus(message);
  }

  function clearScannerFocusTimers() {
    if (scannerFocusFrameRef.current) {
      window.cancelAnimationFrame(scannerFocusFrameRef.current);
      scannerFocusFrameRef.current = null;
    }
    if (scannerFocusTimerRef.current) {
      window.clearTimeout(scannerFocusTimerRef.current);
      scannerFocusTimerRef.current = null;
    }
  }

  function focusScannerViewport({ line = 1 } = {}) {
    const targetLineNumber = Math.max(1, Number(line || 1) || 1);
    setSandboxPreviewOpen(false);
    setRepairOpen(false);
    setActivePane("explorer");
    setTargetLine(targetLineNumber);
    clearScannerFocusTimers();
    scannerFocusFrameRef.current = window.requestAnimationFrame(() => {
      scannerFocusFrameRef.current = null;
      scannerFocusTimerRef.current = window.setTimeout(() => {
        scannerFocusTimerRef.current = null;
        const editor = editorRef.current;
        const workbench = document.getElementById("code-workbench");
        const visualTarget = editor?.closest(".code-workbench-main") || workbench;
        visualTarget?.scrollIntoView({ behavior: "smooth", block: "start" });
        if (!editor) return;
        editor.scrollTop = 0;
        editor.scrollLeft = 0;
        setEditorScrollTop(0);
        setEditorScrollLeft(0);
        if (gutterRef.current) {
          gutterRef.current.scrollTop = 0;
        }
        const linesBeforeTarget = editor.value.split("\n").slice(0, targetLineNumber - 1);
        const caretPosition = linesBeforeTarget.length ? linesBeforeTarget.join("\n").length + 1 : 0;
        try {
          editor.focus({ preventScroll: true });
        } catch {
          editor.focus();
        }
        editor.setSelectionRange(caretPosition, caretPosition);
      }, CODE_SCANNER_FOCUS_DELAY_MS);
    });
  }

  function scrollEditorToLine(line) {
    const editor = editorRef.current;
    if (!editor || !line) return 0;
    const computed = window.getComputedStyle(editor);
    const parsedLineHeight = Number.parseFloat(computed.lineHeight);
    const lineHeight = Number.isFinite(parsedLineHeight) ? parsedLineHeight : CODE_SCANNER_LINE_HEIGHT_PX;
    const targetRow = Math.max(0, Math.max(1, line) - 1);
    const viewportRows = Math.max(1, Math.floor(Math.max(lineHeight, editor.clientHeight) / lineHeight));
    const marginRows = Math.min(
      CODE_SCANNER_SCROLL_MARGIN_ROWS,
      Math.max(1, Math.floor(viewportRows / 3))
    );
    const maxScrollTop = Math.max(0, editor.scrollHeight - editor.clientHeight);
    const targetTop = targetRow * lineHeight;
    let scrollTop = editor.scrollTop;
    const upperGuard = scrollTop + marginRows * lineHeight;
    const lowerGuard = scrollTop + Math.max(lineHeight, editor.clientHeight - (marginRows + 2) * lineHeight);
    if (targetTop < upperGuard) {
      scrollTop = Math.max(0, targetTop - marginRows * lineHeight);
    } else if (targetTop > lowerGuard) {
      const pinnedRow = Math.max(1, viewportRows - marginRows - 2);
      scrollTop = Math.min(maxScrollTop, Math.max(0, targetTop - pinnedRow * lineHeight));
    }
    editor.scrollTop = scrollTop;
    setEditorScrollTop(scrollTop);
    setEditorScrollLeft(editor.scrollLeft);
    if (gutterRef.current) {
      gutterRef.current.scrollTop = scrollTop;
    }
    return Math.max(0, (targetTop - scrollTop) / lineHeight);
  }

  function scanFileWithMagnifier(reportFile, content, fileIndex, totalFiles) {
    return new Promise((resolve) => {
      if (scannerTimerRef.current) {
        window.clearInterval(scannerTimerRef.current);
        scannerTimerRef.current = null;
      }
      const lines = String(content || "").split("\n").slice(0, CODE_SCANNER_VISUAL_LINE_LIMIT);
      const totalLines = Math.max(1, lines.length);
      let lineIndex = 0;
      let column = 0;
      scannerTimerRef.current = window.setInterval(() => {
        const line = lines[lineIndex] || "";
        const lineLength = Math.max(1, line.length);
        const charStep = Math.max(8, Math.ceil(lineLength / CODE_SCANNER_MAX_LINE_TICKS));
        column = Math.min(lineLength, column + charStep);
        const visibleRow = scrollEditorToLine(lineIndex + 1);
        const fileProgress = (lineIndex + column / lineLength) / totalLines;
        const percent = Math.min(100, ((fileIndex + fileProgress) / Math.max(1, totalFiles)) * 100);
        setTargetLine(lineIndex + 1);
        setCodeScanner((current) => ({
          ...current,
          active: true,
          passed: null,
          percent,
          fileIndex: fileIndex + 1,
          totalFiles,
          path: reportFile.path,
          line: lineIndex + 1,
          totalLines,
          column,
          visibleRow,
          message: `Scanner leyendo ${reportFile.path}`,
        }));
        if (column >= lineLength) {
          lineIndex += 1;
          column = 0;
        }
        if (lineIndex >= totalLines) {
          window.clearInterval(scannerTimerRef.current);
          scannerTimerRef.current = null;
          resolve(true);
        }
      }, CODE_SCANNER_TICK_MS);
    });
  }

  async function launchCodeScanner({ projectId = selectedProject, force = false } = {}) {
    const scannerProject = projectId || selectedProjectRef.current;
    if (!scannerProject || dirtyRef.current || (!force && (lockRef.current.locked || liveWriterRef.current.active || finalSequenceRef.current.active || codeScannerRef.current.active))) {
      if (codeScannerRef.current.active) {
        setStatus("Scanner final ya esta activo. Usa Detener scanner si quedo pegado.");
      }
      return false;
    }
    focusScannerViewport({ line: 1 });
    setError("");
    setStatus("Scanner final preparando lectura completa del workspace.");
    setCodeScanner({
      active: true,
      passed: null,
      percent: 0,
      fileIndex: 0,
      totalFiles: 0,
      path: "",
      line: 0,
      totalLines: 0,
      column: 0,
      visibleRow: 0,
      message: "Scanner final preparando reporte persistente.",
      artifactPath: "",
    });
    if (scannerWatchdogRef.current) {
      window.clearTimeout(scannerWatchdogRef.current);
    }
    scannerWatchdogRef.current = window.setTimeout(() => {
      scannerWatchdogRef.current = null;
      stopCodeScanner("Scanner final detenido por timeout visual; el reporte persistente puede revisarse en artefactos.");
      setCodeScanner((current) => ({ ...current, passed: false }));
    }, CODE_SCANNER_WATCHDOG_MS);
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(scannerProject)}/code-scanner`, {
        method: "POST",
      });
      const report = payload.report || {};
      const scannerFiles = Array.isArray(report.files) ? report.files : [];
      if (!scannerFiles.length) {
        throw new Error(report.validation?.blockers?.[0] || "scanner_without_files");
      }
      const visualScannerFiles = scannerFiles.slice(0, CODE_SCANNER_VISUAL_FILE_LIMIT);
      for (let index = 0; index < visualScannerFiles.length; index += 1) {
        const reportFile = visualScannerFiles[index];
        skipNextAutoLoadRef.current = `${scannerProject}:${reportFile.path}`;
        setSelectedProject(scannerProject);
        setSelectedPath(reportFile.path);
        setTargetLine(1);
        const loadedFile = await loadProjectFile(scannerProject, reportFile.path, { silent: true, preserveDirty: true });
        const content = String(loadedFile?.content || "");
        if (index === 0) {
          focusScannerViewport({ line: 1 });
          await sleep(CODE_SCANNER_FOCUS_DELAY_MS);
        }
        await scanFileWithMagnifier(reportFile, content, index, visualScannerFiles.length);
      }
      if (scannerWatchdogRef.current) {
        window.clearTimeout(scannerWatchdogRef.current);
        scannerWatchdogRef.current = null;
      }
      const passed = Boolean(report.validation?.passed);
      setCodeScanner((current) => ({
        ...current,
        active: false,
        passed,
        percent: 100,
        message: passed ? "Scanner final aprobado." : "Scanner final bloqueado.",
        artifactPath: payload.artifactPath || report.validation?.artifact || "",
      }));
      setStatus(
        passed
          ? `Scanner final aprobado: ${report.summary?.filesScanned || scannerFiles.length} archivo(s), ${report.summary?.charactersScanned || 0} caracter(es). Animacion acotada a ${visualScannerFiles.length} archivo(s).`
          : `Scanner final bloqueado: ${(report.validation?.blockers || []).join(" | ")}`
      );
      await loadProjectFiles(scannerProject, { silent: true });
      return passed;
    } catch (scanError) {
      if (scannerWatchdogRef.current) {
        window.clearTimeout(scannerWatchdogRef.current);
        scannerWatchdogRef.current = null;
      }
      stopCodeScanner(scanError.message || "Scanner final bloqueado.");
      setCodeScanner((current) => ({ ...current, passed: false }));
      setError(scanError.message || "No fue posible ejecutar scanner final.");
      return false;
    }
  }

  async function persistFinalTypewriterPlayback(projectId, finalFiles, trigger) {
    const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/typewriter-final`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        trigger,
        playedFiles: (finalFiles || []).map((entry) => entry.path),
      }),
    });
    const report = payload.report || {};
    if (!report.validation?.passed) {
      throw new Error((report.validation?.blockers || []).join(" | ") || "Typewriter final no pudo persistir evidencia.");
    }
    setStatus(`Typewriter final persistido: ${report.summary?.filesPlayed || 0} archivo(s), ${report.summary?.charactersPlayed || 0} caracter(es).`);
    return report;
  }

  async function waitForFinalSequenceUnlock(projectId) {
    let snapshot = { files: filesRef.current, lock: lockRef.current };
    for (let attempt = 0; attempt < FINAL_SEQUENCE_UNLOCK_RETRIES; attempt += 1) {
      snapshot = await loadProjectFiles(projectId, { silent: true });
      const nextLock = snapshot.lock || EMPTY_LOCK;
      const status = String(nextLock.projectStatus || "").toLowerCase();
      if (!isRuntimeActive(nextLock) && (!status || FINAL_SEQUENCE_TERMINAL_STATUSES.has(status))) {
        return snapshot;
      }
      await sleep(FINAL_SEQUENCE_UNLOCK_DELAY_MS);
    }
    return snapshot;
  }

  async function runFinalRuntimeSequence(projectId, trigger = "runtime cerrado", { force = false } = {}) {
    if (!projectId || finalSequenceRunningRef.current || codeScannerRef.current.active) return false;
    if (dirtyRef.current) {
      const message = "Typewriter final bloqueado: hay cambios humanos sin guardar.";
      setStatus(message);
      setError(message);
      return false;
    }
    if (!force && finalSequenceCompletedProjectsRef.current.has(projectId) && !runtimeActiveProjectsRef.current.has(projectId)) return false;

    finalSequenceRunningRef.current = true;
    setRepairOpen(false);
    setActivePane("explorer");
    setError("");
    setTargetLine(1);
    document.getElementById("code-workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
    setFinalSequence({
      active: true,
      phase: "waiting",
      index: 0,
      total: 0,
      path: "",
      message: `Secuencia final esperando cierre real: ${trigger}`,
    });
    setStatus("Runtime cerrado: preparando typewriter final de todos los archivos.");

    try {
      const snapshot = await waitForFinalSequenceUnlock(projectId);
      const nextLock = snapshot.lock || EMPTY_LOCK;
      if (isRuntimeActive(nextLock)) {
        throw new Error(nextLock.message || "El runtime sigue activo; scanner final aplazado.");
      }
      const finalFiles = orderedFinalFiles(snapshot.files || filesRef.current);
      if (!finalFiles.length) {
        throw new Error("No hay archivos visibles para la secuencia final.");
      }

      for (let index = 0; index < finalFiles.length; index += 1) {
        const entry = finalFiles[index];
        skipNextAutoLoadRef.current = `${projectId}:${entry.path}`;
        setSelectedProject(projectId);
        setSelectedPath(entry.path);
        setTargetLine(1);
        focusWriterAtStart();
        setFinalSequence({
          active: true,
          phase: "typewriter",
          index: index + 1,
          total: finalFiles.length,
          path: entry.path,
          message: `Typewriter final ${index + 1}/${finalFiles.length}: ${entry.path}`,
        });
        setStatus(`Typewriter final escribiendo ${entry.path}`);
        const loadedFile = await loadProjectFile(projectId, entry.path, { silent: true, preserveDirty: true });
        await typewriteContent(
          String(loadedFile?.content || ""),
          entry.path,
          `Typewriter final ${index + 1}/${finalFiles.length}: ${entry.path}`,
          { forceFromStart: true, keepAtTop: true }
        );
      }

      await persistFinalTypewriterPlayback(projectId, finalFiles, trigger);

      setFinalSequence({
        active: true,
        phase: "scanner",
        index: finalFiles.length,
        total: finalFiles.length,
        path: "",
        message: "Typewriter final completo. Activando scanner final.",
      });
      const scannerPassed = await launchCodeScanner({ projectId, force: true });
      let sandboxState = null;
      if (scannerPassed) {
        setFinalSequence({
          active: true,
          phase: "sandbox",
          index: finalFiles.length,
          total: finalFiles.length,
          path: "",
          message: "Scanner aprobado. Activando Runtime Sandbox del proyecto.",
        });
        sandboxState = await startSandbox({ projectId, automatic: true });
      }
      const sandboxReady = Boolean(sandboxState?.running);
      setFinalSequence({
        active: false,
        phase: scannerPassed && sandboxReady ? "done" : "blocked",
        index: finalFiles.length,
        total: finalFiles.length,
        path: "",
        message: scannerPassed && sandboxReady
          ? `Secuencia final completa: writer, scanner y sandbox activos en ${sandboxState.url}.`
          : scannerPassed
            ? "Scanner aprobado, pero el Runtime Sandbox no pudo arrancar."
            : "Secuencia final bloqueada en scanner.",
      });
      if (scannerPassed && sandboxReady) {
        finalSequenceCompletedProjectsRef.current.add(projectId);
        runtimeActiveProjectsRef.current.delete(projectId);
      }
      return scannerPassed && sandboxReady;
    } catch (sequenceError) {
      stopLiveWriter(sequenceError.message || "Secuencia final detenida.");
      stopCodeScanner(sequenceError.message || "Secuencia final detenida.");
      setFinalSequence((current) => ({
        ...current,
        active: false,
        phase: "blocked",
        message: sequenceError.message || "Secuencia final bloqueada.",
      }));
      setError(sequenceError.message || "No fue posible ejecutar secuencia final.");
      return false;
    } finally {
      finalSequenceRunningRef.current = false;
    }
  }

  function rememberFileSignatures(projectId, nextFiles, { detect = false } = {}) {
    const projectKey = String(projectId || "");
    const previous = fileSignaturesByProjectRef.current.get(projectKey);
    const next = new Map();
    const changedFiles = [];
    for (const entry of nextFiles || []) {
      const path = String(entry?.path || "");
      if (!path) continue;
      const signature = fileSignature(entry);
      next.set(path, signature);
      if (detect && previous?.size && previous.get(path) !== signature) {
        changedFiles.push(entry);
      }
    }
    fileSignaturesByProjectRef.current.set(projectKey, next);
    return changedFiles;
  }

  async function openLiveWriterFile(projectId, entry, writerMessage = "") {
    const path = typeof entry === "string" ? entry : String(entry?.path || "");
    if (!projectId || !path || dirtyRef.current) return false;
    const signature = typeof entry === "string" ? "" : fileSignature(entry);
    const writerKey = `${projectId}:${path}:${signature}`;
    if (writerKey && lastAutoWriterKeyRef.current === writerKey && liveWriterRef.current.path === path) {
      return false;
    }
    lastAutoWriterKeyRef.current = writerKey;
    skipNextAutoLoadRef.current = `${projectId}:${path}`;
    setSelectedProject(projectId);
    setSelectedPath(path);
    setTargetLine(null);
    setActivePane("explorer");
    setStatus(`IA escribiendo en vivo: ${path}`);
    await loadProjectFile(projectId, path, {
      silent: true,
      preserveDirty: true,
      animate: true,
      writerMessage: writerMessage || `IA escribiendo ${path}`,
    });
    return true;
  }

  async function loadProjectProblems(projectId, { silent = false } = {}) {
    if (!projectId) return;
    if (!silent) {
      setLoadingProblems(true);
      setError("");
    }
    try {
      const payload = await fetchJson(`/api/architecture/lint?scene=${encodeURIComponent(projectId)}`);
      setProblems(payload.report?.findings || []);
      if (!silent) {
        setStatus(`${payload.report?.findings?.length || 0} hallazgos visuales cargados.`);
      }
    } catch (loadError) {
      if (!silent) setError(loadError.message || "No fue posible cargar problemas.");
    } finally {
      if (!silent) setLoadingProblems(false);
    }
  }

  async function loadSandbox(projectId = selectedProject, { silent = false } = {}) {
    if (!projectId) return null;
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/sandbox`);
      const nextSandbox = {
        ...(payload.sandbox || {}),
        logs: payload.logs || [],
      };
      setSandbox(nextSandbox);
      if (nextSandbox.running && nextSandbox.embedUrl && !silent && !codeScannerRef.current.active) {
        setSandboxPreviewOpen(true);
      }
      return nextSandbox;
    } catch (sandboxError) {
      if (!silent) setError(sandboxError.message || "No fue posible cargar sandbox.");
      return null;
    }
  }

  async function loadRuntimeTruth(projectId = selectedProject, { silent = false } = {}) {
    if (!projectId) {
      setRuntimeTruth(null);
      return null;
    }
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/runtime-truth`);
      lastRuntimeTruthRefreshAtRef.current = Date.now();
      setRuntimeTruth(payload);
      return payload;
    } catch (truthError) {
      if (!silent) setError(truthError.message || "No fue posible cargar supervisor real.");
      return null;
    }
  }

  async function releaseRuntimeZombie(projectId = selectedProject) {
    if (!projectId || runtimeTruthBusy) return null;
    setRuntimeTruthBusy(true);
    setError("");
    setActivePane("runtime");
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/runtime-zombie/release`, { method: "POST" });
      if (payload.projects) setProjects(payload.projects);
      setRuntimeTruth(payload.truth || null);
      await loadProjectFiles(projectId, { silent: true });
      await loadRuntimeTruth(projectId, { silent: true });
      setStatus(`Supervisor real libero zombie: ${(payload.releasedTaskIds || []).join(", ") || "sin id"}.`);
      return payload;
    } catch (releaseError) {
      const message = releaseError.message || "No fue posible liberar zombie runtime.";
      setError(message);
      setStatus(message);
      return null;
    } finally {
      setRuntimeTruthBusy(false);
    }
  }

  async function focusIntegrityFinding(finding, { openRepair = true } = {}) {
    if (!finding) return;
    const path = normalizeWorkbenchRelativePath(finding.path || finding.focusPath || "");
    const line = Math.max(1, Number(finding.line || 1) || 1);
    if (path) {
      const projectId = selectedProjectRef.current || selectedProject;
      const repairTarget = integrityFindingToTarget(finding, projectId);
      setSelectedPath(path);
      setActivePane("explorer");
      setTargetLine(line);
      setActiveIssueTarget(repairTarget);
      setRepairInstruction(
        "Repara o restaura este cambio externo usando la evidencia de integridad y valida que Verificar integridad quede limpio. No aceptes baseline."
      );
      setRepairStatus("");
      if (openRepair) setRepairOpen(true);
      setJumpNotice(`Cambio externo: ${path}:${line}`);
      if (projectId && !dirtyRef.current) {
        await loadProjectFile(projectId, path, { silent: true, preserveDirty: false });
      }
      window.setTimeout(() => focusEditorLine(line), 120);
    }
  }

  async function loadIntegrityReport(projectId = selectedProject, { silent = false } = {}) {
    if (!projectId) return null;
    if (!silent) {
      setIntegrityBusy(true);
      setError("");
    }
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/integrity/report`);
      const report = payload.report || null;
      setIntegrityReport(report);
      return report;
    } catch (integrityError) {
      if (!silent) setError(integrityError.message || "No fue posible cargar integridad.");
      return null;
    } finally {
      if (!silent) setIntegrityBusy(false);
    }
  }

  async function scanIntegrity(projectId = selectedProject, { silent = false } = {}) {
    if (!projectId) return null;
    if (codeScannerRef.current.active) {
      stopCodeScanner("Scanner final detenido para verificar integridad.");
    }
    if (integrityScanInFlightRef.current) {
      if (!silent) setVisibleIntegrityStatus("Ya hay un scan de integridad en ejecucion; espera el resultado.");
      return null;
    }
    const blocker = !silent ? integrityBlockedReason("Verificar integridad") : "";
    if (blocker) {
      setVisibleIntegrityStatus(blocker);
      return null;
    }
    integrityScanInFlightRef.current = true;
    if (!silent) {
      setIntegrityBusy(true);
      setError("");
      setVisibleIntegrityStatus("Observer escaneando integridad de archivos...");
    }
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/integrity/scan`, { method: "POST" });
      const report = payload.report || null;
      setIntegrityReport(report);
      const findings = Array.isArray(report?.findings) ? report.findings : [];
      if (findings.length && !silent) {
        setSandboxPreviewOpen(false);
        focusIntegrityFinding(findings[0], { openRepair: true });
        setVisibleIntegrityStatus(`Observer detecto ${findings.length} huella(s). Abri la primera para reparacion.`);
      } else if (!silent) {
        setVisibleIntegrityStatus("Observer no detecto cambios externos en archivos generados.");
      }
      return report;
    } catch (integrityError) {
      if (!silent) {
        const message = integrityError.message || "No fue posible ejecutar integridad.";
        setError(message);
        setVisibleIntegrityStatus(message);
      }
      return null;
    } finally {
      integrityScanInFlightRef.current = false;
      if (!silent) setIntegrityBusy(false);
    }
  }

  async function acceptIntegrityBaseline(projectId = selectedProject) {
    if (!projectId) return;
    if (codeScannerRef.current.active) {
      stopCodeScanner("Scanner final detenido para aceptar baseline.");
    }
    const blocker = integrityBlockedReason("Aceptar baseline");
    if (blocker) {
      setVisibleIntegrityStatus(blocker);
      return;
    }
    const confirmed = window.confirm("Aceptar baseline marca el estado actual como confiable. Hazlo solo si revisaste las huellas.");
    if (!confirmed) {
      setVisibleIntegrityStatus("Aceptar baseline cancelado por humano.");
      return;
    }
    setIntegrityBusy(true);
    setError("");
    setVisibleIntegrityStatus("Aceptando nueva baseline de integridad...");
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/integrity/baseline`, { method: "POST" });
      setIntegrityReport(payload.report || null);
      setVisibleIntegrityStatus("Nueva baseline de integridad aceptada por humano.");
    } catch (integrityError) {
      const message = integrityError.message || "No fue posible aceptar baseline.";
      setError(message);
      setVisibleIntegrityStatus(message);
    } finally {
      setIntegrityBusy(false);
    }
  }

  async function runFrozenSniper(projectId = selectedProject) {
    if (!projectId) return;
    if (codeScannerRef.current.active) {
      stopCodeScanner("Scanner final detenido para ejecutar Frozen Sniper.");
    }
    const blocker = integrityBlockedReason("Frozen Sniper");
    if (blocker) {
      setVisibleIntegrityStatus(blocker);
      return;
    }
    if (!integrityFindings.length) {
      setVisibleIntegrityStatus("No hay huellas activas para Frozen Sniper. Verificando integridad otra vez...");
      const latestReport = await scanIntegrity(projectId, { silent: true });
      const latestFindings = Array.isArray(latestReport?.findings) ? latestReport.findings : [];
      if (!latestFindings.length) {
        setIntegrityReport(latestReport);
        setVisibleIntegrityStatus("Integridad limpia: Frozen Sniper no tiene nada que restaurar.");
        return;
      }
    }
    const confirmed = window.confirm("Frozen Sniper va a congelar evidencia, restaurar archivos de la baseline y poner no registrados en cuarentena.");
    if (!confirmed) {
      setVisibleIntegrityStatus("Frozen Sniper cancelado por humano.");
      return;
    }
    setIntegrityBusy(true);
    setError("");
    setVisibleIntegrityStatus("Frozen Sniper congelando evidencia y recuperando archivos...");
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(projectId)}/integrity/frozen-sniper`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: "FROZEN_SNIPER" }),
      });
      const report = payload.report || {};
      const summary = report.summary || {};
      const afterIntegrityReport = payload.afterIntegrityReport || report.afterIntegrityReport || null;
      setIntegrityReport(afterIntegrityReport);
      setRepairOpen(false);
      setActiveIssueTarget(null);
      setJumpNotice("");
      setVisibleIntegrityStatus(`Frozen Sniper restauro ${summary.restoredFiles || 0} archivo(s), cuarenteno ${summary.quarantinedFiles || 0} y congelo evidencia.`);
      await loadProjectFiles(projectId, { silent: true });
      if (selectedPath) {
        await loadProjectFile(projectId, selectedPath, { silent: true, preserveDirty: false });
      }
      const latestReport = afterIntegrityReport || await loadIntegrityReport(projectId, { silent: true });
      const remainingFindings = Array.isArray(latestReport?.findings) ? latestReport.findings.length : 0;
      setVisibleIntegrityStatus(
        remainingFindings
          ? `Frozen Sniper termino, pero quedan ${remainingFindings} huella(s).`
          : `Frozen Sniper completo: ${summary.restoredFiles || 0} archivo(s) restaurado(s), integridad limpia.`
      );
    } catch (integrityError) {
      const message = integrityError.message || "Frozen Sniper no pudo recuperar integridad.";
      setError(message);
      setVisibleIntegrityStatus(message);
    } finally {
      setIntegrityBusy(false);
    }
  }

  async function startSandbox(options = {}) {
    const requestedProject = options?.projectId || selectedProject;
    const automatic = Boolean(options?.automatic);
    if (!requestedProject || sandboxBusy || (!automatic && (finalSequenceRef.current.active || codeScannerRef.current.active))) return null;
    setSandboxBusy(true);
    setError("");
    setStatus(automatic ? "Scanner aprobado. Arrancando Runtime Sandbox..." : "Arrancando sandbox runtime...");
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(requestedProject)}/sandbox/start`, {
        method: "POST",
      });
      const nextSandbox = { ...(payload.sandbox || {}), logs: payload.logs || [] };
      setSandbox(nextSandbox);
      if (nextSandbox.running && nextSandbox.embedUrl && !codeScannerRef.current.active) {
        setSandboxPreviewOpen(true);
      }
      setStatus(`Sandbox activo: ${payload.sandbox?.url || "preview local listo"}`);
      return nextSandbox;
    } catch (sandboxError) {
      setError(sandboxError.message || "No fue posible arrancar sandbox.");
      await loadSandbox(requestedProject, { silent: true });
      return null;
    } finally {
      setSandboxBusy(false);
    }
  }

  async function stopSandbox() {
    if (!selectedProject || sandboxBusy) return;
    setSandboxBusy(true);
    setError("");
    setStatus("Deteniendo sandbox runtime...");
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(selectedProject)}/sandbox/stop`, {
        method: "POST",
      });
      setSandbox({ ...(payload.sandbox || {}), logs: payload.logs || [] });
      setSandboxPreviewOpen(false);
      setStatus("Sandbox detenido.");
    } catch (sandboxError) {
      setError(sandboxError.message || "No fue posible detener sandbox.");
      await loadSandbox(selectedProject, { silent: true });
    } finally {
      setSandboxBusy(false);
    }
  }

  async function openEditorTarget(target, { source = "navigation" } = {}) {
    if (!target?.projectId || !target?.path) return;
    const line = Math.max(1, Number(target.line || 1) || 1);
    const nextIssueTarget = {
      projectId: target.projectId,
      path: target.path,
      line,
      message: target.message || source,
      code: target.code || "visual_issue",
      severity: target.severity || "warning",
      hint: target.hint || "",
      evidence: target.evidence || null,
      source: target.source || source,
    };
    setActivePane("explorer");
    setSelectedProject(target.projectId);
    setSelectedPath(target.path);
    setTargetLine(line);
    setActiveIssueTarget(nextIssueTarget);
    setJumpNotice(`${target.path}:${line} · ${target.message || source}`);
    setRepairStatus("");
    if (repairCompletionTimerRef.current) {
      window.clearTimeout(repairCompletionTimerRef.current);
      repairCompletionTimerRef.current = null;
    }
    setRepairProgress({
      active: false,
      percent: 0,
      label: "reparando codigo",
      detail: "",
      messages: [],
    });
    setStatus(`Navegando a ${target.path}:${line}`);
    if (selectedProject === target.projectId && selectedPath === target.path) {
      await loadProjectFile(target.projectId, target.path);
    }
    window.setTimeout(() => {
      document.getElementById("code-workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 20);
  }

  async function launchRepairAgent() {
    const blocker = repairBlockedReason();
    if (blocker) {
      setRepairStatus(blocker);
      setStatus(blocker);
      return;
    }
    setRepairSending(true);
    setRepairStatus("");
    setError("");
    onRepairPresenceStart?.({
      path: activeIssueTarget.path,
      line: activeIssueTarget.line,
      code: activeIssueTarget.code,
      message: activeIssueTarget.message,
    });
    updateRepairProgress({
      active: true,
      percent: 8,
      label: "reparando codigo",
      detail: `preparando worker para ${buildRepairStructureLabel(activeIssueTarget)}`,
      message: "preparando directiva de reparacion",
    });
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(selectedProject)}/repair`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: activeIssueTarget.path,
          line: activeIssueTarget.line,
          severity: activeIssueTarget.severity,
          code: activeIssueTarget.code,
          message: activeIssueTarget.message,
          hint: activeIssueTarget.hint,
          evidence: activeIssueTarget.evidence || {},
          instruction: repairInstruction,
        }),
      });
      const sessionId = payload.session?.sessionId || "sesion iniciada";
      setRepairStatus(`Worker de reparacion lanzado: ${sessionId}`);
      setStatus(`Worker reparando ${activeIssueTarget.path}:${activeIssueTarget.line}`);
      updateRepairProgress({
        active: true,
        minPercent: 18,
        detail: `worker activo sobre ${buildRepairStructureLabel(activeIssueTarget)}`,
        message: `worker lanzado: ${sessionId}`,
      });
      await loadProjectFiles(selectedProject, { silent: true });
      await loadProjectProblems(selectedProject, { silent: true });
    } catch (repairError) {
      setRepairStatus(repairError.message || "No fue posible lanzar el agente de reparacion.");
      setError(repairError.message || "No fue posible lanzar el agente de reparacion.");
      finishRepairProgress(repairError.message || "No fue posible lanzar el agente de reparacion.", { failed: true });
    } finally {
      setRepairSending(false);
    }
  }

  async function handleSave() {
    if (!canSave) return;
    setSaving(true);
    setError("");
    try {
      const payload = await fetchJson(`/api/projects/${encodeURIComponent(selectedProject)}/file`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: selectedPath, content: draft }),
      });
      const nextFile = payload.file || null;
      setFile(nextFile);
      setDraft(String(nextFile?.content || ""));
      setDirty(false);
      setLock(payload.lock || EMPTY_LOCK);
      setStatus(`Guardado humano confirmado: ${selectedPath}`);
      await loadProjects({ silent: true });
      await loadProjectFiles(selectedProject, { silent: true });
    } catch (saveError) {
      if (saveError.payload?.lock) setLock(saveError.payload.lock);
      setError(saveError.message || "No fue posible guardar.");
    } finally {
      setSaving(false);
    }
  }

  function handleDraftChange(value) {
    stopLiveWriter("Writer detenido por edicion humana.");
    setDraft(value);
    setDirty(value !== String(file?.content || ""));
  }

  function handleEditorScroll(event) {
    setEditorScrollTop(event.currentTarget.scrollTop);
    setEditorScrollLeft(event.currentTarget.scrollLeft);
    if (gutterRef.current) {
      gutterRef.current.scrollTop = event.currentTarget.scrollTop;
    }
  }

  function focusEditorLine(line) {
    const editor = editorRef.current;
    if (!editor || !line) return;
    const [start, end] = lineRange(draft, line);
    const computed = window.getComputedStyle(editor);
    const parsedLineHeight = Number.parseFloat(computed.lineHeight);
    const lineHeight = Number.isFinite(parsedLineHeight) ? parsedLineHeight : 20;
    const scrollTop = Math.max(0, (Math.max(1, line) - 1) * lineHeight - 110);
    editor.focus();
    editor.setSelectionRange(start, end);
    editor.scrollTop = scrollTop;
    setEditorScrollTop(scrollTop);
    setEditorScrollLeft(editor.scrollLeft);
    if (gutterRef.current) {
      gutterRef.current.scrollTop = scrollTop;
    }
  }

  useEffect(() => {
    selectedProjectRef.current = selectedProject;
  }, [selectedProject]);

  useEffect(() => () => {
    if (agentChangeTraceTimerRef.current) window.clearTimeout(agentChangeTraceTimerRef.current);
  }, []);

  useEffect(() => {
    selectedPathRef.current = selectedPath;
  }, [selectedPath]);

  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  useEffect(() => {
    lockRef.current = lock;
    if (selectedProject && isRuntimeActive(lock)) {
      runtimeActiveProjectsRef.current.add(selectedProject);
      finalSequenceCompletedProjectsRef.current.delete(selectedProject);
    }
  }, [lock, selectedProject]);

  useEffect(() => {
    dirtyRef.current = dirty;
  }, [dirty]);

  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  useEffect(() => {
    liveWriterRef.current = liveWriter;
  }, [liveWriter]);

  useEffect(() => {
    finalSequenceRef.current = finalSequence;
  }, [finalSequence]);

  useEffect(() => {
    codeScannerRef.current = codeScanner;
  }, [codeScanner]);

  useEffect(() => {
    if (codeScanner.active && sandboxPreviewOpen) {
      setSandboxPreviewOpen(false);
    }
  }, [codeScanner.active, sandboxPreviewOpen]);

  useEffect(() => {
    return () => {
      if (writerTimerRef.current) {
        window.clearInterval(writerTimerRef.current);
        writerTimerRef.current = null;
      }
      if (writerDoneTimerRef.current) {
        window.clearTimeout(writerDoneTimerRef.current);
        writerDoneTimerRef.current = null;
      }
      if (writerResolveRef.current) {
        writerResolveRef.current(false);
        writerResolveRef.current = null;
      }
      if (scannerTimerRef.current) {
        window.clearInterval(scannerTimerRef.current);
        scannerTimerRef.current = null;
      }
      if (scannerWatchdogRef.current) {
        window.clearTimeout(scannerWatchdogRef.current);
        scannerWatchdogRef.current = null;
      }
      clearScannerFocusTimers();
      if (writerFrameRef.current) {
        window.cancelAnimationFrame(writerFrameRef.current);
        writerFrameRef.current = null;
      }
      if (repairCompletionTimerRef.current) {
        window.clearTimeout(repairCompletionTimerRef.current);
        repairCompletionTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!repairProgress.active) return undefined;
    const timerId = window.setInterval(() => {
      setRepairProgress((current) => {
        if (!current.active || current.percent >= 92) return current;
        const step = current.percent < 32 ? 4 : current.percent < 70 ? 2 : 1;
        return { ...current, percent: Math.min(92, current.percent + step) };
      });
    }, 900);
    return () => window.clearInterval(timerId);
  }, [repairProgress.active]);

  useEffect(() => {
    if (!socketUrl) return undefined;
    const socket = io(socketUrl, {
      transports: ["polling"],
      upgrade: false,
      reconnection: true,
      timeout: 20000,
    });

    async function fetchApi(path, options = {}) {
      const response = await fetch(buildApiUrl(socketUrl, path), options);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.lock?.message || payload?.message || payload?.error || `request_failed_${response.status}`);
      }
      return payload;
    }

    async function refreshFiles(projectId) {
      const payload = await fetchApi(`/api/projects/${encodeURIComponent(projectId)}/files`);
      const nextFiles = payload.files || [];
      const nextLock = payload.lock || EMPTY_LOCK;
      const changedFiles = rememberFileSignatures(projectId, nextFiles, { detect: true });
      filesRef.current = nextFiles;
      lockRef.current = nextLock;
      if (isRuntimeActive(nextLock)) {
        runtimeActiveProjectsRef.current.add(projectId);
        finalSequenceCompletedProjectsRef.current.delete(projectId);
      }
      setFiles(nextFiles);
      setLock(nextLock);
      setSelectedPath((current) => {
        if (current && nextFiles.some((entry) => entry.path === current)) return current;
        return chooseInitialFile(nextFiles);
      });
      return { changedFiles, files: nextFiles, lock: nextLock };
    }

    async function refreshProblems(projectId) {
      const payload = await fetchApi(`/api/architecture/lint?scene=${encodeURIComponent(projectId)}`);
      setProblems(payload.report?.findings || []);
    }

    async function refreshFile(projectId, path, animate, message) {
      if (dirtyRef.current) return;
      const previousContent = selectedPathRef.current === path ? draftRef.current : "";
      const payload = await fetchApi(`/api/projects/${encodeURIComponent(projectId)}/file?path=${encodeURIComponent(path)}`);
      const nextFile = payload.file || null;
      const nextContent = String(nextFile?.content || "");
      setFile(nextFile);
      setLock(payload.lock || EMPTY_LOCK);
      setDirty(false);
      if (animate) {
        const changedLine = firstChangedLine(previousContent, nextContent);
        markAgentChangedFile(path, message || `Agente modifico ${path}`, changedLine);
        typewriteContent(nextContent, path, message);
      } else {
        setDraft(nextContent);
      }
    }

    socket.on("agent:session", (nextSession) => {
      if (!nextSession?.sessionId) return;
      const projectSlug = String(nextSession.projectSlug || "");
      const currentProject = selectedProjectRef.current;
      if (currentProject && projectSlug && projectSlug !== currentProject) return;
      appendAgentChatEvent({
        op: `session_${nextSession.status || "update"}`,
        sessionId: nextSession.sessionId,
        projectSlug,
        status: nextSession.status,
        message: nextSession.progressLabel || nextSession.errorMessage || `Sesion ${nextSession.status || "actualizada"}`,
      });
      if (["completed", "failed", "stopped", "blocked"].includes(String(nextSession.status || "").toLowerCase())) {
        appendAgentChatMessage({
          role: "assistant",
          text: nextSession.errorMessage || nextSession.progressLabel || `Sesion ${nextSession.status}.`,
        });
      }
    });

    socket.on("agent:terminal", (payload) => {
      if (!payload?.sessionId) return;
      const projectSlug = String(payload.projectSlug || "");
      const currentProject = selectedProjectRef.current;
      if (currentProject && projectSlug && projectSlug !== currentProject) return;
      appendAgentChatEvent({
        op: "terminal",
        sessionId: payload.sessionId,
        projectSlug,
        status: payload.status,
        message: payload.status ? `Terminal ${payload.status}` : "Terminal actualizado",
      });
    });

    socket.on("agent:visual", (payload) => {
      if (!payload?.projectSlug) return;
      const projectSlug = String(payload.projectSlug);
      const currentProject = selectedProjectRef.current;
      if (currentProject && projectSlug !== currentProject) return;
      appendAgentChatEvent(payload);
      const op = String(payload.op || "").toLowerCase();
      const relativePath = String(payload.relativePath || "").replace(/^\/+/, "");

      if (op === "delegate_chat" || op === "agent_chat_delegate") {
        window.dispatchEvent(new CustomEvent("code-workbench:delegate-agent-chat", {
          detail: {
            projectSlug,
            prompt: payload.prompt || payload.requirement || payload.message || "",
          },
        }));
        return;
      }

      if (op === "repair_session_start") {
        setRepairStatus(payload.message || "Worker de reparacion lanzado.");
        setStatus(payload.message || "Worker de reparacion activo.");
        updateRepairProgress({
          active: true,
          minPercent: 24,
          detail: selectedPathRef.current ? `reparando ${selectedPathRef.current}` : "worker de reparacion activo",
          message: payload.message || "worker de reparacion activo",
        });
        return;
      }

      if (op === "sync_file" && relativePath) {
        markAgentChangedFile(relativePath, payload.message || `Agente modifico ${relativePath}`, Number(payload.line || 1) || 1);
        skipNextAutoLoadRef.current = `${projectSlug}:${relativePath}`;
        setSelectedProject(projectSlug);
        setSelectedPath(relativePath);
        setTargetLine(null);
        setActivePane("explorer");
        setStatus(`Writer en vivo: ${relativePath}`);
        setRepairStatus(`Agente escribio ${relativePath}`);
        updateRepairProgress({
          active: true,
          minPercent: 62,
          detail: `aplicando cambios en ${relativePath}`,
          message: payload.message || `writer sincronizando ${relativePath}`,
        });
        refreshFiles(projectSlug)
          .then(() => refreshFile(projectSlug, relativePath, true, payload.message || `IA escribiendo ${relativePath}`))
          .then(() => refreshProblems(projectSlug))
          .catch((liveError) => setError(liveError.message || "No fue posible refrescar el writer en vivo."));
        return;
      }

      if (
        op === "session_complete" ||
        op === "session_completed" ||
        op === "session_completed_with_warnings" ||
        op === "session_blocked" ||
        op === "session_failed" ||
        op === "session_stopped"
      ) {
        const message = payload.message || `Sesion de reparacion cerrada: ${payload.status || op}`;
        setRepairStatus(message);
        setStatus(message);
        stopLiveWriter(message);
        finishRepairProgress(message, { failed: op === "session_blocked" || op === "session_failed" || op === "session_stopped" });
        refreshFiles(projectSlug)
          .then(() => refreshProblems(projectSlug))
          .then(() => {
            if (FINAL_SEQUENCE_OPS.has(op)) {
              runtimeActiveProjectsRef.current.add(projectSlug);
              return runFinalRuntimeSequence(projectSlug, op, { force: true });
            }
            const currentPath = selectedPathRef.current;
            if (currentPath) return refreshFile(projectSlug, currentPath, false, "");
            return null;
          })
          .catch((liveError) => setError(liveError.message || "No fue posible refrescar el cierre de reparacion."));
      }

      if (op === "sandbox_started" || op === "sandbox_stopped") {
        loadSandbox(projectSlug, { silent: true }).then((nextSandbox) => {
          if (op === "sandbox_started" && nextSandbox?.running && nextSandbox?.embedUrl && !codeScannerRef.current.active) {
            setSandboxPreviewOpen(true);
          }
          if (op === "sandbox_stopped") {
            setSandboxPreviewOpen(false);
          }
        });
      }

      if (op === "file_integrity_scan_complete" && payload.report) {
        setIntegrityReport(payload.report);
        const findings = Array.isArray(payload.report.findings) ? payload.report.findings : [];
        if (findings.length) {
          setSandboxPreviewOpen(false);
          focusIntegrityFinding(findings[0], { openRepair: true });
        }
      }

      if (op === "frozen_sniper_recovery_complete" && payload.report) {
        const afterIntegrityReport = payload.report.afterIntegrityReport || null;
        if (afterIntegrityReport) setIntegrityReport(afterIntegrityReport);
        loadProjectFiles(projectSlug, { silent: true });
      }
    });

    return () => socket.disconnect();
  }, [socketUrl]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (cancelled) return;
      await loadProjects({ silent: true });
    }
    loadProjects();
    const timerId = window.setInterval(run, 20000);
    return () => {
      cancelled = true;
      window.clearInterval(timerId);
    };
  }, [socketUrl]);

  useEffect(() => {
    if (!sortedProjects.length) {
      setSelectedProject("");
      return;
    }
    setSelectedProject((current) => {
      if (focusedProject && sortedProjects.some((project) => project.slug === focusedProject)) {
        return focusedProject;
      }
      if (current && sortedProjects.some((project) => project.slug === current)) {
        return current;
      }
      return sortedProjects[0]?.slug || "";
    });
  }, [focusedProject, sortedProjects]);

  useEffect(() => {
    if (!selectedProject) {
      setFiles([]);
      setSelectedPath("");
      setFile(null);
      setDraft("");
      setDirty(false);
      setLock(EMPTY_LOCK);
      setSandbox({ status: "idle", running: false, url: "", port: null, technology: null, logs: [] });
      setRuntimeTruth(null);
      setIntegrityReport(null);
      setEditorScrollTop(0);
      setEditorScrollLeft(0);
      setSandboxPreviewOpen(false);
      return;
    }
    setSandboxPreviewOpen(false);
    loadProjectFiles(selectedProject);
    loadProjectProblems(selectedProject, { silent: true });
    loadSandbox(selectedProject, { silent: true });
    loadRuntimeTruth(selectedProject, { silent: true });
    loadIntegrityReport(selectedProject, { silent: true });
  }, [selectedProject]);

  useEffect(() => {
    if (!selectedProject || !selectedPath) {
      setFile(null);
      setDraft("");
      setDirty(false);
      setEditorScrollTop(0);
      setEditorScrollLeft(0);
      return;
    }
    if (editorRef.current) {
      editorRef.current.scrollTop = 0;
      editorRef.current.scrollLeft = 0;
    }
    if (gutterRef.current) {
      gutterRef.current.scrollTop = 0;
    }
    setEditorScrollTop(0);
    setEditorScrollLeft(0);
    if (skipNextAutoLoadRef.current === `${selectedProject}:${selectedPath}`) {
      skipNextAutoLoadRef.current = "";
      return;
    }
    loadProjectFile(selectedProject, selectedPath);
  }, [selectedProject, selectedPath]);

  useEffect(() => {
    if (!selectedProject) return undefined;
    let cancelled = false;
    async function refreshLiveEditor() {
      if (cancelled) return;
      const snapshot = await loadProjectFiles(selectedProject, { silent: true });
      const changedFiles = snapshot?.changedFiles || [];
      if (cancelled) return;
      await loadProjectProblems(selectedProject, { silent: true });
      await loadSandbox(selectedProject, { silent: true });
      if (Date.now() - lastRuntimeTruthRefreshAtRef.current > 8000) {
        await loadRuntimeTruth(selectedProject, { silent: true });
      }
      if (!dirtyRef.current && !liveWriterRef.current.active && !codeScannerRef.current.active && !finalSequenceRef.current.active) {
        if (changedFiles.length) {
          const changedKey = `${selectedProject}:${changedFiles.map((entry) => `${entry.path}:${fileSignature(entry)}`).join("|")}`;
          if (changedKey !== lastIntegrityAutoScanKeyRef.current) {
            lastIntegrityAutoScanKeyRef.current = changedKey;
            await scanIntegrity(selectedProject, { silent: true });
          }
        } else if (Date.now() - lastIntegrityReportRefreshAtRef.current > INTEGRITY_REPORT_REFRESH_MS) {
          lastIntegrityReportRefreshAtRef.current = Date.now();
          await loadIntegrityReport(selectedProject, { silent: true });
        }
      }
      if (cancelled) return;
      const nextLock = snapshot?.lock || lockRef.current || EMPTY_LOCK;
      const status = String(nextLock.projectStatus || "").toLowerCase();
      if (
        runtimeActiveProjectsRef.current.has(selectedProject) &&
        !finalSequenceCompletedProjectsRef.current.has(selectedProject) &&
        !isRuntimeActive(nextLock) &&
        (FINAL_SEQUENCE_TERMINAL_STATUSES.has(status) || !status)
      ) {
        runFinalRuntimeSequence(selectedProject, "transicion polling runtime cerrado");
        return;
      }
      if (!changedFiles?.length && selectedPath && !dirtyRef.current && !liveWriterRef.current.active && !codeScannerRef.current.active) {
        await loadProjectFile(selectedProject, selectedPath, { silent: true, preserveDirty: true });
      }
    }
    const timerId = window.setInterval(refreshLiveEditor, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(timerId);
    };
  }, [selectedProject, selectedPath]);

  useEffect(() => {
    if (!jumpTarget?.id) return;
    openEditorTarget(jumpTarget, { source: "visual issue" });
  }, [jumpTarget?.id]);

  useEffect(() => {
    if (!targetLine || !selectedPath) return undefined;
    const timerId = window.setTimeout(() => focusEditorLine(targetLine), 80);
    return () => window.clearTimeout(timerId);
  }, [draft, selectedPath, targetLine]);

  const terminalLines = [
    `Neuro LACE Runtime Code Workbench`,
    `project: ${selectedProject || "sin proyecto"}`,
    `mode: ${lock.locked ? "live-readonly" : "human-editable"}`,
    `truth_verdict: ${runtimeTruthLabel(runtimeTruth)}`,
    `truth_sessions: ${runtimeTruth?.sessions?.activeCount ?? "?"} active / ${runtimeTruth?.sessions?.totalRuntimeSessions ?? "?"} total`,
    `truth_worker: ${runtimeTruth?.worker?.alive === true ? `alive pid=${runtimeTruth?.worker?.pid || "?"}` : "none"}`,
    `truth_last_disk: ${formatTruthAge(runtimeTruth?.disk?.lastActivityAgeSeconds)} ago`,
    `runtime_status: ${lock.projectStatus || "idle"}`,
    `task: ${lock.currentTaskId || "none"}`,
    `file: ${selectedPath || "none"}`,
    `writer: ${liveWriter.active ? `active ${liveWriter.path}` : "idle"}`,
    `final_sequence: ${finalSequence.active ? `${finalSequence.phase} ${finalSequence.index}/${finalSequence.total}` : finalSequence.phase}`,
    `scanner: ${codeScanner.active ? `active ${codeScanner.path}:${codeScanner.line}` : codeScanner.passed === true ? "passed" : codeScanner.passed === false ? "blocked" : "idle"}`,
    `integrity: ${integrityFindings.length ? `${integrityFindings.length} external-change finding(s)` : integrityReport?.baselineExists === false ? "no baseline" : "clean"}`,
    `sandbox: ${sandbox.running ? `running ${sandbox.url}` : sandbox.status || "idle"}`,
    `pane: ${activePane}`,
    `problems: ${problems.length}`,
    `target_line: ${targetLine || "none"}`,
    `dirty: ${dirty ? "yes" : "no"}`,
    `status: ${error || status}`,
  ];

  return (
    <section id="code-workbench" className={`code-workbench-panel ${expanded ? "is-expanded-editor" : ""}`}>
      <CodeWorkbenchTopMenu
        lock={lock}
        canSave={canSave}
        selectedProject={selectedProject}
        selectedPath={selectedPath}
        dirty={dirty}
        liveWriterActive={liveWriter.active}
        finalSequenceActive={finalSequence.active}
        scannerActive={codeScanner.active}
        integrityBusy={integrityBusy}
        sandboxBusy={sandboxBusy}
        sandboxRunning={sandbox.running}
        sandboxEmbedUrl={sandbox.embedUrl}
        onSave={handleSave}
        onRefreshFiles={() => selectedProject && loadProjectFiles(selectedProject)}
        onRevertFile={() => selectedProject && selectedPath && loadProjectFile(selectedProject, selectedPath)}
        onPaneChange={setActivePane}
        onLoadProblems={() => { setActivePane("problems"); loadProjectProblems(selectedProject); }}
        onRunFinalSequence={() => selectedProject && runFinalRuntimeSequence(selectedProject, "manual", { force: true })}
        onToggleScanner={() => codeScanner.active ? stopCodeScanner("Scanner final detenido por humano.") : launchCodeScanner()}
        onScanIntegrity={() => scanIntegrity()}
        onStartSandbox={() => startSandbox()}
        onOpenSandbox={() => setSandboxPreviewOpen(true)}
        onStopSandbox={stopSandbox}
      />

      <div className="code-workbench-shell" style={{ "--workbench-sidebar-width": `${sidebarWidth}px` }}>
        <CodeWorkbenchActivityBar
          activePane={activePane}
          onPaneChange={setActivePane}
          onProblemsOpen={() => { setActivePane("problems"); loadProjectProblems(selectedProject); }}
        />

        <CodeWorkbenchSidebar
          activePane={activePane}
          selectedProject={selectedProject}
          selectedPath={selectedPath}
          sortedProjects={sortedProjects}
          selectedProjectMeta={selectedProjectMeta}
          files={files}
          loadingProjects={loadingProjects}
          loadingFile={loadingFile}
          loadingProblems={loadingProblems}
          finalSequenceActive={finalSequence.active}
          scannerActive={codeScanner.active}
          fileFilter={fileFilter}
          filteredFiles={filteredFiles}
          problemRows={problemRows}
          testFiles={testFiles}
          lock={lock}
          sandbox={sandbox}
          sandboxBusy={sandboxBusy}
          runtimeTruth={runtimeTruth}
          runtimeTruthBusy={runtimeTruthBusy}
          onReleaseRuntimeZombie={() => releaseRuntimeZombie(selectedProject)}
          onPaneChange={setActivePane}
          onProjectChange={(project) => {
            setTargetLine(null);
            setJumpNotice("");
            setSelectedProject(project);
          }}
          onRefresh={() => activePane === "problems" ? loadProjectProblems(selectedProject) : loadProjectFiles(selectedProject)}
          onFileFilterChange={setFileFilter}
          onSelectFile={(path) => {
            setTargetLine(null);
            setJumpNotice("");
            setSelectedPath(path);
          }}
          onProblemOpen={(problem) => openEditorTarget(problem.target, { source: problem.source || "problems" })}
          onLoadProblems={() => loadProjectProblems(selectedProject)}
          onOpenSandboxPreview={() => setSandboxPreviewOpen(true)}
          onStartSandbox={() => startSandbox()}
          onStopSandbox={stopSandbox}
          agentChangedPaths={agentChangedPaths}
        />

        <div
          className="code-workbench-sidebar-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize editor sidebar"
          tabIndex="0"
          onPointerDown={startSidebarResize}
          onKeyDown={handleSidebarResizeKey}
        />

        <main className="code-workbench-main">
          <CodeWorkbenchEditorHeader
            selectedProject={selectedProject}
            selectedPath={selectedPath}
            selectedFileMeta={selectedFileMeta}
            finalSequence={finalSequence}
            codeScanner={codeScanner}
            liveWriter={liveWriter}
            dirty={dirty}
            integrityFindings={integrityFindings}
            integrityActionStatus={integrityActionStatus}
            integrityBusy={integrityBusy}
            jumpNotice={jumpNotice}
            repairSending={repairSending}
            onStopScanner={() => stopCodeScanner("Scanner final detenido por humano.")}
            onFocusFirstIntegrity={() => focusIntegrityFinding(integrityFindings[0], { openRepair: true })}
            onFrozenSniper={() => runFrozenSniper()}
            onAcceptBaseline={() => acceptIntegrityBaseline()}
            onToggleRepair={() => setRepairOpen((current) => !current)}
            onOpenRepair={openRepairPanel}
          />

          <div
            className={`code-workbench-editor ${lock.locked ? "is-locked" : ""} ${liveWriter.active ? "is-writing" : ""} ${codeScanner.active ? "is-scanning" : ""} ${visibleIntegrityFindings.length ? "has-integrity-findings" : ""} ${visibleAgentChangeMarker ? "has-agent-change" : ""}`}
            style={{
              "--scanner-x": `${Math.min(720, Math.max(0, codeScanner.column) * CODE_SCANNER_CHAR_WIDTH_PX)}px`,
              "--scanner-y": `${Math.max(0, codeScanner.visibleRow) * CODE_SCANNER_LINE_HEIGHT_PX}px`,
              "--scanner-progress": `${Math.max(0, Math.min(100, codeScanner.percent))}%`,
              "--agent-change-y": `${visibleAgentChangeMarker?.y || 14}px`,
            }}
          >
            <CodeWorkbenchGutter gutterRef={gutterRef} lineNumbers={lineNumbers} targetLine={targetLine} visibleIntegrityLines={visibleIntegrityLines} agentChangeLine={visibleAgentChangeMarker?.line || null} activeIssueTarget={activeIssueTarget} onTargetClick={() => setRepairOpen(true)} />
            <CodeWorkbenchTextarea editorRef={editorRef} draft={draft} readOnly={lock.locked || liveWriter.active || codeScanner.active || !selectedPath} selectedPath={selectedPath} selectedProject={selectedProject} onDraftChange={handleDraftChange} onEditorScroll={handleEditorScroll} />
            <CodeWorkbenchEditorOverlays
              visibleIntegrityMarkers={visibleIntegrityMarkers}
              lock={lock}
              liveWriter={liveWriter}
              finalSequence={finalSequence}
              codeScanner={codeScanner}
            />
            {visibleAgentChangeMarker ? (
              <div className="code-workbench-agent-change-beam" aria-hidden="true">
                <span>{visibleAgentChangeMarker.message}</span>
              </div>
            ) : null}
            {repairOpen ? (
              <CodeWorkbenchRepairBubble
                target={activeIssueTarget}
                progressVisible={repairProgressVisible}
                progress={repairProgress}
                structureLabel={repairStructureLabel}
                instruction={repairInstruction}
                sending={repairSending}
                dirty={dirty}
                locked={lock.locked}
                lockMessage={lock.message}
                onClose={() => setRepairOpen(false)}
                onInstructionChange={setRepairInstruction}
                onLaunch={launchRepairAgent}
                onResetPrompt={() => setRepairInstruction("Repara este error en esta linea y valida que el punto rojo desaparezca.")}
              />
            ) : null}
          </div>

          <CodeWorkbenchActions
            canSave={canSave}
            saving={saving}
            selectedProject={selectedProject}
            selectedPath={selectedPath}
            loadingFile={loadingFile}
            liveWriterActive={liveWriter.active}
            finalSequenceActive={finalSequence.active}
            scannerActive={codeScanner.active}
            dirty={dirty}
            lock={lock}
            integrityBusy={integrityBusy}
            integrityFindings={integrityFindings}
            runtimeTruth={runtimeTruth}
            runtimeTruthBusy={runtimeTruthBusy}
            error={error}
            repairStatus={repairStatus}
            onSave={handleSave}
            onReloadFile={() => selectedProject && selectedPath && loadProjectFile(selectedProject, selectedPath)}
            onToggleScanner={() => codeScanner.active ? stopCodeScanner("Scanner final detenido por humano.") : launchCodeScanner()}
            onScanIntegrity={() => scanIntegrity()}
            onReleaseRuntimeZombie={() => releaseRuntimeZombie(selectedProject)}
          />

          <CodeWorkbenchAgentChat
            selectedProject={selectedProject}
            selectedPath={selectedPath}
            selectedFileMeta={selectedFileMeta}
            lock={lock}
            messages={agentChatMessages}
            events={agentChatEvents}
            draft={agentChatDraft}
            sending={agentChatSending}
            open={agentChatOpen}
            onDraftChange={setAgentChatDraft}
            onSubmit={handleAgentChatSubmit}
            onClear={clearAgentChat}
            onToggleOpen={() => setAgentChatOpen((current) => !current)}
            automation={agentChatPilot}
            onDelegateAssist={() => runVisibleAgentDelegation()}
          />

          <CodeWorkbenchTerminal
            activePane={activePane}
            terminalLines={terminalLines}
            onPaneChange={setActivePane}
          />

          <CodeWorkbenchSandboxModal
            open={sandboxPreviewOpen}
            sandbox={sandbox}
            selectedProject={selectedProject}
            onRefresh={() => loadSandbox(selectedProject, { silent: true })}
            onClose={() => setSandboxPreviewOpen(false)}
          />
        </main>
      </div>
    </section>
  );
}
