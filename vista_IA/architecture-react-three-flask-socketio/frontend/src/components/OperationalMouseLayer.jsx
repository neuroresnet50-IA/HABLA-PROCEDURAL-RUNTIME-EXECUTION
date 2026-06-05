import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";

const TOOLS = [
  {
    id: "scanner",
    label: "Scanner",
    title: "Scanner final",
    evidence: "runtime/artifacts/final_code_scanner_report.json",
  },
  {
    id: "broom",
    label: "Escoba",
    title: "Escoba runtime",
    evidence: "runtime/artifacts/broom/latest.json",
  },
  {
    id: "web_research",
    label: "Research",
    title: "Web research",
    evidence: "runtime/artifacts/web_research/*.json",
  },
  {
    id: "typewriter",
    label: "Typewriter",
    title: "Typewriter final",
    evidence: "runtime/artifacts/final_typewriter_report.json",
  },
  {
    id: "integrity",
    label: "Integrity",
    title: "Integrity scan",
    evidence: "runtime/artifacts/file_integrity_report.json",
  },
  {
    id: "lace_gate",
    label: "LACE",
    title: "LACE closure gate",
    evidence: "runtime/task_queue.json + docs/lace_cycles",
  },
];

const TOOL_LOOKUP = new Map(TOOLS.map((tool) => [tool.id, tool]));
const EDITOR_AUTONOMY_TARGETS = {
  copy_evidence: { selector: '[data-editor-autonomy-action="copy_evidence"]', label: "copiar evidencia" },
  send_repair: { selector: '[data-editor-autonomy-action="send_repair"]', label: "enviar reparador" },
  minimize_certificate: { selector: '[data-editor-autonomy-action="minimize_certificate"]', label: "minimizar certificado" },
  close_certificate: { selector: '[data-editor-autonomy-action="close_certificate"]', label: "cerrar certificado" },
  open_supervisor: { selector: '[data-editor-autonomy-action="open_supervisor"]', label: "ver supervisor" },
  restore_certificate: { selector: '[data-editor-autonomy-action="restore_certificate"]', label: "restaurar certificado" },
};

