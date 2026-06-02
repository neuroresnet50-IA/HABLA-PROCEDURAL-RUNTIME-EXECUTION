import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";

const UI_REFRESH_SUPPRESS_AUTH_KEY = "hablaUiRefreshSuppressAuthGate";
const UI_REFRESH_AUTH_READY_KEY = "hablaAuthSessionReady";
const UI_REFRESH_LAST_KEY = "hablaRuntimeUiRefreshLast";
const LACE_GATE_AUTO_PREFIX = "hablaLaceGateAutoQueuedAt:";
const UI_REFRESH_COOLDOWN_MS = 120000;
const LACE_GATE_AUTO_COOLDOWN_MS = 180000;

const GATE_LABELS = {
  mouse: "Mouse",
  scanner: "Scanner",
  integrity: "Integrity",
  sandbox: "Sandbox",
  cyberlace: "CyberLACE",
  lace: "LACE",
  broom: "Escoba",
  typewriter: "Typewriter",
};

function nowLabel() {
  return new Date().toISOString();
}

function sessionGet(key) {
  try {
    return window.sessionStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function sessionSet(key, value) {
  try {
    window.sessionStorage.setItem(key, String(value));
  } catch {
    // Session storage can be unavailable; the UI refresh still falls back to a normal reload.
  }
}

function compact(value, fallback = "sin evidencia") {
  const text = String(value || "").trim();
  return text || fallback;
}

function gateFromEvent(event, source) {
  const op = String(event?.op || "").toLowerCase();
  const phase = String(event?.phase || "").toLowerCase();
  const action = String(event?.action || "").toLowerCase();
  const tool = String(event?.targetTool || "").toLowerCase().replace(/-/g, "_");
  const joined = `${op} ${phase} ${action} ${tool}`;
  if (source === "mouse" || joined.includes("operational_mouse") || joined.includes("ui:mouse")) return tool || "mouse";
  if (joined.includes("code_scanner") || joined.includes("scanner")) return "scanner";
  if (joined.includes("integrity") || joined.includes("findings")) return "integrity";
  if (joined.includes("sandbox")) return "sandbox";
  if (joined.includes("cyberlace") || joined.includes("quarantine")) return "cyberlace";
  if (joined.includes("lace")) return "lace";
  if (joined.includes("broom") || joined.includes("escoba")) return "broom";
  if (joined.includes("typewriter")) return "typewriter";
  return "mouse";
}

function statusFromEvent(event, source) {
  if (source === "mouse") return "queued";
  const status = String(event?.status || event?.state || "").toLowerCase();
  if (status) return status;
  const op = String(event?.op || "").toLowerCase();
  if (op.includes("complete") || op.includes("completed")) return "passed";
  if (op.includes("blocked") || op.includes("failed")) return "blocked";
  return "observing";
}

function normalizeEvent(event, source) {
  const gate = gateFromEvent(event, source);
  const status = statusFromEvent(event, source);
  return {
    id: `${source}-${event?.actionId || event?.timestamp || Date.now()}-${Math.random().toString(16).slice(2)}`,
    source,
    gate,
    status,
    projectSlug: compact(event?.projectSlug || event?.projectId, "sin proyecto"),
    message: compact(event?.message || event?.reason || event?.op || event?.action, "evento runtime"),
    evidence: compact(event?.expectedEvidence || event?.relativePath || event?.reportPath || event?.artifactPath || event?.focusPath, "sin evidencia"),
    timestamp: compact(event?.timestamp || event?.updatedAt || event?.createdAt || nowLabel(), "sin timestamp"),
  };
}

export default function ForensicTruthRail({ socketUrl = "", autonomousMode = false, selectedProject = "" }) {
  const apiBase = String(socketUrl || "").replace(/\/$/, "");
  const [events, setEvents] = useState([]);
  const [gates, setGates] = useState({});
  const [laceDependencyStatus, setLaceDependencyStatus] = useState(null);
  const [laceGateActionStatus, setLaceGateActionStatus] = useState("");
  const refreshScheduledRef = useRef(false);

  const scheduleRuntimeUiRefresh = useCallback((event) => {
    if (!autonomousMode || refreshScheduledRef.current) return;
    const status = String(event?.status || "").toLowerCase();
    if (!['blocked', 'failed'].includes(status)) return;
    if (event?.source === 'mouse') return;
    const now = Date.now();
    const lastRefreshAt = Number(sessionGet(UI_REFRESH_LAST_KEY) || 0);
    if (Number.isFinite(lastRefreshAt) && now - lastRefreshAt < UI_REFRESH_COOLDOWN_MS) return;
    refreshScheduledRef.current = true;
    sessionSet(UI_REFRESH_LAST_KEY, String(now));
    sessionSet(UI_REFRESH_SUPPRESS_AUTH_KEY, String(now));
    sessionSet(UI_REFRESH_AUTH_READY_KEY, String(now));
    sessionSet('hablaRuntimeUiRefreshReason', `${event.gate || 'runtime'}:${event.message || status}`.slice(0, 240));
    window.setTimeout(() => {
      window.location.reload();
    }, 1100);
  }, [autonomousMode]);

  const queueLaceGateAction = useCallback(async (reason = "LACE closure bloqueado; abrir gate visual para diagnostico.") => {
    const project = String(selectedProject || "").trim();
    if (!autonomousMode || !project) return null;
    setLaceGateActionStatus("encolando");
    try {
      const response = await fetch(`${apiBase}/api/ui-actions/enqueue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          targetTool: "lace_gate",
          projectSlug: project,
          source: "forensic_truth_rail",
          reason,
          expectedEvidence: "runtime/task_queue.json + docs/lace_cycles",
          autoRun: true,
          expiresSeconds: 120,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      setLaceGateActionStatus(payload?.ok === false || !response.ok ? "bloqueado" : "solicitado");
      return payload;
    } catch {
      setLaceGateActionStatus("fallo");
      return null;
    }
  }, [apiBase, autonomousMode, selectedProject]);

  useEffect(() => {
    if (!autonomousMode) return undefined;
    const socket = io(apiBase || undefined, { transports: ["polling"], upgrade: false });
    function push(source) {
      return (payload) => {
        if (!payload || typeof payload !== "object") return;
        const item = normalizeEvent(payload, source);
        setEvents((current) => [item, ...current].slice(0, 32));
        setGates((current) => ({
          ...current,
          [item.gate]: item,
        }));
        scheduleRuntimeUiRefresh(item);
      };
    }
    socket.on("agent:visual", push("visual"));
    socket.on("agent:observer", push("observer"));
    socket.on("ui:mouse-action", push("mouse"));
    return () => socket.disconnect();
  }, [apiBase, autonomousMode, scheduleRuntimeUiRefresh]);

  useEffect(() => {
    const project = String(selectedProject || "").trim();
    if (!autonomousMode || !project) {
      setLaceDependencyStatus(null);
      return undefined;
    }
    let cancelled = false;
    async function loadLaceStatus() {
      try {
        const response = await fetch(`${apiBase}/api/projects/${encodeURIComponent(project)}/lace-dependency-status`);
        const payload = await response.json();
        if (!cancelled) setLaceDependencyStatus(payload?.ok === false ? null : payload);
      } catch {
        if (!cancelled) setLaceDependencyStatus(null);
      }
    }
    void loadLaceStatus();
    const timer = window.setInterval(loadLaceStatus, 10000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [apiBase, autonomousMode, selectedProject]);

  useEffect(() => {
    const project = String(selectedProject || "").trim();
    if (!autonomousMode || !project || !laceDependencyStatus?.lace?.closureBlocked) return;
    const key = `${LACE_GATE_AUTO_PREFIX}${project}`;
    const now = Date.now();
    const lastQueuedAt = Number(sessionGet(key) || 0);
    if (Number.isFinite(lastQueuedAt) && now - lastQueuedAt < LACE_GATE_AUTO_COOLDOWN_MS) return;
    sessionSet(key, String(now));
    void queueLaceGateAction("Linea de Verdad detecto LACE closure bloqueado; abrir diagnostico visual no destructivo.");
  }, [autonomousMode, laceDependencyStatus, queueLaceGateAction, selectedProject]);

  const gateRows = useMemo(() => {
    const keys = ["mouse", "scanner", "integrity", "sandbox", "cyberlace", "lace", "broom", "typewriter"];
    return keys.map((key) => {
      if (key === "lace" && laceDependencyStatus?.lace) {
        return {
          gate: "lace",
          status: laceDependencyStatus.lace.closureStatus || "observing",
          message: `Ciclos ${laceDependencyStatus.lace.validCycleEvidenceCount || 0}/${laceDependencyStatus.lace.requiredCycles || 0}`,
          evidence: (laceDependencyStatus.ghostDependencies || []).length
            ? `deps fantasma: ${laceDependencyStatus.ghostDependencies.join(", ")}`
            : `faltan ${laceDependencyStatus.lace.missingCycles || 0} ciclo(s)`,
        };
      }
      return gates[key] || { gate: key, status: "sin evidencia", message: "pendiente", evidence: "sin evidencia" };
    });
  }, [gates, laceDependencyStatus]);

  if (!autonomousMode) return null;

  return (
    <aside className="forensic-truth-rail" aria-label="Linea de verdad forense">
      <header className="forensic-truth-rail__header">
        <strong>Linea de Verdad</strong>
        <span>evidencia viva</span>
      </header>
      <div className="forensic-gate-grid">
        {gateRows.map((gate) => (
          <article key={gate.gate} className={`forensic-gate-card is-${String(gate.status || "").replace(/[^a-z0-9_-]/gi, "-").toLowerCase()}`}>
            <strong>{GATE_LABELS[gate.gate] || gate.gate}</strong>
            <span>{gate.status}</span>
            <small>{gate.evidence}</small>
          </article>
        ))}
      </div>
      {laceDependencyStatus?.lace?.closureBlocked ? (
        <section className="forensic-lace-alert">
          <strong>LACE closure gate bloqueado</strong>
          <p>Faltan {laceDependencyStatus.lace.missingCycles || 0} ciclo(s); validos {laceDependencyStatus.lace.validCycleEvidenceCount || 0}/{laceDependencyStatus.lace.requiredCycles || 0}.</p>
          {laceDependencyStatus.dependencyFindings?.slice(0, 4).map((finding) => (
            <p key={finding.taskId}>
              {finding.taskId}: falta {finding.missingDependencies.join(", ")}
            </p>
          ))}
          <button type="button" data-truth-action="open-lace-gate" onClick={() => queueLaceGateAction("Humano solicito abrir LACE Gate desde Linea de Verdad.")}>
            Abrir LACE Gate
          </button>
          {laceGateActionStatus ? <small>mouse action: {laceGateActionStatus}</small> : null}
        </section>
      ) : null}
      <section className="forensic-event-stream">
        {events.length ? events.map((event) => (
          <article key={event.id} className="forensic-event-row">
            <header>
              <strong>{GATE_LABELS[event.gate] || event.gate}</strong>
              <span>{event.source} · {event.status}</span>
            </header>
            <p>{event.message}</p>
            <small>{event.projectSlug} · {event.evidence}</small>
          </article>
        )) : <p className="forensic-empty">Sin eventos nuevos. Esperando evidencia real del runtime.</p>}
      </section>
    </aside>
  );
}