function normalizeEditorAutonomyAction(action) {
  return String(action || "auto_closure").trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function findEditorAutonomyTarget(action) {
  const normalized = normalizeEditorAutonomyAction(action);
  if (normalized === "auto" || normalized === "auto_closure" || normalized === "closure") {
    const ordered = ["send_repair", "open_supervisor", "minimize_certificate", "close_certificate"];
    for (const key of ordered) {
      const candidate = EDITOR_AUTONOMY_TARGETS[key];
      const element = document.querySelector(candidate.selector);
      if (clickableElementReady(element)) return { key, ...candidate, element };
    }
    return null;
  }
  const target = EDITOR_AUTONOMY_TARGETS[normalized];
  if (!target) return null;
  const element = document.querySelector(target.selector);
  if (!clickableElementReady(element)) return null;
  return { key: normalized, ...target, element };
}

function compactPayload(payload) {
  if (!payload || typeof payload !== "object") return String(payload || "");
  try {
    return JSON.stringify(payload, null, 2).slice(0, 2800);
  } catch {
    return String(payload).slice(0, 2800);
  }
}

function apiErrorMessage(payload, fallback) {
  if (!payload || typeof payload !== "object") return fallback;
  return payload.message || payload.error || fallback;
}

function encodeProject(projectId) {
  return encodeURIComponent(String(projectId || "").trim());
}

function actionExpired(action) {
  const raw = String(action?.expiresAt || "").trim();
  if (!raw) return false;
  const value = Date.parse(raw);
  return Number.isFinite(value) && value <= Date.now();
}

function getLacePayload(payload) {
  if (!payload || typeof payload !== "object") return null;
  return payload.plan?.statusAfter || payload.plan?.statusBefore || payload.statusAfter || payload.statusBefore || payload;
}

function getLaceGraph(payload) {
  const source = getLacePayload(payload);
  return source?.graph && typeof source.graph === "object" ? source.graph : null;
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function clickableElementReady(element) {
  if (!(element instanceof HTMLElement)) return false;
  if (element.hasAttribute("disabled") || element.getAttribute("aria-disabled") === "true") return false;
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

async function waitForClickableElement(selector, { timeoutMs = 2200, intervalMs = 80 } = {}) {
  const startedAt = Date.now();
  while (Date.now() - startedAt <= timeoutMs) {
    const element = document.querySelector(selector);
    if (clickableElementReady(element)) return element;
    await wait(intervalMs);
  }
  const element = document.querySelector(selector);
  return clickableElementReady(element) ? element : null;
}

async function waitForCondition(predicate, { timeoutMs = 2200, intervalMs = 50 } = {}) {
  const startedAt = Date.now();
  while (Date.now() - startedAt <= timeoutMs) {
    if (predicate()) return true;
    await wait(intervalMs);
  }
  return Boolean(predicate());
}

function pointHitsElement(element, rect) {
  const x = rect.left + rect.width / 2;
  const y = rect.top + rect.height / 2;
  const hit = document.elementFromPoint(x, y);
  return {
    ok: hit === element || Boolean(hit && element.contains(hit)),
    hitTag: hit?.tagName?.toLowerCase?.() || "",
    hitText: String(hit?.textContent || "").trim().slice(0, 100),
  };
}

function dispatchMouseLikeEvent(element, type, rect) {
  const eventOptions = {
    bubbles: true,
    cancelable: true,
    composed: true,
    view: window,
    button: 0,
    buttons: type.includes("down") ? 1 : 0,
    clientX: rect.left + rect.width / 2,
    clientY: rect.top + rect.height / 2,
  };
  if (type.startsWith("pointer") && typeof window.PointerEvent === "function") {
    element.dispatchEvent(new window.PointerEvent(type, { ...eventOptions, pointerId: 1, pointerType: "mouse", isPrimary: true }));
    return;
  }
  element.dispatchEvent(new MouseEvent(type.replace("pointer", "mouse"), eventOptions));
}

async function clickRealElement(element, { actionId = "", selector = "", label = "" } = {}) {
  if (!clickableElementReady(element)) {
    return { ok: false, error: "target_not_clickable", actionId, selector, label };
  }
  element.scrollIntoView({ block: "center", inline: "center", behavior: "auto" });
  if (typeof element.focus === "function") element.focus({ preventScroll: true });
  await wait(80);
  const rect = element.getBoundingClientRect();
  element.dataset.operationalAutoClick = "true";
  dispatchMouseLikeEvent(element, "pointerdown", rect);
  dispatchMouseLikeEvent(element, "mousedown", rect);
  await wait(55);
  dispatchMouseLikeEvent(element, "pointerup", rect);
  dispatchMouseLikeEvent(element, "mouseup", rect);
  element.click();
  window.setTimeout(() => {
    delete element.dataset.operationalAutoClick;
  }, 160);
  return {
    ok: true,
    actionId,
    selector,
    label,
    tagName: element.tagName.toLowerCase(),
    text: String(element.textContent || "").trim().slice(0, 120),
    rect: { x: Math.round(rect.left), y: Math.round(rect.top), width: Math.round(rect.width), height: Math.round(rect.height) },
    eventSequence: ["pointerdown", "mousedown", "pointerup", "mouseup", "click"],
  };
}

export default function OperationalMouseLayer({ socketUrl = "", selectedProject = "", autonomousMode = false }) {
  const apiBase = String(socketUrl || "").replace(/\/$/, "");
  const [projectId, setProjectId] = useState(String(selectedProject || ""));
  const [activeTool, setActiveTool] = useState(null);
  const [busyTool, setBusyTool] = useState("");
  const [toolResult, setToolResult] = useState(null);
  const [minimizedTools, setMinimizedTools] = useState({});
  const [researchQuery, setResearchQuery] = useState("arquitectura segura IA agente autonomo evidencia runtime");
  const [researchUrl, setResearchUrl] = useState("");
  const [laceRepairBusy, setLaceRepairBusy] = useState(false);
  const [cursor, setCursor] = useState({ x: 24, y: 24, label: "idle", active: false });
  const [activeAction, setActiveAction] = useState(null);
  const [actionTrace, setActionTrace] = useState([]);
  const projectIdRef = useRef(String(selectedProject || ""));
  const activeToolRef = useRef(null);
  const busyToolRef = useRef("");
  const toolResultRef = useRef(null);
  const lastDockClickRef = useRef(null);
  const lastRunClickRef = useRef(null);
  const lastMinimizeClickRef = useRef(null);
  const lastTrayCloseClickRef = useRef(null);
  const autoCloseTimersRef = useRef(new Map());
  const handledActionsRef = useRef(new Set());
  const pendingActionsRef = useRef([]);
  const executingRef = useRef(false);
  const runToolRef = useRef(null);
  const pendingAutoRunRef = useRef(null);

  const activeToolConfig = activeTool ? TOOL_LOOKUP.get(activeTool) : null;

  useEffect(() => {
    activeToolRef.current = activeTool;
  }, [activeTool]);

  useEffect(() => {
    busyToolRef.current = busyTool;
  }, [busyTool]);

  useEffect(() => {
    toolResultRef.current = toolResult;
  }, [toolResult]);

  useEffect(() => () => {
    autoCloseTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    autoCloseTimersRef.current.clear();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      const nextProject = String(selectedProject);
      projectIdRef.current = nextProject;
      setProjectId(nextProject);
    }
  }, [selectedProject]);

  const pushActionTrace = useCallback((step, status, message, evidence = "") => {
    const item = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      step,
      status,
      message,
      evidence,
      at: new Date().toISOString(),
    };
    setActionTrace((current) => [...current, item].slice(-12));
  }, []);

  const beginActionTrace = useCallback((action, toolId, projectSlug) => {
    const actionId = String(action?.actionId || "");
    setActiveAction({
      actionId,
      toolId,
      projectSlug,
      reason: String(action?.reason || "accion runtime"),
      treeId: action?.behaviorTree?.treeId || "BT-local-fallback",
      treeSource: action?.governedBy || (action?.behaviorTree ? "observer_behavior_tree" : "frontend_fallback"),
      startedAt: new Date().toISOString(),
    });
    setActionTrace([]);
    pushActionTrace("accion", "running", `Runtime solicito ${TOOL_LOOKUP.get(toolId)?.label || toolId}.`, projectSlug || "sin proyecto");
  }, [pushActionTrace]);


  const upsertMinimizedTool = useCallback((toolId, patch = {}) => {
    const tool = TOOL_LOOKUP.get(toolId);
    if (!tool) return;
    const now = new Date().toISOString();
    setMinimizedTools((current) => ({
      ...current,
      [toolId]: {
        toolId,
        label: tool.label,
        title: tool.title,
        evidence: tool.evidence,
        projectId: projectIdRef.current,
        status: "open",
        payload: {},
        createdAt: current[toolId]?.createdAt || now,
        updatedAt: now,
        ...(current[toolId] || {}),
        ...patch,
        updatedAt: now,
      },
    }));
  }, []);

  const closeActiveTool = useCallback((toolId, event = null) => {
    if (!TOOL_LOOKUP.has(toolId)) return;
    lastTrayCloseClickRef.current = {
      toolId,
      kind: "active_modal",
      at: Date.now(),
      trusted: Boolean(event?.isTrusted),
    };
    if (activeToolRef.current === toolId) activeToolRef.current = null;
    setActiveTool((current) => (current === toolId ? null : current));
    pushActionTrace("modal", "completed", "Modal cerrado por ciclo operativo.", toolId);
  }, [pushActionTrace]);

  const minimizeTool = useCallback((toolId, event = null, patch = {}) => {
    const tool = TOOL_LOOKUP.get(toolId);
    if (!tool) return;
    const result = toolResultRef.current?.toolId === toolId ? toolResultRef.current : null;
    lastMinimizeClickRef.current = {
      toolId,
      at: Date.now(),
      trusted: Boolean(event?.isTrusted),
      text: String(event?.currentTarget?.textContent || "Minimizar").trim().slice(0, 120),
    };
    const recentlyStartedRun = lastRunClickRef.current?.toolId === toolId && Date.now() - Number(lastRunClickRef.current?.at || 0) < 5000;
    upsertMinimizedTool(toolId, {
      status: patch.status || (busyToolRef.current === toolId || recentlyStartedRun ? "running" : result?.status || "open"),
      payload: patch.payload || result?.payload || {},
      actionId: patch.actionId || "",
      projectId: patch.projectId || projectIdRef.current,
      reason: patch.reason || "modal_minimized",
      minimizedAt: new Date().toISOString(),
    });
    if (activeToolRef.current === toolId) activeToolRef.current = null;
    setActiveTool((current) => (current === toolId ? null : current));
    pushActionTrace("modal", "completed", "Modal recogido en bandeja inferior.", toolId);
  }, [pushActionTrace, upsertMinimizedTool]);

  const reopenMinimizedTool = useCallback((toolId, event = null) => {
    const card = minimizedTools[toolId];
    if (!card || !TOOL_LOOKUP.has(toolId)) return;
    lastDockClickRef.current = {
      toolId,
      at: Date.now(),
      trusted: Boolean(event?.isTrusted),
      text: "restaurar tarjeta operativa",
    };
    setMinimizedTools((current) => {
      const next = { ...current };
      delete next[toolId];
      return next;
    });
    activeToolRef.current = toolId;
    setActiveTool(toolId);
    if (card.payload && Object.keys(card.payload).length) {
      setToolResult({ toolId, status: card.status || "running", payload: card.payload });
    }
    pushActionTrace("modal", "completed", "Tarjeta recogida restaurada a modal.", toolId);
  }, [minimizedTools, pushActionTrace]);

  const closeMinimizedTool = useCallback((toolId, event = null) => {
    if (!TOOL_LOOKUP.has(toolId)) return;
    lastTrayCloseClickRef.current = {
      toolId,
      kind: "minimized_card",
      at: Date.now(),
      trusted: Boolean(event?.isTrusted),
    };
    setMinimizedTools((current) => {
      const next = { ...current };
      delete next[toolId];
      return next;
    });
    if (toolResultRef.current?.toolId === toolId) {
      setToolResult(null);
    }
    pushActionTrace("modal", "completed", "Tarjeta operativa cerrada con evidencia persistida.", toolId);
  }, [pushActionTrace]);

  const autoCloseCompletedTool = useCallback((toolId) => {
    const tool = TOOL_LOOKUP.get(toolId);
    if (!tool) return;
    const previous = autoCloseTimersRef.current.get(toolId);
    if (previous) window.clearTimeout(previous);
    const timer = window.setTimeout(async () => {
      const closeSelector = `[data-operational-minimized-close="${toolId}"]`;
      const closeButton = await waitForClickableElement(closeSelector, { timeoutMs: 3600, intervalMs: 80 });
      if (!(closeButton instanceof HTMLElement)) {
        pushActionTrace("BT close completed", "blocked", "No se encontro tarjeta recogida para cerrar.", closeSelector);
        return;
      }
      const rect = closeButton.getBoundingClientRect();
      setCursor({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, label: `cerrar ${tool.label}`, active: true });
      const startedAt = Date.now();
      pushActionTrace("BT close completed", "running", "Cursor cierra tarjeta completada.", closeSelector);
      const click = await clickRealElement(closeButton, { selector: closeSelector, label: `tray-close:${toolId}` });
      if (!click.ok) {
        pushActionTrace("BT close completed", "blocked", "La tarjeta completada no acepto click de cierre.", click.error || closeSelector);
        return;
      }
      const accepted = await waitForCondition(
        () => lastTrayCloseClickRef.current?.toolId === toolId && Number(lastTrayCloseClickRef.current?.at || 0) >= startedAt,
        { timeoutMs: 1200, intervalMs: 40 },
      );
      pushActionTrace("BT close completed", accepted ? "completed" : "blocked", accepted ? "Tarjeta completada cerrada por el cursor." : "React no confirmo cierre de tarjeta.", closeSelector);
      window.setTimeout(() => setCursor((current) => ({ ...current, active: false })), 260);
    }, 1400);
    autoCloseTimersRef.current.set(toolId, timer);
  }, [pushActionTrace]);

  const callApi = useCallback(async (path, options = {}) => {
    const response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = { ok: false, error: "invalid_json_response" };
    }
    if (!response.ok || payload?.ok === false) {
      const error = new Error(apiErrorMessage(payload, `HTTP ${response.status}`));
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    return payload;
  }, [apiBase]);

  const recordActionResult = useCallback(async (actionId, status, result) => {
    if (!actionId) return;
    try {
      await callApi(`/api/ui-actions/${encodeURIComponent(actionId)}/result`, {
        method: "POST",
        body: JSON.stringify({ status, result }),
      });
    } catch {
      // UI action history is useful evidence, but tool execution should not fail if history persistence is busy.
    }
  }, [callApi]);

  const ackAction = useCallback(async (actionId) => {
    if (!actionId) return;
    try {
      await callApi(`/api/ui-actions/${encodeURIComponent(actionId)}/ack`, {
        method: "POST",
        body: JSON.stringify({ client: "operational_mouse" }),
      });
    } catch {
      // Ack is audit evidence; a busy backend should not prevent the visible tool action.
    }
  }, [callApi]);

  const runTool = useCallback(async (toolId, { actionId = "", projectIdOverride = "" } = {}) => {
    const tool = TOOL_LOOKUP.get(toolId);
    if (!tool) return null;
    const slug = String(projectIdOverride || projectIdRef.current || "").trim();
    if (slug) {
      projectIdRef.current = slug;
      setProjectId(slug);
    }
    if (!slug) {
      const result = { ok: false, error: "project_required", message: "Selecciona un proyecto workspace." };
      setToolResult({ toolId, status: "blocked", payload: result });
      pushActionTrace("proceso", "blocked", "No hay proyecto activo para ejecutar la herramienta.", "project_required");
      await recordActionResult(actionId, "blocked", result);
      return result;
    }

    const runningPayload = { message: `${tool.title} en ejecucion real...`, projectId: slug, startedAt: new Date().toISOString() };
    setBusyTool(toolId);
    setToolResult({ toolId, status: "running", payload: runningPayload });
    upsertMinimizedTool(toolId, { status: "running", payload: runningPayload, actionId, projectId: slug, startedAt: runningPayload.startedAt });
    pushActionTrace("proceso", "running", `${tool.title} llamo endpoint real.`, slug);
    try {
      let payload;
      if (toolId === "scanner") {
        payload = await callApi(`/api/projects/${encodeProject(slug)}/code-scanner`, { method: "POST", body: "{}" });
      } else if (toolId === "broom") {
        payload = await callApi(`/api/projects/${encodeProject(slug)}/broom`, {
          method: "POST",
          body: JSON.stringify({ phase: "ui_operational_mouse", reason: "operational_mouse_tool_dock" }),
        });
      } else if (toolId === "web_research") {
        payload = await callApi(`/api/projects/${encodeProject(slug)}/web-research/record`, {
          method: "POST",
          body: JSON.stringify({ query: researchQuery, source: "operational_mouse" }),
        });
        if (payload?.url) setResearchUrl(payload.url);
      } else if (toolId === "typewriter") {
        payload = await callApi(`/api/projects/${encodeProject(slug)}/typewriter-final`, {
          method: "POST",
          body: JSON.stringify({ trigger: "operational_mouse" }),
        });
      } else if (toolId === "integrity") {
        payload = await callApi(`/api/projects/${encodeProject(slug)}/integrity/scan`, { method: "POST", body: "{}" });
      } else if (toolId === "lace_gate") {
        payload = await callApi(`/api/projects/${encodeProject(slug)}/lace-dependency-status`);
      }
      const status = payload?.ok === false || (toolId === "lace_gate" && payload?.lace?.closureBlocked) ? "blocked" : "completed";
      setToolResult({ toolId, status, payload });
      upsertMinimizedTool(toolId, { status, payload, actionId, projectId: slug, completedAt: new Date().toISOString() });
      pushActionTrace("resultado", status, status === "completed" ? "Herramienta termino con evidencia." : "Herramienta bloqueo cierre con evidencia.", payload?.reportPath || payload?.artifactPath || payload?.relativePath || payload?.evidence?.taskQueue || "resultado runtime");
      await recordActionResult(actionId, status, payload);
      if (status === "completed") autoCloseCompletedTool(toolId);
      return payload;
    } catch (error) {
      const payload = error?.payload || { ok: false, error: error?.message || "tool_failed", status: error?.status };
      const status = error?.status === 423 ? "blocked" : "failed";
      setToolResult({ toolId, status, payload });
      upsertMinimizedTool(toolId, { status, payload, actionId, projectId: slug, completedAt: new Date().toISOString() });
      pushActionTrace("resultado", status, payload?.message || payload?.error || "La herramienta no pudo terminar.", String(error?.status || "sin status"));
      await recordActionResult(actionId, status, payload);
      return payload;
    } finally {
      setBusyTool("");
    }
  }, [autoCloseCompletedTool, callApi, pushActionTrace, recordActionResult, researchQuery, upsertMinimizedTool]);

  useEffect(() => {
    runToolRef.current = runTool;
  }, [runTool]);

  const repairLaceDependencies = useCallback(async ({ dryRun = true } = {}) => {
    const slug = String(projectId || "").trim();
    if (!slug) {
      setToolResult({ toolId: "lace_gate", status: "blocked", payload: { ok: false, error: "project_required", message: "Selecciona un proyecto workspace." } });
      return null;
    }
    setLaceRepairBusy(true);
    setToolResult({ toolId: "lace_gate", status: "running", payload: { message: dryRun ? "Calculando reparacion LACE..." : "Encolando ciclos LACE faltantes..." } });
    try {
      const payload = await callApi(`/api/projects/${encodeProject(slug)}/lace-dependency-repair`, {
        method: "POST",
        body: JSON.stringify({ dryRun, confirm: dryRun ? "" : "ENQUEUE_LACE" }),
      });
      setToolResult({ toolId: "lace_gate", status: payload?.ok ? (dryRun ? "planned" : "completed") : "blocked", payload });
      return payload;
    } catch (error) {
      const payload = error?.payload || { ok: false, error: error?.message || "lace_repair_failed", status: error?.status };
      setToolResult({ toolId: "lace_gate", status: error?.status === 423 ? "blocked" : "failed", payload });
      return payload;
    } finally {
      setLaceRepairBusy(false);
    }
  }, [callApi, projectId]);

  const openTool = useCallback((toolId, event = null) => {
    if (!TOOL_LOOKUP.has(toolId)) return;
    lastDockClickRef.current = {
      toolId,
      at: Date.now(),
      trusted: Boolean(event?.isTrusted),
      text: String(event?.currentTarget?.textContent || TOOL_LOOKUP.get(toolId)?.label || toolId).trim().slice(0, 140),
    };
    activeToolRef.current = toolId;
    setActiveTool(toolId);
    setToolResult(null);
    pushActionTrace("BT dock handler", "completed", "React acepto el click del boton de herramienta.", toolId);
  }, [pushActionTrace]);

  const handleRunToolButtonClick = useCallback((toolId, event = null) => {
    if (!TOOL_LOOKUP.has(toolId)) return;
    const pending = pendingAutoRunRef.current && pendingAutoRunRef.current.toolId === toolId
      ? pendingAutoRunRef.current
      : { actionId: "", projectId: projectIdRef.current };
    pendingAutoRunRef.current = null;
    lastRunClickRef.current = {
      toolId,
      at: Date.now(),
      trusted: Boolean(event?.isTrusted),
      text: String(event?.currentTarget?.textContent || "Ejecutar herramienta real").trim().slice(0, 140),
    };
    pushActionTrace("BT modal handler", "completed", "React acepto el click del boton interno del modal.", toolId);
    void runTool(toolId, { actionId: pending.actionId || "", projectIdOverride: pending.projectId || "" });
  }, [pushActionTrace, runTool]);

  const runEditorAutonomyAction = useCallback(async (detail = {}) => {
    const actionName = normalizeEditorAutonomyAction(detail?.action || "auto_closure");
    const actionId = String(detail?.actionId || `editor-${actionName}-${Date.now()}`);
    const projectSlug = String(detail?.projectSlug || selectedProject || projectIdRef.current || "").trim();
    const source = String(detail?.source || "section-06-editor");
    const isAutonomousPolicy = source === "agent-studio-closure-policy" || detail?.trigger === "autonomous_closure_policy";
    setActiveAction({
      actionId,
      toolId: isAutonomousPolicy ? "certificado-runtime" : "06-editor",
      projectSlug,
      reason: String(detail?.reason || (isAutonomousPolicy ? "closure_policy_autonomy" : "editor_modal_autonomy")),
      treeId: isAutonomousPolicy ? "BT-closure-policy-autonomy" : "BT-editor-modal-autonomy",
      treeSource: source,
      startedAt: new Date().toISOString(),
    });
    setActionTrace([]);
    pushActionTrace(
      isAutonomousPolicy ? "politica autonoma" : "editor autonomia",
      "running",
      isAutonomousPolicy ? `El sistema decidio ejecutar click real: ${actionName}.` : `Solicitud de click real: ${actionName}.`,
      projectSlug || "sin proyecto",
    );

    let target = findEditorAutonomyTarget(actionName);
    if (!target?.element && actionName !== "restore_certificate") {
      const restoreTarget = findEditorAutonomyTarget("restore_certificate");
      if (restoreTarget?.element) {
        const restoreRect = restoreTarget.element.getBoundingClientRect();
        const restoreHit = pointHitsElement(restoreTarget.element, restoreRect);
        if (restoreHit.ok) {
          setCursor({ x: restoreRect.left + restoreRect.width / 2, y: restoreRect.top + restoreRect.height / 2, label: restoreTarget.label, active: true });
          pushActionTrace("restaurar modal", "running", "Certificado estaba minimizado; restaurando antes del click objetivo.", restoreTarget.selector);
          await wait(300);
          const restoreClick = await clickRealElement(restoreTarget.element, { actionId, selector: restoreTarget.selector, label: "editor:restore_certificate" });
          pushActionTrace("restaurar modal", restoreClick.ok ? "completed" : "blocked", restoreClick.ok ? "Certificado restaurado con click real." : "No se pudo restaurar el certificado minimizado.", restoreClick.text || restoreClick.error || restoreTarget.selector);
          if (restoreClick.ok) {
            await waitForCondition(() => document.querySelector('[data-editor-autonomy-modal="closure-certificate"]'), { timeoutMs: 1800, intervalMs: 60 });
            target = findEditorAutonomyTarget(actionName);
          }
        } else {
          pushActionTrace("restaurar modal", "blocked", "La tarjeta minimizada esta cubierta por otra capa.", `${restoreTarget.selector} hit=${restoreHit.hitTag}`);
        }
      }
    }

    if (!target?.element) {
      pushActionTrace("buscar boton", "blocked", "No hay modal de cierre clickeable para esta accion.", actionName);
      setCursor((current) => ({ ...current, active: false }));
      return;
    }

    const rect = target.element.getBoundingClientRect();
    const hit = pointHitsElement(target.element, rect);
    if (!hit.ok) {
      pushActionTrace("foco boton", "blocked", "El boton objetivo esta cubierto por otra capa.", `${target.selector} hit=${hit.hitTag}`);
      setCursor((current) => ({ ...current, active: false }));
      return;
    }

    setCursor({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, label: target.label, active: true });
    pushActionTrace("foco boton", "completed", "Cursor ubicado sobre boton real del certificado.", target.selector);
    await wait(420);

    const click = await clickRealElement(target.element, { actionId, selector: target.selector, label: `editor:${target.key}` });
    pushActionTrace("click real", click.ok ? "completed" : "blocked", click.ok ? `Click aceptado: ${target.label}.` : "El boton no acepto el click real.", click.text || click.error || target.selector);
    window.setTimeout(() => setCursor((current) => ({ ...current, active: false })), 360);
  }, [pushActionTrace, selectedProject]);

  useEffect(() => {
    if (!autonomousMode) return undefined;
    const handler = (event) => {
      void runEditorAutonomyAction(event?.detail || {});
    };
    window.addEventListener("habla:editor-autonomy-action", handler);
    return () => window.removeEventListener("habla:editor-autonomy-action", handler);
  }, [autonomousMode, runEditorAutonomyAction]);

  const runBehaviorTreeAction = useCallback(async (action) => {
    const toolId = String(action?.targetTool || "").replace(/-/g, "_");
    if (!TOOL_LOOKUP.has(toolId)) return;
    const actionId = String(action.actionId || "");
    const actionProject = String(action?.projectSlug || action?.projectId || selectedProject || projectIdRef.current || "").trim();
    if (actionProject) {
      projectIdRef.current = actionProject;
      setProjectId(actionProject);
    }
    beginActionTrace(action, toolId, actionProject);
    const tree = action?.behaviorTree || null;
    const treeNodes = Array.isArray(tree?.root?.nodes) ? tree.root.nodes : [];
    const treeNodeIds = new Set(treeNodes.map((node) => String(node?.id || "")));
    pushActionTrace("BT plan", tree ? "completed" : "running", tree ? "Plan recibido desde Observer plane." : "Usando fallback local; accion vieja sin Behavior Tree persistido.", tree?.treeId || "BT-local-fallback");
    pushActionTrace("BT root", "running", "Sequence: operar herramienta con UI real.", toolId);

    const fail = async (node, message, result) => {
      pushActionTrace(node, "blocked", message, result?.selector || result?.error || "sin evidencia");
      await recordActionResult(actionId, "blocked", { ok: false, node, message, ...(result || {}) });
      setCursor((current) => ({ ...current, active: false }));
    };

    if (tree && !treeNodeIds.has("click_tool_button")) {
      await fail("BT plan", "El Behavior Tree del Observer no contiene nodo click_tool_button.", { error: "invalid_behavior_tree", treeId: tree.treeId });
      return;
    }
    if (tree && action.autoRun !== false && !treeNodeIds.has("click_execute_button")) {
      await fail("BT plan", "El Behavior Tree del Observer no contiene nodo click_execute_button.", { error: "invalid_behavior_tree", treeId: tree.treeId });
      return;
    }

    const dockSelector = `[data-operational-tool="${toolId}"]`;
    pushActionTrace("BT find tool", "running", "Buscar boton real de herramienta.", dockSelector);
    const toolButton = await waitForClickableElement(dockSelector, { timeoutMs: 2600, intervalMs: 60 });
    if (!(toolButton instanceof HTMLElement)) {
      await fail("BT find tool", "No existe boton real clickeable en el dock.", { selector: dockSelector, error: "tool_button_missing" });
      return;
    }
    pushActionTrace("BT find tool", "completed", "Boton real encontrado.", dockSelector);

    await ackAction(actionId);
    const toolRect = toolButton.getBoundingClientRect();
    const toolHit = pointHitsElement(toolButton, toolRect);
    if (!toolHit.ok) {
      await fail("BT focus tool", "El boton real esta cubierto por otra capa.", { selector: dockSelector, error: "tool_button_occluded", hit: toolHit });
      return;
    }
    setCursor({ x: toolRect.left + toolRect.width / 2, y: toolRect.top + toolRect.height / 2, label: TOOL_LOOKUP.get(toolId)?.label || toolId, active: true });
    pushActionTrace("BT focus tool", "completed", "Cursor ubicado en el recuadro real de herramienta.", `${Math.round(toolRect.left)},${Math.round(toolRect.top)}`);
    await wait(520);

    const dockClickStartedAt = Date.now();
    pushActionTrace("BT click tool", "running", "Click real sobre boton de herramienta.", dockSelector);
    const dockClick = await clickRealElement(toolButton, { actionId, selector: dockSelector, label: `dock:${toolId}` });
    if (!dockClick.ok) {
      await fail("BT click tool", "El boton de herramienta no acepto click real.", dockClick);
      return;
    }
    const dockHandlerAccepted = await waitForCondition(
      () => lastDockClickRef.current?.toolId === toolId && Number(lastDockClickRef.current?.at || 0) >= dockClickStartedAt,
      { timeoutMs: 1200, intervalMs: 40 },
    );
    if (!dockHandlerAccepted) {
      await fail("BT click tool", "React no confirmo el handler del boton de herramienta.", { selector: dockSelector, error: "dock_handler_not_confirmed", dockClick });
      return;
    }
    pushActionTrace("BT click tool", "completed", "Click de herramienta aceptado; modal debe abrir.", dockClick.text || dockSelector);

    if (action.autoRun === false) {
      await recordActionResult(actionId, "completed", { ok: true, message: "behavior_tree_modal_opened", targetTool: toolId, dockClick });
      pushActionTrace("BT complete", "completed", "Arbol termino en apertura de modal por configuracion.", toolId);
      return;
    }

    pendingAutoRunRef.current = { toolId, actionId, projectId: actionProject };
    const modalSelector = `[data-operational-modal-tool="${toolId}"]`;
    const runSelector = `[data-operational-run-button="${toolId}"]`;
    pushActionTrace("BT wait modal", "running", "Esperando modal real de herramienta.", modalSelector);
    const modalReady = await waitForCondition(() => activeToolRef.current === toolId && document.querySelector(modalSelector), { timeoutMs: 2600, intervalMs: 60 });
    if (!modalReady) {
      pendingAutoRunRef.current = null;
      await fail("BT wait modal", "El click del dock no abrio el modal real.", { selector: modalSelector, error: "modal_not_opened", dockClick });
      return;
    }
    pushActionTrace("BT wait modal", "completed", "Modal real abierto.", modalSelector);

    const runButton = await waitForClickableElement(runSelector, { timeoutMs: 4200, intervalMs: 70 });
    if (!(runButton instanceof HTMLElement)) {
      pendingAutoRunRef.current = null;
      await fail("BT find execute", "No existe boton interno clickeable para ejecutar.", { selector: runSelector, error: "run_button_missing", dockClick });
      return;
    }
    const runRect = runButton.getBoundingClientRect();
    const runHit = pointHitsElement(runButton, runRect);
    if (!runHit.ok) {
      pendingAutoRunRef.current = null;
      await fail("BT focus execute", "El boton interno esta cubierto por otra capa.", { selector: runSelector, error: "run_button_occluded", hit: runHit, dockClick });
      return;
    }
    setCursor({ x: runRect.left + runRect.width / 2, y: runRect.top + runRect.height / 2, label: TOOL_LOOKUP.get(toolId)?.label || toolId, active: true });
    pushActionTrace("BT focus execute", "completed", "Cursor ubicado sobre el boton interno real.", `${Math.round(runRect.left)},${Math.round(runRect.top)}`);
    await wait(520);

    const modalClickStartedAt = Date.now();
    pushActionTrace("BT click execute", "running", "Click real sobre boton interno del modal.", runSelector);
    const modalClick = await clickRealElement(runButton, { actionId, selector: runSelector, label: `modal-run:${toolId}` });
    if (!modalClick.ok) {
      pendingAutoRunRef.current = null;
      await fail("BT click execute", "El boton interno no acepto click real.", { ...modalClick, dockClick });
      return;
    }
    const modalHandlerAccepted = await waitForCondition(
      () => lastRunClickRef.current?.toolId === toolId && Number(lastRunClickRef.current?.at || 0) >= modalClickStartedAt,
      { timeoutMs: 1200, intervalMs: 40 },
    );
    if (!modalHandlerAccepted) {
      pendingAutoRunRef.current = null;
      await fail("BT click execute", "React no confirmo el handler del boton interno.", { selector: runSelector, error: "run_handler_not_confirmed", dockClick, modalClick });
      return;
    }
    pushActionTrace("BT click execute", "completed", "Click interno aceptado; proceso real entregado a la herramienta.", modalClick.text || runSelector);

    const minimizeSelector = `[data-operational-minimize-button="${toolId}"]`;
    const traySelector = `[data-operational-minimized-tool="${toolId}"]`;
    pushActionTrace("BT minimize modal", "running", "Recoger modal para que la herramienta trabaje en bandeja inferior.", minimizeSelector);
    const minimizeButton = await waitForClickableElement(minimizeSelector, { timeoutMs: 2600, intervalMs: 70 });
    if (minimizeButton instanceof HTMLElement) {
      const minimizeRect = minimizeButton.getBoundingClientRect();
      const minimizeHit = pointHitsElement(minimizeButton, minimizeRect);
      if (minimizeHit.ok) {
        setCursor({ x: minimizeRect.left + minimizeRect.width / 2, y: minimizeRect.top + minimizeRect.height / 2, label: "minimizar", active: true });
        await wait(360);
        const minimizeStartedAt = Date.now();
        const minimizeClick = await clickRealElement(minimizeButton, { actionId, selector: minimizeSelector, label: `modal-minimize:${toolId}` });
        const minimizeAccepted = minimizeClick.ok && await waitForCondition(
          () => lastMinimizeClickRef.current?.toolId === toolId && Number(lastMinimizeClickRef.current?.at || 0) >= minimizeStartedAt,
          { timeoutMs: 1200, intervalMs: 40 },
        );
        pushActionTrace("BT minimize modal", minimizeAccepted ? "completed" : "blocked", minimizeAccepted ? "Modal recogido con click real." : "React no confirmo minimizar modal.", minimizeSelector);
      } else {
        minimizeTool(toolId, null, { actionId, projectId: actionProject, reason: "minimize_button_occluded" });
        pushActionTrace("BT minimize modal", "blocked", "Boton de minimizar cubierto; se recogio por fallback seguro.", minimizeSelector);
      }
    } else {
      minimizeTool(toolId, null, { actionId, projectId: actionProject, reason: "minimize_button_missing" });
      pushActionTrace("BT minimize modal", "blocked", "No existe boton de minimizar; se recogio por fallback seguro.", minimizeSelector);
    }

    const trayReady = await waitForCondition(() => document.querySelector(traySelector), { timeoutMs: 1800, intervalMs: 60 });
    pushActionTrace("BT wait tray", trayReady ? "completed" : "blocked", trayReady ? "Tarea visible en bandeja mientras trabaja." : "La bandeja inferior no monto tarjeta de tarea.", traySelector);
    pushActionTrace("BT wait result", "running", "La herramienta sigue viva; el cursor queda libre para otra accion compatible.", traySelector);
    window.setTimeout(() => setCursor((current) => ({ ...current, active: false })), 360);
  }, [ackAction, beginActionTrace, minimizeTool, pushActionTrace, recordActionResult, selectedProject]);

  const drainActions = useCallback(async () => {
    if (executingRef.current || !autonomousMode) return;
    executingRef.current = true;
    try {
      while (pendingActionsRef.current.length && autonomousMode) {
        const action = pendingActionsRef.current.shift();
        await runBehaviorTreeAction(action);
      }
    } finally {
      executingRef.current = false;
    }
  }, [autonomousMode, runBehaviorTreeAction]);

  const enqueueAction = useCallback((action) => {
    if (!action || typeof action !== "object") return;
    if (action.requiresAutonomousMode && !autonomousMode) return;
    const actionId = String(action.actionId || `${action.targetTool}-${Date.now()}`);
    if (handledActionsRef.current.has(actionId)) return;
    if (actionExpired(action)) {
      handledActionsRef.current.add(actionId);
      void recordActionResult(actionId, "blocked", { ok: false, error: "ui_action_expired", expiresAt: action.expiresAt });
      return;
    }
    handledActionsRef.current.add(actionId);
    pendingActionsRef.current.push(action);
    void drainActions();
  }, [autonomousMode, drainActions]);

  useEffect(() => {
    if (!autonomousMode) return undefined;
    const socket = io(apiBase || undefined, { transports: ["polling"], upgrade: false });
    socket.on("ui:mouse-action", enqueueAction);
    return () => socket.disconnect();
  }, [apiBase, autonomousMode, enqueueAction]);

  useEffect(() => {
    if (!autonomousMode) return undefined;
    let cancelled = false;
    async function pollQueue() {
      try {
        const payload = await callApi("/api/ui-actions/queue");
        if (cancelled) return;
        (payload?.actions || []).forEach((action) => enqueueAction(action));
      } catch {
        // Polling is secondary to socket events. The modal still works manually in autonomous mode.
      }
    }
    void pollQueue();
    const timer = window.setInterval(pollQueue, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [autonomousMode, callApi, enqueueAction]);

  const resultText = useMemo(() => compactPayload(toolResult?.payload), [toolResult]);
  const laceGraph = useMemo(() => getLaceGraph(toolResult?.payload), [toolResult]);
  const minimizedToolList = useMemo(() => Object.values(minimizedTools).sort((a, b) => String(a.createdAt || "").localeCompare(String(b.createdAt || ""))), [minimizedTools]);
  const dockAutoVisible = Boolean(cursor.active || busyTool || laceRepairBusy || activeTool);
  const layerClassName = [
    "operational-mouse-layer",
    dockAutoVisible ? "is-engaged" : "is-clear",
    activeTool ? "has-modal" : "",
    minimizedToolList.length ? "has-tray" : "",
    dockAutoVisible ? "is-auto-visible" : "",
  ].filter(Boolean).join(" ");

  function consumePendingAction(toolId) {
    const pending = pendingAutoRunRef.current;
    if (!pending || pending.toolId !== toolId) return { actionId: "", projectId: projectIdRef.current };
    pendingAutoRunRef.current = null;
    return pending;
  }

  if (!autonomousMode) return null;

  return (
    <div className={layerClassName} aria-live="polite">
      <div
        className={`operational-mouse-cursor ${cursor.active ? "is-active" : ""}`}
        style={{ transform: `translate3d(${cursor.x}px, ${cursor.y}px, 0)` }}
      >
        <span className="operational-mouse-pointer" />
        <span className="operational-mouse-label">{cursor.label}</span>
      </div>

      <section className="operational-tool-dock" aria-label="Mouse operativo autonomo">
        <header className="operational-tool-dock__header">
          <strong>Mouse operativo</strong>
          <span>autonomo activo</span>
        </header>
        <label className="operational-tool-project">
          <span>Proyecto</span>
          <input value={projectId} onChange={(event) => { projectIdRef.current = event.target.value; setProjectId(event.target.value); }} />
        </label>
        <div className="operational-tool-grid">
          {TOOLS.map((tool) => (
            <button
              type="button"
              key={tool.id}
              data-operational-tool={tool.id}
              className={`operational-tool-button ${busyTool === tool.id ? "is-busy" : ""}`}
              onClick={(event) => openTool(tool.id, event)}
            >
              <span>{tool.label}</span>
              <small>{tool.evidence}</small>
            </button>
          ))}
        </div>
      </section>

      {(activeAction || actionTrace.length) ? (
        <section className="operational-action-trace" aria-label="Pasos reales del mouse operativo">
          <header>
            <strong>Accion real</strong>
            <span>{activeAction?.toolId || "sin herramienta"} · {activeAction?.projectSlug || projectId || "sin proyecto"} · {activeAction?.treeId || "sin BT"}</span>
          </header>
          <ol>
            {actionTrace.map((item) => (
              <li key={item.id} className={`is-${String(item.status || "pending").replace(/[^a-z0-9_-]/gi, "-").toLowerCase()}`}>
                <strong>{item.step}</strong>
                <span>{item.message}</span>
                {item.evidence ? <small>{item.evidence}</small> : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}



      {minimizedToolList.length ? (
        <section className="operational-minimized-tray" aria-label="Herramientas operativas recogidas">
          {minimizedToolList.map((card) => (
            <article
              key={card.toolId}
              data-operational-minimized-tool={card.toolId}
              className={`operational-minimized-card is-${String(card.status || "open").replace(/[^a-z0-9_-]/gi, "-").toLowerCase()}`}
            >
              <header>
                <strong>{card.label || card.toolId}</strong>
                <span>{card.status || "open"}</span>
              </header>
              <small>{card.projectId || projectId || "sin proyecto"}</small>
              <p>{card.payload?.reportPath || card.payload?.artifactPath || card.payload?.relativePath || card.payload?.message || card.evidence}</p>
              <div className="operational-minimized-card__actions">
                <button type="button" data-operational-restore-button={card.toolId} onClick={(event) => reopenMinimizedTool(card.toolId, event)}>Ver</button>
                <button type="button" data-operational-minimized-close={card.toolId} disabled={card.status === "running"} onClick={(event) => closeMinimizedTool(card.toolId, event)}>Cerrar</button>
              </div>
            </article>
          ))}
        </section>
      ) : null}

      {activeToolConfig ? (
        <div className="operational-modal-backdrop" role="dialog" aria-modal="true" aria-label={activeToolConfig.title}>
          <article className="operational-modal" data-operational-modal-tool={activeTool}>
            <header className="operational-modal__header">
              <div>
                <strong>{activeToolConfig.title}</strong>
                <span>{activeToolConfig.evidence}</span>
              </div>
              <div className="operational-modal__header-actions">
                <button type="button" className="operational-modal__close" data-operational-minimize-button={activeTool} onClick={(event) => minimizeTool(activeTool, event)}>Minimizar</button>
                <button type="button" className="operational-modal__close" data-operational-close-button={activeTool} onClick={(event) => closeActiveTool(activeTool, event)}>Cerrar</button>
              </div>
            </header>

            {activeTool === "web_research" ? (
              <div className="operational-research-panel">
                <label>
                  <span>Consulta segura</span>
                  <input value={researchQuery} onChange={(event) => setResearchQuery(event.target.value)} />
                </label>
                {researchUrl ? (
                  <iframe title="Web research seguro" src={researchUrl} sandbox="allow-forms allow-scripts allow-same-origin allow-popups" referrerPolicy="no-referrer" />
                ) : null}
              </div>
            ) : null}

            {activeTool === "lace_gate" ? (
              <section className="operational-lace-panel">
                <div className="operational-lace-metrics">
                  <span><strong>{toolResult?.payload?.lace?.requiredCycles ?? toolResult?.payload?.plan?.requiredCycles ?? "?"}</strong><small>requeridos</small></span>
                  <span><strong>{toolResult?.payload?.lace?.validCycleEvidenceCount ?? toolResult?.payload?.plan?.validCycleEvidenceCount ?? "?"}</strong><small>validos</small></span>
                  <span><strong>{toolResult?.payload?.lace?.missingCycles ?? toolResult?.payload?.plan?.missingCycles ?? "?"}</strong><small>faltantes</small></span>
                  <span><strong>{toolResult?.payload?.dependencyFindings?.length ?? toolResult?.payload?.plan?.statusBefore?.dependencyFindings?.length ?? 0}</strong><small>deps fantasma</small></span>
                </div>
                {toolResult?.payload?.ghostDependencies?.length ? (
                  <div className="operational-lace-warning">Deps fantasma: {toolResult.payload.ghostDependencies.join(", ")}</div>
                ) : null}
                {toolResult?.payload?.plan?.plannedTaskIds?.length ? (
                  <div className="operational-lace-plan">
                    <strong>Tareas a encolar</strong>
                    <p>{toolResult.payload.plan.plannedTaskIds.join(", ")}</p>
                  </div>
                ) : null}
                {toolResult?.payload?.plan && !toolResult.payload.plan.plannedTaskIds?.length ? (
                  <div className="operational-lace-plan">No hay tareas nuevas que encolar.</div>
                ) : null}
                {laceGraph?.nodes?.length ? (
                  <div className="operational-lace-graph" aria-label="Grafo LACE de dependencias">
                    <header>
                      <strong>Grafo LACE</strong>
                      <span>{laceGraph.nodes.length} nodo(s) · {(laceGraph.edges || []).length} enlace(s)</span>
                    </header>
                    <div className="operational-lace-node-grid">
                      {laceGraph.nodes.slice(0, 16).map((node) => (
                        <article key={node.id} className={`operational-lace-node is-${String(node.status || "unknown").replace(/[^a-z0-9_-]/gi, "-").toLowerCase()}`}>
                          <strong>{node.label || node.id}</strong>
                          <span>{node.taskId || "tarea faltante"}</span>
                          <small>doc={node.hasDoc ? "si" : "no"} · checkpoint={node.hasCheckpoint ? "si" : "no"}</small>
                          {node.missingDependencies?.length ? <em>falta {node.missingDependencies.join(", ")}</em> : null}
                        </article>
                      ))}
                    </div>
                    {(laceGraph.edges || []).some((edge) => edge.status === "missing") ? (
                      <p className="operational-lace-graph-warning">Hay enlaces con dependencia ausente. El cierre canonico debe seguir bloqueado.</p>
                    ) : null}
                  </div>
                ) : null}
              </section>
            ) : null}

            <div className="operational-modal__actions">
              <button type="button" className="operational-run-button" data-operational-run-button={activeTool} disabled={Boolean(busyTool)} onClick={(event) => handleRunToolButtonClick(activeTool, event)}>
                {busyTool === activeTool ? "Ejecutando" : activeTool === "lace_gate" ? "Diagnosticar LACE" : "Ejecutar herramienta real"}
              </button>
              {activeTool === "lace_gate" ? (
                <>
                  <button type="button" className="operational-run-button" data-operational-lace-action="dry-run" disabled={laceRepairBusy} onClick={() => repairLaceDependencies({ dryRun: true })}>
                    {laceRepairBusy ? "Calculando" : "Plan dry-run"}
                  </button>
                  <button type="button" className="operational-run-button is-warning" data-operational-lace-action="enqueue" disabled={laceRepairBusy} onClick={() => repairLaceDependencies({ dryRun: false })}>
                    Encolar faltantes
                  </button>
                </>
              ) : null}
              {researchUrl ? <a href={researchUrl} target="_blank" rel="noreferrer">Abrir investigacion</a> : null}
            </div>

            {toolResult ? (
              <section className={`operational-tool-result is-${toolResult.status}`}>
                <header>
                  <strong>{toolResult.status}</strong>
                  <span>{toolResult.payload?.reportPath || toolResult.payload?.artifactPath || toolResult.payload?.relativePath || "resultado runtime"}</span>
                </header>
                <pre>{resultText}</pre>
              </section>
            ) : null}
          </article>
        </div>
      ) : null}
    </div>
  );
}
