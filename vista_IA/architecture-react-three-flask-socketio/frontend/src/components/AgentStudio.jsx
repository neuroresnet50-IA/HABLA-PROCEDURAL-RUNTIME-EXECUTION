import { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";
import { buildClosureCertificate, buildRuntimeClosureCertificate, formatAgentStatus } from "./agentClosureCertificate.js";
import LiveReviewerPanel from "./LiveReviewerPanel.jsx";

import {
  ACTIVE_AGENT_STATUSES,
  DEFAULT_AGENT_RUNTIME_MODE,
  RUNTIME_MODE_PRESETS,
  booleanLabel,
  buildGeneratedProjectName,
  describeVisualState,
  emitWithAck,
  flattenDetectedStack,
  formatDuration,
  getLaceProgress,
  getLiveStage,
  getLiveStageLabel,
  getProgressLabel,
  getProgressPercent,
  getSessionElapsedSeconds,
  humanizeAgentError,
  humanizeRuntimeResetError,
  isAgentActive,
  looksLikeProjectName,
  mergeHumanAlignmentReviewList,
  mergeReviewerEvents,
  normalizeShortConfirmation,
  parseInlineProjectPrompt,
  parseTimestamp,
  sameReviewerScope,
  slugify,
} from "./agentStudioUtils.js";

export default function AgentStudio({ socketUrl, onSceneFocus, onWorkspaceClean }) {
  const [projects, setProjects] = useState([]);
  const [launchMode, setLaunchMode] = useState("new");
  const [runtimeMode, setRuntimeMode] = useState(DEFAULT_AGENT_RUNTIME_MODE);
  const [selectedProject, setSelectedProject] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [requirement, setRequirement] = useState("");
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [session, setSession] = useState(null);
  const [terminalOutput, setTerminalOutput] = useState("");
  const [agentRoomEvents, setAgentRoomEvents] = useState([]);
  const [subagentPlan, setSubagentPlan] = useState(null);
  const [assignedSubagentPlan, setAssignedSubagentPlan] = useState(null);
  const [isPlanningSubagents, setIsPlanningSubagents] = useState(false);
  const [connected, setConnected] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isResettingRuntime, setIsResettingRuntime] = useState(false);
  const [isClearingPendingQueue, setIsClearingPendingQueue] = useState(false);
  const [retryableTask, setRetryableTask] = useState(null);
  const [isLoadingRetryableTask, setIsLoadingRetryableTask] = useState(false);
  const [isRelaunchingTask, setIsRelaunchingTask] = useState(false);
  const [isCleaningWorkspace, setIsCleaningWorkspace] = useState(false);
  const [workspaceCleanOpen, setWorkspaceCleanOpen] = useState(false);
  const [workspaceCleanStep, setWorkspaceCleanStep] = useState(1);
  const [workspaceCleanKeyword, setWorkspaceCleanKeyword] = useState("");
  const [workspaceCleanConfirmation, setWorkspaceCleanConfirmation] = useState("");
  const [error, setError] = useState("");
  const [visualState, setVisualState] = useState(null);
  const [reviewerEvents, setReviewerEvents] = useState([]);
  const [reviewerStatus, setReviewerStatus] = useState(null);
  const [reviewerOpen, setReviewerOpen] = useState(false);
  const [reviewerMinimized, setReviewerMinimized] = useState(false);
  const [reviewerExpanded, setReviewerExpanded] = useState(false);
  const [emailCommandStatus, setEmailCommandStatus] = useState(null);
  const [emailCommandMessage, setEmailCommandMessage] = useState("");
  const [emailCommandHistory, setEmailCommandHistory] = useState([]);
  const [emailConfigOpen, setEmailConfigOpen] = useState(false);
  const [emailConfig, setEmailConfig] = useState(null);
  const [isSavingEmailConfig, setIsSavingEmailConfig] = useState(false);
  const [hablaRuntimeStatus, setHablaRuntimeStatus] = useState(null);
  const [hablaRuntimeError, setHablaRuntimeError] = useState("");
  const [dismissedClosureKey, setDismissedClosureKey] = useState("");
  const [nowTick, setNowTick] = useState(Date.now());
  const [agentBursts, setAgentBursts] = useState([]);
  const [harReview, setHarReview] = useState(null);
  const [harReviews, setHarReviews] = useState([]);
  const [harTechOptions, setHarTechOptions] = useState({});
  const [harFeedback, setHarFeedback] = useState("");
  const [harMessage, setHarMessage] = useState("");
  const [harSelectedPreferences, setHarSelectedPreferences] = useState({});
  const [harPreferenceCategory, setHarPreferenceCategory] = useState("databases");
  const [harPreferenceValue, setHarPreferenceValue] = useState("SQL Server");
  const [isHarLoading, setIsHarLoading] = useState(false);
  const [isHarSubmitting, setIsHarSubmitting] = useState(false);
  const socketRef = useRef(null);
  const activeSessionRef = useRef(null);
  const sessionRef = useRef(null);
  const reviewerProjectRef = useRef("");
  const reviewerUserMinimizedRef = useRef(false);
  const reviewerAutoOpenedSessionRef = useRef("");
  const latestBurstKeyRef = useRef("");
  const latestBurstAtRef = useRef(0);
  const heartbeatBurstAtRef = useRef(0);
  const terminalRef = useRef(null);

  const selectedProjectMeta = useMemo(
    () => projects.find((project) => project.slug === selectedProject) || null,
    [projects, selectedProject]
  );
  const habla = session?.habla || null;
  const hablaState = habla?.state || null;
  const hablaRuntimeState = hablaState || hablaRuntimeStatus || {};
  const hablaRuntimeAvailable = Boolean(habla?.available || hablaRuntimeStatus?.available);
  const lacePolicyLoaded = hablaRuntimeState?.lacePolicyLoaded ?? hablaRuntimeStatus?.lacePolicyLoaded;
  const lacePolicyPath = hablaRuntimeState?.lacePolicyPath || session?.lacePolicyPath || hablaRuntimeStatus?.agentRuntime?.lacePolicySource || "";
  const laceRuntimeLabel = hablaRuntimeState?.laceRuntime || "not_active";
  const hablaRuntimeLabel = [hablaRuntimeState?.runtime, hablaRuntimeState?.engineVersion].filter(Boolean).join(" ") || "HABLA sin motor";
  const visualNote = describeVisualState(visualState);
  const hablaConfidence = hablaState?.confidence || null;
  const laceCycles = Array.isArray(session?.laceCycles) ? session.laceCycles : [];
  const reviewerProjectSlug = session?.projectSlug || selectedProject || selectedProjectMeta?.slug || "";
  const liveStage = getLiveStage(session);
  const liveElapsedSeconds = getSessionElapsedSeconds(session, nowTick);
  const liveActive = isAgentActive(session);
  const closureCertificate = buildClosureCertificate(session) || buildRuntimeClosureCertificate(reviewerStatus, selectedProjectMeta || { projectSlug: reviewerProjectSlug });
  const closureModalOpen = Boolean(closureCertificate && closureCertificate.key !== dismissedClosureKey);
  const harDetectedStack = harReview?.summary?.detected_stack || {};
  const harStackEntries = flattenDetectedStack(harDetectedStack);
  const harDecisionEntries = Array.isArray(harReview?.summary?.architecture_decisions)
    ? harReview.summary.architecture_decisions
    : [];
  const harCategoryOptions = Object.keys(harTechOptions || {});
  const harValueOptions = Array.isArray(harTechOptions?.[harPreferenceCategory])
    ? harTechOptions[harPreferenceCategory]
    : [];
  const harSelectedPreferenceEntries = Object.entries(harSelectedPreferences || {}).flatMap(([category, values]) => (
    Array.isArray(values) ? values.map((value) => ({ category, value })) : []
  ));

  useEffect(() => {
    activeSessionRef.current = activeSessionId;
  }, [activeSessionId]);

  useEffect(() => {
    sessionRef.current = session;
    reviewerProjectRef.current = reviewerProjectSlug;
  }, [session, reviewerProjectSlug]);

  useEffect(() => {
    if (ACTIVE_AGENT_STATUSES.has(session?.status)) {
      setDismissedClosureKey("");
    }
  }, [session?.sessionId, session?.status]);

  useEffect(() => {
    const projectSlug = String(selectedProject || "").trim();
    if (!projectSlug) {
      setRetryableTask(null);
      setIsLoadingRetryableTask(false);
      return undefined;
    }

    let cancelled = false;
    setIsLoadingRetryableTask(true);
    fetch(`/api/agent/projects/${encodeURIComponent(projectSlug)}/retryable-task`)
      .then(async (response) => {
        const payload = await response.json().catch(() => null);
        if (cancelled) return;
        if (response.status === 404 || payload?.ok === false) {
          setRetryableTask(null);
          return;
        }
        if (!response.ok) {
          throw new Error(payload?.error || "retryable_task_load_failed");
        }
        setRetryableTask(payload?.task || null);
      })
      .catch((nextError) => {
        if (!cancelled) {
          setRetryableTask(null);
          setError(`No fue posible leer orden recuperable: ${humanizeRuntimeResetError(nextError)}`);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoadingRetryableTask(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedProject]);

  useEffect(() => {
    const timer = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!liveActive) return undefined;
    const timer = window.setInterval(() => {
      const now = Date.now();
      if (now - heartbeatBurstAtRef.current < 18000) return;
      heartbeatBurstAtRef.current = now;
      pushAgentBurst({
        source: "Pulso vivo",
        message: "Worker activo; esperando nueva evidencia en disco o evento visual.",
        tone: getLiveStage(sessionRef.current),
      });
    }, 6000);
    return () => window.clearInterval(timer);
  }, [liveActive]);

  function pushAgentBurst({ source = "Runtime", message = "", tone = "middle" }) {
    const cleanMessage = String(message || "").trim();
    if (!cleanMessage) return;
    const cleanSource = String(source || "Runtime").trim();
    const key = `${cleanSource}|${cleanMessage}`;
    const now = Date.now();
    if (latestBurstKeyRef.current === key && now - latestBurstAtRef.current < 5000) return;
    latestBurstKeyRef.current = key;
    latestBurstAtRef.current = now;

    const id = `${now}-${Math.random().toString(36).slice(2)}`;
    setAgentBursts((current) => [
      ...current.slice(-4),
      { id, source: cleanSource, message: cleanMessage, tone: tone || "middle" },
    ]);
    window.setTimeout(() => {
      setAgentBursts((current) => current.filter((burst) => burst.id !== id));
    }, 5000);
  }

  function appendAgentRoomEvent({ agentId = "A00", agentName = "Runtime", kind = "evento", message = "", tone = "middle", detail = "" }) {
    const cleanMessage = String(message || "").replace(/\s+/g, " ").trim();
    if (!cleanMessage) return;
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setAgentRoomEvents((current) => [
      ...current.slice(-119),
      {
        id,
        at: new Date().toLocaleTimeString(),
        agentId,
        agentName,
        kind,
        message: cleanMessage.slice(0, 420),
        detail: String(detail || "").slice(0, 520),
        tone: tone || "middle",
      },
    ]);
  }

  function terminalChunkPreview(chunk) {
    const lines = String(chunk || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    return lines[lines.length - 1] || String(chunk || "").trim();
  }

  function applyEmailCommandPayload(payload = {}) {
    if (payload.emailStatus) {
      setEmailCommandStatus(payload.emailStatus);
    }
    if (payload.message) {
      setEmailCommandMessage(payload.message);
    }

    const command = payload.command;
    if (command?.id) {
      setEmailCommandHistory((current) => [command, ...current.filter((item) => item.id !== command.id)].slice(0, 8));
      if (command.requirement) {
        setLaunchMode("new");
        setSelectedProject("");
        setNewProjectName(command.projectName || command.projectSlug || buildGeneratedProjectName());
        setRequirement(command.requirement);
        if (command.projectSlug) {
          onSceneFocus?.(command.projectSlug);
        }
      }
      pushAgentBurst({
        source: "Correo ejecutable",
        message: payload.message || `${command.projectName || command.projectSlug} recibido por email.`,
        tone: command.status === "failed" ? "danger" : command.status === "started" ? "final" : "initial",
      });
    }

    if (payload.session) {
      setActiveSessionId(payload.session.sessionId);
      setSession(payload.session);
      setTerminalOutput(payload.session.output || "");
      if (payload.session.projectSlug) {
        setSelectedProject(payload.session.projectSlug);
        onSceneFocus?.(payload.session.projectSlug);
      }
    }
  }

  async function loadEmailCommandConfig() {
    try {
      const response = await fetch("/api/email-commands/config");
      const payload = await response.json();
      if (payload?.config) {
        setEmailConfig({
          ...payload.config,
          imapPassword: "",
        });
      }
      if (payload?.email) {
        setEmailCommandStatus(payload.email);
      }
    } catch (nextError) {
      setEmailCommandMessage(nextError?.message || "No fue posible cargar configuracion de correo.");
    }
  }

  async function loadHablaRuntimeStatus() {
    try {
      const statusUrl = new URL("/api/runtime/habla-status", socketUrl).toString();
      const response = await fetch(statusUrl);
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || "habla_status_failed");
      }
      setHablaRuntimeStatus(payload.habla || null);
      setHablaRuntimeError("");
    } catch (nextError) {
      setHablaRuntimeError(nextError?.message || "No fue posible leer el estado HABLA.");
    }
  }

  async function saveEmailCommandConfig() {
    if (!emailConfig) return;
    setIsSavingEmailConfig(true);
    setEmailCommandMessage("Guardando configuracion de correo...");
    try {
      const response = await fetch("/api/email-commands/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(emailConfig),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || "email_config_save_failed");
      }
      setEmailConfig({
        ...payload.config,
        imapPassword: "",
      });
      setEmailCommandStatus(payload.email || null);
      setEmailCommandMessage("Configuracion de correo guardada.");
      setEmailConfigOpen(false);
    } catch (nextError) {
      setEmailCommandMessage(nextError?.message || "No fue posible guardar configuracion.");
    } finally {
      setIsSavingEmailConfig(false);
    }
  }

  useEffect(() => {
    if (launchMode === "new" && !newProjectName) {
      setNewProjectName(buildGeneratedProjectName());
    }
  }, [launchMode, newProjectName]);

  useEffect(() => {
    loadHablaRuntimeStatus();
  }, [socketUrl]);

  useEffect(() => {
    const socket = io(socketUrl, {
      transports: ["polling"],
      upgrade: false,
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      setError("");
      socket.emit("agent:request");
      loadEmailCommandConfig();
      loadHablaRuntimeStatus();
    });

    socket.on("disconnect", () => {
      setConnected(false);
    });

    socket.on("agent:projects", (payload) => {
      const nextProjects = payload?.projects || [];
      setError("");
      setProjects(nextProjects);
      setSelectedProject((current) => (
        current && nextProjects.some((project) => project.slug === current)
          ? current
          : ""
      ));
    });

    socket.on("agent:email_command", (payload) => {
      if (!payload) return;
      applyEmailCommandPayload(payload);
    });

    socket.on("agent:session", (nextSession) => {
      if (!nextSession?.sessionId) return;
      setError("");
      if (ACTIVE_AGENT_STATUSES.has(nextSession.status) || nextSession.status === "completed" || nextSession.status === "failed") {
        const sessionMessage = getProgressLabel(nextSession);
        pushAgentBurst({
          source: "Control plane",
          message: sessionMessage,
          tone: getLiveStage(nextSession),
        });
        appendAgentRoomEvent({
          agentId: "A01",
          agentName: "Orquestador",
          kind: nextSession.status || "session",
          message: sessionMessage,
          tone: getLiveStage(nextSession),
          detail: nextSession.activeTaskId || nextSession.sessionId || "",
        });
      }

      setSession((current) => {
        if (current?.sessionId === nextSession.sessionId) {
          setTerminalOutput(nextSession.output || "");
          if (nextSession.status === "failed" && nextSession.errorMessage) {
            setError(nextSession.errorMessage);
          }
          return nextSession;
        }

        if (!activeSessionRef.current || nextSession.status === "running" || nextSession.status === "starting") {
          setActiveSessionId(nextSession.sessionId);
          setTerminalOutput(nextSession.output || "");
          if (nextSession.projectSlug) {
            setSelectedProject(nextSession.projectSlug);
            onSceneFocus?.(nextSession.projectSlug);
          }
          if (nextSession.status === "failed" && nextSession.errorMessage) {
            setError(nextSession.errorMessage);
          }
          return nextSession;
        }

        return current;
      });
    });

    socket.on("agent:terminal", (payload) => {
      if (!payload?.sessionId) return;
      if (activeSessionRef.current && payload.sessionId !== activeSessionRef.current) return;
      setError("");
      setActiveSessionId(payload.sessionId);
      setTerminalOutput(payload.output || "");
      setSession((current) => (
        current?.sessionId === payload.sessionId
          ? { ...current, output: payload.output || "", status: payload.status || current.status, updatedAt: payload.updatedAt }
          : current
      ));
      appendAgentRoomEvent({
        agentId: "A04",
        agentName: "Codex Worker",
        kind: payload.status ? `terminal/${payload.status}` : "terminal",
        message: terminalChunkPreview(payload.chunk) || "Terminal actualizado",
        tone: payload.status === "failed" ? "danger" : "middle",
        detail: payload.sessionId,
      });
      if (payload.projectSlug) {
        setSelectedProject(payload.projectSlug);
        onSceneFocus?.(payload.projectSlug);
      }
    });

    socket.on("agent:visual", (payload) => {
      if (!payload) return;
      setVisualState(payload);
      if (payload.subagentPlan) {
        setSubagentPlan(payload.subagentPlan);
      }
      appendAgentRoomEvent({
        agentId: payload.op === "subagents_assigned" || payload.op === "subagent_plan_ready" ? "A01" : "A05",
        agentName: payload.op === "subagents_assigned" || payload.op === "subagent_plan_ready" ? "Orquestador" : "Visual Bridge",
        kind: payload.phase || payload.op || "visual",
        message: payload.message || payload.relativePath || payload.focusPath || payload.op,
        tone: payload.status === "failed" ? "danger" : payload.status === "completed" ? "final" : getLiveStage(sessionRef.current),
        detail: payload.relativePath || payload.focusPath || "",
      });
      if (["human_alignment_review_created", "human_alignment_feedback_submitted"].includes(payload.op)) {
        const payloadProject = payload.projectSlug || payload.projectId || "";
        const currentProject = reviewerProjectRef.current;
        if (!payloadProject || !currentProject || payloadProject === currentProject) {
          if (payload.review) {
            setHarReview(payload.review);
            setHarReviews((current) => mergeHumanAlignmentReviewList(current, payload.review));
          }
          setHarMessage(payload.message || "HAR actualizado.");
        }
      }
      pushAgentBurst({
        source: payload.phase ? `Bridge: ${payload.phase}` : "Bridge visual",
        message: payload.message || payload.relativePath || payload.focusPath || payload.op,
        tone: getLiveStage(sessionRef.current),
      });
    });

    socket.on("agent:reviewer", (payload) => {
      if (!payload) return;
      const activeSession = sessionRef.current;
      const projectSlug = reviewerProjectRef.current;
      if (!sameReviewerScope(payload, activeSession, projectSlug)) return;
      setReviewerEvents((current) => mergeReviewerEvents(current, [payload]));
      if (payload.status) {
        setReviewerStatus(payload.status);
      }
      pushAgentBurst({
        source: "Supervisor",
        message: payload.message || payload.type || "Evidencia del reviewer actualizada.",
        tone: payload.severity === "error" ? "danger" : payload.severity === "warning" ? "initial" : getLiveStage(activeSession),
      });
      appendAgentRoomEvent({
        agentId: "A06",
        agentName: "Live Reviewer",
        kind: payload.type || payload.event_type || "reviewer",
        message: payload.message || "Evidencia del reviewer actualizada.",
        tone: payload.severity === "error" ? "danger" : payload.severity === "warning" ? "initial" : "final",
        detail: payload.current_task_id || payload.session_id || "",
      });
      if (ACTIVE_AGENT_STATUSES.has(activeSession?.status) && !reviewerUserMinimizedRef.current) {
        setReviewerOpen(true);
      }
    });

    socket.on("agent:observer", (payload) => {
      if (!payload) return;
      appendAgentRoomEvent({
        agentId: "A07",
        agentName: "Observer Plane",
        kind: payload.phase || payload.op || payload.state || "observer",
        message: payload.message || payload.reason || "Observer actualizado.",
        tone: payload.op === "observer_authorization_required" ? "initial" : "middle",
        detail: payload.focusPath || payload.relativePath || payload.state || "",
      });
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [socketUrl]);

  useEffect(() => {
    if (!terminalRef.current) return;
    terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [terminalOutput, agentRoomEvents.length]);

  useEffect(() => {
    if (!session?.sessionId || !ACTIVE_AGENT_STATUSES.has(session.status)) return undefined;
    let cancelled = false;

    async function reconcileActiveSession() {
      try {
        const response = await fetch("/api/agent/sessions");
        if (!response.ok) return;
        const payload = await response.json();
        if (cancelled) return;
        const liveSessions = Array.isArray(payload?.sessions) ? payload.sessions : [];
        const stillLive = liveSessions.some((item) => (
          item?.sessionId === session.sessionId && ACTIVE_AGENT_STATUSES.has(item?.status)
        ));
        if (stillLive) return;
        setActiveSessionId(null);
        setSession((current) => (
          current?.sessionId === session.sessionId
            ? {
                ...current,
                status: "stopped",
                errorCode: current.errorCode || "stale_frontend_session",
                errorMessage: current.errorMessage || "La UI tenia una sesion viva, pero el backend ya no tiene worker activo.",
                progressLabel: "Sesion local descartada: backend sin worker activo.",
                updatedAt: new Date().toISOString(),
              }
            : current
        ));
        setError("Sesion local descartada: backend sin worker activo. Botones desbloqueados.");
      } catch (_error) {
        // La verdad final la mantiene runtime-truth; este reconciliador solo evita UI stale.
      }
    }

    reconcileActiveSession();
    const timer = window.setInterval(reconcileActiveSession, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [session?.sessionId, session?.status]);

  useEffect(() => {
    if (!reviewerProjectSlug) return undefined;
    const sessionIsLive = Boolean(session?.sessionId && ACTIVE_AGENT_STATUSES.has(session?.status));
    let cancelled = false;

    async function loadReviewerStatus() {
      const sessionQuery = sessionIsLive ? `?sessionId=${encodeURIComponent(session.sessionId)}` : "";
      try {
        const response = await fetch(`/api/projects/${encodeURIComponent(reviewerProjectSlug)}/reviewer-status${sessionQuery}`);
        if (!response.ok) return;
        const payload = await response.json();
        if (cancelled || payload?.ok === false) return;
        setReviewerStatus(payload.status || null);
        if (sessionIsLive) {
          setReviewerEvents((current) => mergeReviewerEvents(current, payload.events || []));
        }
      } catch (_error) {
        // Polling is a fallback; socket events remain the primary live path.
      }
    }

    loadReviewerStatus();
    if (!sessionIsLive) {
      return () => {
        cancelled = true;
      };
    }
    const timer = window.setInterval(loadReviewerStatus, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [reviewerProjectSlug, session?.sessionId, session?.status]);

  useEffect(() => {
    if (ACTIVE_AGENT_STATUSES.has(session?.status)) {
      if (reviewerAutoOpenedSessionRef.current === session.sessionId) {
        if (!reviewerUserMinimizedRef.current) {
          setReviewerOpen(true);
        }
        return;
      }
      reviewerAutoOpenedSessionRef.current = session.sessionId;
      reviewerUserMinimizedRef.current = false;
      setReviewerOpen(true);
      setReviewerMinimized(false);
    }
  }, [session?.sessionId, session?.runtimeMode, session?.status]);

  useEffect(() => {
    if (!reviewerProjectSlug) {
      setHarReview(null);
      setHarReviews([]);
      setHarMessage("");
      return undefined;
    }
    let cancelled = false;
    loadHumanAlignmentReview(reviewerProjectSlug, { silent: true, cancelled: () => cancelled });
    return () => {
      cancelled = true;
    };
  }, [reviewerProjectSlug]);

  useEffect(() => {
    if (!harCategoryOptions.length) return;
    if (!harCategoryOptions.includes(harPreferenceCategory)) {
      setHarPreferenceCategory(harCategoryOptions[0]);
    }
  }, [harCategoryOptions.join("|"), harPreferenceCategory]);

  useEffect(() => {
    if (!harValueOptions.length) return;
    if (!harValueOptions.includes(harPreferenceValue)) {
      setHarPreferenceValue(harValueOptions[0]);
    }
  }, [harPreferenceCategory, harValueOptions.join("|"), harPreferenceValue]);

  async function loadHumanAlignmentReview(projectSlug = reviewerProjectSlug, options = {}) {
    if (!projectSlug) return;
    if (!options.silent) {
      setIsHarLoading(true);
      setHarMessage("");
    }
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(projectSlug)}/human-alignment-review`);
      const payload = await response.json();
      if (options.cancelled?.()) return;
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || "human_alignment_review_load_failed");
      }
      setHarReview(payload.latestReview || null);
      setHarReviews(payload.reviews || []);
      setHarTechOptions(payload.techStackOptions || {});
      if (!options.silent) {
        setHarMessage(payload.latestReview ? "HAR cargado." : "No hay HAR para este proyecto.");
      }
    } catch (nextError) {
      if (!options.silent) {
        setHarMessage(nextError?.message || "No fue posible cargar HAR.");
      }
    } finally {
      if (!options.silent) {
        setIsHarLoading(false);
      }
    }
  }

  async function handleCreateHumanAlignmentReview() {
    if (!reviewerProjectSlug) return;
    setIsHarSubmitting(true);
    setHarMessage("");
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(reviewerProjectSlug)}/human-alignment-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: "manual",
          trigger: "manual_human_alignment_review",
          reason: "Revision de alineacion humana solicitada desde la UI.",
        }),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || "human_alignment_review_create_failed");
      }
      setHarReview(payload.review || null);
      setHarReviews((current) => mergeHumanAlignmentReviewList(current, payload.review));
      setHarTechOptions(payload.techStackOptions || {});
      setHarMessage(payload.created ? "HAR creado; esperando preferencias humanas." : "HAR existente reutilizado.");
    } catch (nextError) {
      setHarMessage(nextError?.message || "No fue posible crear HAR.");
    } finally {
      setIsHarSubmitting(false);
    }
  }

  function handleAddHarPreference() {
    if (!harPreferenceCategory || !harPreferenceValue) return;
    setHarSelectedPreferences((current) => {
      const values = Array.isArray(current[harPreferenceCategory]) ? current[harPreferenceCategory] : [];
      if (values.includes(harPreferenceValue)) return current;
      return {
        ...current,
        [harPreferenceCategory]: [...values, harPreferenceValue],
      };
    });
  }

  function handleRemoveHarPreference(category, value) {
    setHarSelectedPreferences((current) => {
      const values = (Array.isArray(current[category]) ? current[category] : []).filter((item) => item !== value);
      const next = { ...current };
      if (values.length) {
        next[category] = values;
      } else {
        delete next[category];
      }
      return next;
    });
  }

  async function handleSubmitHumanAlignmentFeedback() {
    if (!reviewerProjectSlug || !harReview?.id || !harFeedback.trim()) return;
    setIsHarSubmitting(true);
    setHarMessage("");
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(reviewerProjectSlug)}/human-alignment-review/${encodeURIComponent(harReview.id)}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback: harFeedback,
          selectedStackPreferences: harSelectedPreferences,
        }),
      });
      const payload = await response.json();
      if (response.status === 423) {
        throw new Error(payload?.lock?.message || "project_locked");
      }
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || "human_alignment_feedback_failed");
      }
      setHarReview(payload.review || null);
      setHarReviews((current) => mergeHumanAlignmentReviewList(current, payload.review));
      setHarTechOptions(payload.techStackOptions || {});
      setHarFeedback("");
      setHarMessage(`Feedback convertido en ${payload.tasks?.length || 0} tarea(s) prioritaria(s).`);
    } catch (nextError) {
      setHarMessage(nextError?.message || "No fue posible registrar feedback HAR.");
    } finally {
      setIsHarSubmitting(false);
    }
  }

  function handleCopyReviewerLog() {
    const body = reviewerEvents.map((event) => `[${event.timestamp}] ${event.severity} ${event.message}`).join("\n");
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(body);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = body;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  function handleExportReviewerLog() {
    const payload = JSON.stringify({ status: reviewerStatus, events: reviewerEvents }, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${reviewerProjectSlug || "project"}-reviewer-log.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function handleCreateProject() {
    setIsCreatingProject(true);
    setError("");
    try {
      const payload = await emitWithAck(
        socketRef.current,
        "agent:project:create",
        {
          name: newProjectName || buildGeneratedProjectName(),
          ensureUnique: true,
          bootstrapProject: false,
        },
        60000
      );
      if (payload.projects) {
        setProjects(payload.projects);
      }
      if (payload.project?.slug) {
        setSelectedProject(payload.project.slug);
        setNewProjectName(payload.project.name || "");
        onSceneFocus?.(payload.project.slug);
      }
    } catch (nextError) {
      setError(`No fue posible crear el proyecto: ${humanizeAgentError(nextError)}`);
    } finally {
      setIsCreatingProject(false);
    }
  }

  function handleSelectLaunchMode(mode) {
    setLaunchMode(mode);
    setError("");
    if (mode === "new") {
      setSelectedProject("");
      onSceneFocus?.("");
      if (!newProjectName) {
        setNewProjectName(buildGeneratedProjectName());
      }
      return;
    }
    if (selectedProject) {
      onSceneFocus?.(selectedProject);
    }
  }

  function handleOpenExistingProject() {
    if (!selectedProjectMeta) {
      setError("Selecciona un proyecto existente para continuar.");
      return;
    }
    setError("");
    onSceneFocus?.(selectedProjectMeta.slug);
  }

  function currentPromptContext() {
    const inlinePrompt = parseInlineProjectPrompt(requirement);
    const normalizedRequirement = inlinePrompt.requirement || requirement.trim();
    const createFreshProject = launchMode === "new" && !selectedProjectMeta;
    const desiredProjectName = (
      createFreshProject
        ? (newProjectName.trim() || inlinePrompt.projectName || buildGeneratedProjectName())
        : (selectedProjectMeta?.name || newProjectName.trim() || "")
    ).trim();
    const desiredProjectSlug = createFreshProject
      ? slugify(desiredProjectName)
      : (selectedProjectMeta?.slug || slugify(desiredProjectName));
    return { inlinePrompt, normalizedRequirement, createFreshProject, desiredProjectName, desiredProjectSlug };
  }

  async function handlePlanSubagents() {
    const context = currentPromptContext();
    if (!context.normalizedRequirement) {
      setError("Escribe el prompt antes de calcular subagentes.");
      return;
    }
    if (!context.createFreshProject && !selectedProjectMeta) {
      setError("Selecciona un proyecto existente antes de calcular subagentes.");
      return;
    }
    setIsPlanningSubagents(true);
    setError("");
    setAssignedSubagentPlan(null);
    try {
      const response = await fetch("/api/agent/subagents/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requirement: context.normalizedRequirement,
          runtimeMode,
          launchMode,
          projectSlug: context.desiredProjectSlug,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "subagent_plan_failed");
      }
      setSubagentPlan(payload.recommendation || null);
      appendAgentRoomEvent({
        agentId: "A01",
        agentName: "Orquestador",
        kind: "dictamen",
        message: payload.recommendation?.summary || "Dictamen de subagentes listo.",
        tone: "final",
        detail: (payload.recommendation?.reasons || []).join(" | "),
      });
    } catch (nextError) {
      setError(`No fue posible calcular subagentes: ${humanizeRuntimeResetError(nextError)}`);
    } finally {
      setIsPlanningSubagents(false);
    }
  }

  function handleAssignSubagents() {
    if (!subagentPlan?.roster?.length) return;
    setAssignedSubagentPlan(subagentPlan);
    appendAgentRoomEvent({
      agentId: "A01",
      agentName: "Orquestador",
      kind: "asignacion",
      message: `${subagentPlan.recommendedAgents || subagentPlan.roster.length} subagente(s) asignados por boton.`,
      tone: "final",
      detail: subagentPlan.roster.map((agent) => `${agent.id} ${agent.name}`).join(" | "),
    });
  }

  async function handleSendRequirement() {
    if (!requirement.trim()) return;
    setIsSending(true);
    setError("");

    try {
      const { normalizedRequirement, createFreshProject, desiredProjectName, desiredProjectSlug } = currentPromptContext();

      if (!normalizedRequirement) {
        throw new Error("missing_requirement");
      }
      if (!desiredProjectName) {
        throw new Error("missing_project_name");
      }
      if (!createFreshProject && !selectedProjectMeta) {
        throw new Error("missing_existing_project");
      }

      onSceneFocus?.(desiredProjectSlug);
      const payload = await emitWithAck(
        socketRef.current,
        "agent:session:start",
        {
          projectName: desiredProjectName,
          projectSlug: desiredProjectSlug,
          requirement: normalizedRequirement,
          ensureNewProject: createFreshProject,
          bootstrapProject: false,
          runtimeMode,
          subagentPlan: assignedSubagentPlan,
        },
        120000
      );

      if (payload.projects) {
        setProjects(payload.projects);
      }

      if (payload.session) {
        setActiveSessionId(payload.session.sessionId);
        setSession(payload.session);
        setTerminalOutput(payload.session.output || "");
        if (payload.session.projectSlug) {
          setSelectedProject(payload.session.projectSlug);
          onSceneFocus?.(payload.session.projectSlug);
        }
      }

      if (createFreshProject && payload.session?.projectSlug) {
        setSelectedProject(payload.session.projectSlug);
      }

      if (payload.session?.projectName) {
        setNewProjectName(payload.session.projectName);
      }
      setRequirement("");
      setAssignedSubagentPlan(null);
    } catch (nextError) {
      setError(`No fue posible arrancar la instancia de Codex: ${humanizeAgentError(nextError)}`);
    } finally {
      setIsSending(false);
    }
  }

  async function handleStopSession() {
    if (!activeSessionId) return;
    setError("");
    try {
      const payload = await emitWithAck(socketRef.current, "agent:session:stop", { sessionId: activeSessionId });
      if (payload.session) {
        setSession(payload.session);
      }
    } catch (nextError) {
      setError(`No fue posible detener la sesion: ${humanizeAgentError(nextError)}`);
    }
  }

  async function handleSyncArchitecture() {
    setIsSyncing(true);
    setError("");
    try {
      await emitWithAck(socketRef.current, "agent:architecture:rescan", {});
    } catch (nextError) {
      setError(`No fue posible sincronizar el mapa: ${humanizeAgentError(nextError)}`);
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleResetRuntime() {
    setIsResettingRuntime(true);
    setError("");
    try {
      const response = await fetch("/api/runtime/reset", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          port: 5001,
          host: "127.0.0.1",
          openBrowser: true,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (response.status === 404) {
        throw new Error("runtime_reset_endpoint_missing");
      }
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || payload?.message || "runtime_reset_failed");
      }
      const nextAppUrl = String(payload?.appUrl || "http://127.0.0.1:5001/").trim();
      setError(`Restableciendo seccion. Redirigiendo a ${nextAppUrl}...`);
      window.setTimeout(() => {
        window.location.assign(nextAppUrl);
      }, Number(payload?.redirectDelayMs || 3500));
    } catch (nextError) {
      setError(`No fue posible restablecer el runtime: ${humanizeRuntimeResetError(nextError)}`);
      setIsResettingRuntime(false);
    }
  }

  async function handleRelaunchRetryableTask() {
    const projectSlug = reviewerProjectSlug || selectedProject;
    if (!projectSlug) {
      setError("Selecciona un proyecto existente para retomar una orden recuperada.");
      return;
    }
    if (!retryableTask?.id) {
      setError("No hay una orden recuperable para este proyecto.");
      return;
    }

    setLaunchMode("existing");
    setIsRelaunchingTask(true);
    setError("");
    try {
      const response = await fetch(`/api/agent/projects/${encodeURIComponent(projectSlug)}/retryable-task/relaunch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          taskId: retryableTask.id,
          runtimeMode,
          forceClean: true,
          subagentPlan: assignedSubagentPlan,
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.lock?.message || payload?.error || "retryable_task_relaunch_failed");
      }
      if (payload.projects) setProjects(payload.projects);
      if (payload.session) {
        setActiveSessionId(payload.session.sessionId);
        setSession(payload.session);
        setTerminalOutput(payload.session.output || "");
        if (payload.session.projectSlug) {
          setSelectedProject(payload.session.projectSlug);
          onSceneFocus?.(payload.session.projectSlug);
        }
      }
      setRetryableTask(payload.task || retryableTask);
      setVisualState({
        op: "retryable_task_relaunched",
        phase: "runtime-retry",
        message: `Orden recuperada relanzada: ${payload.task?.id || retryableTask.id}.`,
      });
      pushAgentBurst({
        source: "Runtime",
        message: `Retomando ${payload.task?.id || retryableTask.id} sobre el mismo workspace.`,
        tone: "final",
      });
      setError(`Orden recuperada relanzada sobre el mismo proyecto: ${payload.task?.id || retryableTask.id}.`);
    } catch (nextError) {
      setError(`No fue posible relanzar la orden recuperada: ${humanizeRuntimeResetError(nextError)}`);
    } finally {
      setIsRelaunchingTask(false);
    }
  }

  async function handleClearPendingQueue() {
    const projectSlug = reviewerProjectSlug || selectedProject;
    if (!projectSlug) {
      setError("Selecciona un proyecto antes de borrar colas pendientes.");
      return;
    }
    const forceClear = Boolean(liveActive);

    setIsClearingPendingQueue(true);
    setError("");
    try {
      const response = await fetch(`/api/agent/projects/${encodeURIComponent(projectSlug)}/pending-queue/clear`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          statuses: forceClear ? ["queued", "starting", "running", "pending", "blocked"] : ["pending", "blocked"],
          force: forceClear,
          source: forceClear ? "human_force_queue_clear_button" : "human_button",
        }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.lock?.message || payload?.error || "pending_queue_clear_failed");
      }
      if (payload.projects) setProjects(payload.projects);
      setVisualState({
        op: "pending_queue_cleared",
        phase: "cleanup",
        message: `${payload.force ? "Limpieza forzada de colas" : "Colas pendientes borradas"}: ${payload.removedCount || 0}.`,
      });
      pushAgentBurst({
        source: "Runtime",
        message: `${payload.force ? "Limpieza forzada de colas" : "Colas pendientes borradas"}: ${payload.removedCount || 0}. Backup: ${payload.backupDir || "registrado"}.`,
        tone: "final",
      });
      setError(`${payload.force ? "Limpieza forzada de colas" : "Colas pendientes borradas"}: ${payload.removedCount || 0}. Backup: ${payload.backupDir || "registrado"}.`);
    } catch (nextError) {
      setError(`No fue posible borrar colas pendientes: ${humanizeRuntimeResetError(nextError)}`);
    } finally {
      setIsClearingPendingQueue(false);
    }
  }

  async function handleCleanWorkspace() {
    if (workspaceCleanKeyword.trim() !== "HABLA") {
      setError("La palabra clave de autorizacion no coincide.");
      return;
    }
    if (workspaceCleanNeedsSafetyPhrase && !workspaceCleanConfirmationOk) {
      setError("El protocolo exige escribir si o confirmar para blanqueo total en modo medium o long-run.");
      return;
    }
    setIsCleaningWorkspace(true);
    setError("");
    try {
      const response = await fetch("/api/runtime/clean-workspace", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          confirmDeleteProjects: true,
          authorizationKeyword: workspaceCleanKeyword.trim(),
          confirmationPhrase: workspaceCleanConfirmation.trim(),
          cleanScope: "total",
          runtimeMode,
          source: "human_button",
          rootCause: "Solicitud manual desde Blanquear Workspace.",
          evidence: ["usuario activo el boton Blanquear Workspace"],
        }),
      });
      const payload = await response.json().catch(() => null);
      if (response.status === 409 && payload?.error === "blanqueo_confirmation_required") {
        setError(payload.decisionSummary || "El protocolo exige confirmacion humana adicional para blanqueo total.");
        return;
      }
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || "workspace_cleanup_failed");
      }
      setProjects([]);
      setLaunchMode("new");
      setSelectedProject("");
      setNewProjectName(buildGeneratedProjectName());
      setRequirement("");
      setActiveSessionId(null);
      setSession(null);
      setTerminalOutput("");
      setAgentRoomEvents([]);
      setSubagentPlan(null);
      setAssignedSubagentPlan(null);
      setVisualState({ op: "workspace_cleaned", phase: "cleanup", message: "Workspace blanqueado." });
      setReviewerEvents([]);
      setReviewerStatus(null);
      setReviewerOpen(false);
      setEmailCommandHistory([]);
      setWorkspaceCleanOpen(false);
      setWorkspaceCleanStep(1);
      setWorkspaceCleanKeyword("");
      setWorkspaceCleanConfirmation("");
      onWorkspaceClean?.(payload);
      onSceneFocus?.("");
      pushAgentBurst({
        source: "Runtime",
        message: `Workspace blanqueado (${payload.scope || "total"}): ${payload.removedProjects || 0} proyecto(s) eliminados. Backup: ${payload.backup?.backup_dir || "registrado"}.`,
        tone: "final",
      });
    } catch (nextError) {
      setError(`No fue posible blanquear el workspace: ${humanizeRuntimeResetError(nextError)}`);
    } finally {
      setIsCleaningWorkspace(false);
    }
  }

  const selectedRuntimePreset = RUNTIME_MODE_PRESETS.find((preset) => preset.value === runtimeMode) || RUNTIME_MODE_PRESETS[1];
  const workspaceCleanNeedsSafetyPhrase = runtimeMode === "medium" || runtimeMode === "long-run";
  const workspaceCleanConfirmationOk = ["si", "confirmar", "confirmo"].includes(normalizeShortConfirmation(workspaceCleanConfirmation));
  const workspaceCleanReady = workspaceCleanKeyword.trim() === "HABLA" && (!workspaceCleanNeedsSafetyPhrase || workspaceCleanConfirmationOk);

  return (
    <>
    <section className="agent-panel">
      <div className="panel-header">
        <div>
          <h2>Agente Codex</h2>
          <p>Canal persistente tipo worker con sesion viva, terminal acoplada y proyectos ordenados dentro del workspace.</p>
        </div>
        <div className="agent-header-actions">
          <span className={`socket-pill ${connected ? "is-online" : "is-offline"}`}>
            {connected ? "Worker conectado" : "Worker desconectado"}
          </span>
          <span className={`socket-pill ${hablaRuntimeAvailable ? "is-online" : "is-offline"}`}>
            {hablaRuntimeLabel}
          </span>
          <span className={`socket-pill ${session?.status === "running" || session?.status === "starting" ? "is-online" : "is-offline"}`}>
            {session ? formatAgentStatus(session.status) : "Sin sesion"}
          </span>
          <span className={`socket-pill ${visualState?.phase || visualState?.op ? "is-online" : "is-offline"}`}>
            {visualState?.phase ? `Fase ${visualState.phase}` : "Sin flujo visual"}
          </span>
          <button
            type="button"
            className="tool-button"
            onClick={() => {
              reviewerUserMinimizedRef.current = false;
              setReviewerOpen(true);
              setReviewerMinimized(false);
            }}
            disabled={!session && !reviewerProjectSlug}
          >
            Supervisor en vivo
          </button>
          <button type="button" className="tool-button" onClick={handleSyncArchitecture} disabled={isSyncing || !connected}>
            {isSyncing ? "Sincronizando..." : "Sincronizar mapa"}
          </button>
          <button type="button" className="tool-button danger" onClick={handleResetRuntime} disabled={isResettingRuntime}>
            {isResettingRuntime ? "Restableciendo seccion..." : "Restablecer seccion"}
          </button>
          <button
            type="button"
            className="tool-button danger"
            onClick={handleClearPendingQueue}
            disabled={isClearingPendingQueue || liveActive || !reviewerProjectSlug}
          >
            {isClearingPendingQueue ? "Borrando colas..." : "Borrar colas pendientes"}
          </button>
          <button
            type="button"
            className="tool-button danger"
            onClick={() => {
              setWorkspaceCleanOpen(true);
              setWorkspaceCleanStep(1);
              setWorkspaceCleanKeyword("");
              setWorkspaceCleanConfirmation("");
            }}
            disabled={isCleaningWorkspace}
          >
            {isCleaningWorkspace ? "Blanqueando..." : "Blanquear workspace"}
          </button>
        </div>
      </div>

      <div className="agent-grid">
        <div className="agent-controls">
          <div className="toolbar-group email-command-panel">
            <span className="toolbar-label">Correo ejecutable</span>
            <div className="email-command-status-row">
              <span className={`socket-pill ${emailCommandStatus?.enabled ? "is-online" : "is-offline"}`}>
                {emailCommandStatus?.enabled ? "buzon activo" : "buzon local"}
              </span>
              <span className={`socket-pill ${emailCommandStatus?.imapConfigured ? "is-online" : "is-offline"}`}>
                {emailCommandStatus?.imapConfigured ? "IMAP configurado" : "IMAP pendiente"}
              </span>
              <span className="meta-pill">pendientes: {emailCommandStatus?.counts?.pending || 0}</span>
              <span className="meta-pill">iniciados: {emailCommandStatus?.counts?.started || 0}</span>
              <span className="meta-pill">token: {emailCommandStatus?.tokenRequired ? "requerido" : "opcional"}</span>
            </div>
            <div className="email-command-copy">
              <strong>{emailCommandMessage || "Esperando orden por email autorizada."}</strong>
              <span>Asunto esperado: {emailCommandStatus?.subjectPrefix || "[HABLA]"} Nombre del proyecto</span>
              <small>El correo llena este chat y arranca un proyecto nuevo por el mismo runtime, sin crear un camino paralelo.</small>
            </div>
            <div className="toolbar-inline compact">
              <button
                type="button"
                className="tool-button primary"
                onClick={() => {
                  setEmailConfigOpen(true);
                  loadEmailCommandConfig();
                }}
              >
                Configurar correo entrante
              </button>
            </div>
            {emailCommandHistory.length ? (
              <div className="email-command-history">
                {emailCommandHistory.map((command) => (
                  <article key={command.id} className={`email-command-card is-${command.status || "pending"}`}>
                    <strong>{command.projectName || command.projectSlug}</strong>
                    <span>{command.status || "pending"} · {command.runtimeMode || "long-run"}</span>
                    <small>{command.sender || command.source || "email"}</small>
                  </article>
                ))}
              </div>
            ) : null}
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Proyecto de trabajo</span>
            <div className="toolbar-inline compact">
              <button
                type="button"
                className={`tool-button ${launchMode === "new" ? "primary" : ""}`}
                onClick={() => handleSelectLaunchMode("new")}
              >
                Iniciar proyecto nuevo
              </button>
              <button
                type="button"
                className={`tool-button ${launchMode === "existing" ? "primary" : ""}`}
                onClick={() => handleSelectLaunchMode("existing")}
              >
                Continuar proyecto existente
              </button>
            </div>

            {launchMode === "new" ? (
              <div className="toolbar-inline compact">
                <label className="editor-field small grow">
                  <span>Nombre del proyecto nuevo</span>
                  <input
                    value={newProjectName}
                    onChange={(event) => {
                      const nextValue = event.target.value;
                      setNewProjectName(nextValue);
                      if (selectedProjectMeta && nextValue.trim() !== (selectedProjectMeta.name || "").trim()) {
                        setSelectedProject("");
                        onSceneFocus?.("");
                      }
                    }}
                    placeholder="payments-orchestrator"
                  />
                </label>
                <button type="button" className="tool-button" onClick={handleCreateProject} disabled={isCreatingProject || !connected}>
                  {isCreatingProject ? "Preparando..." : "Preparar carpeta nueva"}
                </button>
              </div>
            ) : (
              <div className="toolbar-inline compact">
                <label className="editor-field small grow">
                  <span>Proyecto existente</span>
                  <select
                    value={selectedProject}
                    onChange={(event) => {
                      setSelectedProject(event.target.value);
                      setError("");
                    }}
                  >
                    <option value="">selecciona un proyecto</option>
                    {projects.map((project) => (
                      <option key={project.slug} value={project.slug}>
                        {project.name} · {project.relativePath}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="button" className="tool-button" onClick={handleOpenExistingProject} disabled={!selectedProject || !connected}>
                  Abrir proyecto
                </button>
              </div>
            )}

            <div className="agent-project-meta">
              <strong>
                {launchMode === "new"
                  ? (newProjectName || "nuevo-proyecto automatico")
                  : (selectedProjectMeta?.name || "sin proyecto seleccionado")}
              </strong>
              <span>
                {launchMode === "new"
                  ? (selectedProjectMeta?.relativePath || "workspace/projects/<nuevo-proyecto>")
                  : (selectedProjectMeta?.relativePath || "selecciona un proyecto del listado")}
              </span>
              <small>
                {launchMode === "new"
                  ? (selectedProjectMeta
                    ? "carpeta nueva preparada; al iniciar se trabajara solo sobre esta escena vacia"
                    : "si inicias aqui, el mapa arrancara desde cero y solo mostrara este proyecto")
                  : (selectedProjectMeta ? `${selectedProjectMeta.fileCount} archivos detectados en el proyecto seleccionado` : "abre un proyecto existente para continuar ahi")}
              </small>
            </div>

            {launchMode === "existing" && selectedProject ? (
              <div className={`agent-retry-card ${retryableTask ? "is-ready" : "is-empty"}`}>
                <div>
                  <strong>{retryableTask ? "Ultima orden recuperada" : "Orden recuperable"}</strong>
                  <span>
                    {isLoadingRetryableTask
                      ? "buscando backups y cola del runtime..."
                      : retryableTask
                        ? `${retryableTask.id} · ${retryableTask.status || "sin estado"}`
                        : "no hay orden anterior lista para retomar"}
                  </span>
                  <small>
                    {retryableTask?.goalPreview
                      ? retryableTask.goalPreview
                      : "La accion trabaja sobre el mismo workspace; no crea proyecto nuevo ni blanquea archivos."}
                  </small>
                </div>
                {retryableTask ? (
                  <button
                    type="button"
                    className="tool-button primary"
                    onClick={handleRelaunchRetryableTask}
                    disabled={!connected || isRelaunchingTask || isSending}
                  >
                    {isRelaunchingTask ? "Retomando..." : "Retomar aqui"}
                  </button>
                ) : null}
              </div>
            ) : null}

            <div className="toolbar-inline compact">
              <label className="editor-field small grow">
                <span>Modo de procesamiento</span>
                <select
                  value={runtimeMode}
                  onChange={(event) => {
                    setRuntimeMode(event.target.value);
                    setError("");
                  }}
                  disabled={isSending || liveActive}
                >
                  {RUNTIME_MODE_PRESETS.map((preset) => (
                    <option key={preset.value} value={preset.value}>
                      {preset.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="agent-project-meta">
              <strong>{selectedRuntimePreset.label} · runtime {runtimeMode}</strong>
              <span>{selectedRuntimePreset.detail}</span>
              <small>
                Facil evita meter tareas pequenas en ciclos largos; Extradificil usa el flujo largo cuando el proyecto de verdad lo necesita.
              </small>
            </div>

            <div className={`subagent-orchestrator ${assignedSubagentPlan ? "is-assigned" : ""}`}>
              <div className="subagent-orchestrator-head">
                <div>
                  <strong>Orquestador de subagentes</strong>
                  <span>{assignedSubagentPlan ? "subagentes entregados al agente principal" : "primero calcula, despues asigna por boton"}</span>
                </div>
                <div className="toolbar-inline compact">
                  <button
                    type="button"
                    className="tool-button"
                    onClick={handlePlanSubagents}
                    disabled={isPlanningSubagents || isSending || !requirement.trim() || (launchMode === "existing" && !selectedProjectMeta)}
                  >
                    {isPlanningSubagents ? "Calculando..." : "Calcular subagentes"}
                  </button>
                  <button
                    type="button"
                    className="tool-button primary"
                    onClick={handleAssignSubagents}
                    disabled={!subagentPlan?.roster?.length || isSending}
                  >
                    {assignedSubagentPlan ? "Subagentes asignados" : `Asignar ${subagentPlan?.recommendedAgents || 0}`}
                  </button>
                </div>
              </div>

              {subagentPlan ? (
                <div className="subagent-plan-card">
                  <div className="subagent-plan-summary">
                    <strong>{subagentPlan.summary}</strong>
                    <span>{subagentPlan.turnPolicy || "turnos serializados"} · {subagentPlan.reasoningPolicy || "razonamiento publico"}</span>
                    {subagentPlan.complexityEstimate ? (
                      <span>
                        {subagentPlan.difficultyLabel || subagentPlan.complexityEstimate.difficulty_label || "Dificultad no declarada"} · score {subagentPlan.complexityScore ?? subagentPlan.complexityEstimate.score ?? "n/a"} · ciclos {subagentPlan.recommendedLaceCycles ?? subagentPlan.complexityEstimate.recommended_lace_cycles ?? "n/a"} · tareas {subagentPlan.recommendedMaxTasks ?? subagentPlan.complexityEstimate.max_tasks ?? "n/a"} · timeout {subagentPlan.recommendedTimeoutSeconds ?? subagentPlan.complexityEstimate.timeout_seconds ?? "n/a"}s
                      </span>
                    ) : null}
                  </div>
                  <div className="subagent-roster">
                    {(subagentPlan.roster || []).map((agent) => (
                      <article key={agent.id} className="subagent-chip" style={{ "--agent-color": agent.color || "#38bdf8" }}>
                        <b>{agent.id}</b>
                        <strong>{agent.name}</strong>
                        <span>{agent.role}</span>
                      </article>
                    ))}
                  </div>
                  {subagentPlan.reasons?.length ? (
                    <small>{subagentPlan.reasons.join(" · ")}</small>
                  ) : null}
                </div>
              ) : (
                <div className="subagent-plan-empty">
                  <strong>Sin dictamen todavia</strong>
                  <span>El calculo usa prompt, modo de procesamiento y tamano del proyecto seleccionado.</span>
                </div>
              )}
            </div>
          </div>

          <div className="toolbar-group har-panel">
            <div className="har-panel-head">
              <span className="toolbar-label">Human Alignment Review</span>
              <span className={`socket-pill ${harReview ? "is-online" : "is-offline"}`}>
                {harReview?.status || "sin HAR"}
              </span>
            </div>
            <div className="toolbar-inline compact">
              <button
                type="button"
                className="tool-button"
                onClick={() => loadHumanAlignmentReview(reviewerProjectSlug)}
                disabled={!reviewerProjectSlug || isHarLoading}
              >
                {isHarLoading ? "Actualizando..." : "Actualizar HAR"}
              </button>
              <button
                type="button"
                className="tool-button primary"
                onClick={handleCreateHumanAlignmentReview}
                disabled={!reviewerProjectSlug || isHarSubmitting}
              >
                {harReview ? "Abrir ciclo HAR" : "Crear HAR"}
              </button>
            </div>

            {harReview ? (
              <div className="har-review-card">
                <div className="har-summary-row">
                  <strong>{harReview.id}</strong>
                  <span>{harReview.summary?.project_status || "estado no registrado"}</span>
                  <small>{harReviews.length} revision(es)</small>
                </div>
                {harDecisionEntries.length ? (
                  <div className="har-decision-list">
                    {harDecisionEntries.slice(0, 4).map((decision) => (
                      <span key={decision}>{decision}</span>
                    ))}
                  </div>
                ) : null}
                {harStackEntries.length ? (
                  <div className="har-stack-row">
                    {harStackEntries.slice(0, 10).map((entry) => (
                      <span key={`${entry.category}-${entry.value}`} className="meta-pill">
                        {entry.category}: {entry.value}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="agent-project-meta">
                <strong>{reviewerProjectSlug || "sin proyecto"}</strong>
                <span>HAR se abre al cierre tecnico o desde este panel.</span>
              </div>
            )}

            <div className="toolbar-inline compact">
              <label className="editor-field small grow">
                <span>Categoria stack</span>
                <select
                  value={harPreferenceCategory}
                  onChange={(event) => setHarPreferenceCategory(event.target.value)}
                  disabled={!harCategoryOptions.length}
                >
                  {harCategoryOptions.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </label>
              <label className="editor-field small grow">
                <span>Preferencia</span>
                <select
                  value={harPreferenceValue}
                  onChange={(event) => setHarPreferenceValue(event.target.value)}
                  disabled={!harValueOptions.length}
                >
                  {harValueOptions.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="tool-button" onClick={handleAddHarPreference} disabled={!harValueOptions.length}>
                Agregar
              </button>
            </div>

            {harSelectedPreferenceEntries.length ? (
              <div className="har-stack-row">
                {harSelectedPreferenceEntries.map((entry) => (
                  <button
                    type="button"
                    key={`${entry.category}-${entry.value}`}
                    className="har-preference-chip"
                    onClick={() => handleRemoveHarPreference(entry.category, entry.value)}
                  >
                    {entry.category}: {entry.value} ×
                  </button>
                ))}
              </div>
            ) : null}

            <label className="editor-field">
              <span>Feedback humano</span>
              <textarea
                rows={4}
                value={harFeedback}
                onChange={(event) => setHarFeedback(event.target.value)}
                placeholder="Cambiar PostgreSQL por SQL Server; mantener Three.js; priorizar backend FastAPI."
              />
            </label>
            <div className="toolbar-inline compact">
              <button
                type="button"
                className="tool-button primary"
                onClick={handleSubmitHumanAlignmentFeedback}
                disabled={!harReview?.id || !harFeedback.trim() || isHarSubmitting}
              >
                {isHarSubmitting ? "Registrando..." : "Enviar ajustes HAR"}
              </button>
              {harMessage ? <span className="har-message">{harMessage}</span> : null}
            </div>
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Chat de requerimientos</span>
            <label className="editor-field">
              <span>{launchMode === "new" ? "Objetivo del proyecto nuevo" : "Objetivo para continuar el proyecto seleccionado"}</span>
              <textarea
                rows={8}
                value={requirement}
                onChange={(event) => setRequirement(event.target.value)}
                placeholder="Crea un nuevo programa al lado del ecosistema actual con frontend React, backend Python, una capa shared y pruebas. Conectalo con el backend principal y diseña los flujos internos."
              />
            </label>

            <div className="toolbar-inline">
              <button
                type="button"
                className="tool-button primary"
                onClick={handleSendRequirement}
                disabled={isSending || !requirement.trim() || !connected || (launchMode === "existing" && !selectedProjectMeta)}
              >
                {isSending
                  ? "Abriendo Codex..."
                  : launchMode === "new"
                    ? "Iniciar proyecto nuevo"
                    : "Continuar proyecto existente"}
              </button>
              <button type="button" className="tool-button danger" onClick={handleStopSession} disabled={!activeSessionId || session?.status !== "running"}>
                Detener sesion
              </button>
            </div>

            {error ? <p className="agent-error">{error}</p> : null}
          </div>
        </div>

        <div className="agent-terminal-shell">
          <div className="agent-terminal-meta">
            <div>
              <strong>Terminal viva de Codex CLI</strong>
              <span>{session?.projectDir || selectedProjectMeta?.path || "workspace/projects"}</span>
            </div>
            <small>
              {session
                ? `PID ${session.pid || "..."} · ${formatAgentStatus(session.status)}${session.errorCode ? ` · ${session.errorCode}` : ""}${session.visualEventCount != null ? ` · ${session.visualEventCount} evento(s)` : ""}`
                : "esperando instruccion"}
            </small>
          </div>

          <div className={`agent-live-pulse is-${liveStage} ${liveActive ? "is-active" : ""}`}>
            <div className="agent-live-orb" aria-hidden="true">
              <span className="agent-live-orb-core" />
              <span className="agent-live-orb-dot dot-a" />
              <span className="agent-live-orb-dot dot-b" />
              <span className="agent-live-orb-dot dot-c" />
            </div>
            <div className="agent-live-copy">
              <span>{getLiveStageLabel(liveStage)}</span>
              <strong>{liveActive ? "Agentes en movimiento" : formatAgentStatus(session?.status)}</strong>
              <small>{liveActive ? "Pulso conectado a eventos reales del runtime" : "El aro se activa al iniciar una sesion"}</small>
            </div>
            <div className="agent-live-timer">
              <span>Cronometro</span>
              <strong>{formatDuration(liveElapsedSeconds)}</strong>
              <small>{session?.sessionId || "sin sesion"}</small>
            </div>
          </div>

          <div className="agent-progress">
            <div className="agent-progress-meta">
              <strong>{getProgressLabel(session)}</strong>
              <span>{getProgressPercent(session)}%</span>
            </div>
            <div className="agent-progress-track" aria-label="Progreso de la sesion del agente">
              <div className="agent-progress-fill" style={{ width: `${getProgressPercent(session)}%` }} />
            </div>
            <small>
              {session?.firstOutputAt
                ? `Codex ya respondio por terminal${session?.lastHeartbeatAt ? ` · ultimo heartbeat ${session.lastHeartbeatAt}` : ""}`
                : "Esperando primera salida de terminal o primer evento del bridge"}
            </small>
          </div>

          {visualNote ? (
            <div className="agent-visual-note">
              {visualNote}
            </div>
          ) : null}

          <div ref={terminalRef} className="agent-console-canvas" role="log" aria-live="polite">
            <div className="agent-console-canvas-head">
              <div>
                <strong>Sala interna de agentes</strong>
                <span>eventos publicos por turnos · terminal viva · evidencia real</span>
              </div>
              <small>{agentRoomEvents.length} evento(s)</small>
            </div>

            <div className="agent-console-stream">
              {agentRoomEvents.length ? agentRoomEvents.map((event) => (
                <article key={event.id} className={`agent-console-event is-${event.tone || "middle"}`}>
                  <div className="agent-console-avatar">
                    <strong>{event.agentId}</strong>
                    <span>{event.kind}</span>
                  </div>
                  <div className="agent-console-message">
                    <div>
                      <strong>{event.agentName}</strong>
                      <small>{event.at}</small>
                    </div>
                    <p>{event.message}</p>
                    {event.detail ? <code>{event.detail}</code> : null}
                  </div>
                </article>
              )) : (
                <div className="agent-console-empty">
                  <strong>La sala se activara con el primer dictamen o evento real.</strong>
                  <span>No se mostrara razonamiento privado; aqui aparecen decisiones publicas, acciones, herramientas, observaciones y evidencia.</span>
                </div>
              )}
            </div>

            <details className="agent-raw-terminal">
              <summary>Terminal cruda de Codex CLI</summary>
              <pre className="agent-terminal is-raw">
                {terminalOutput || "La terminal del agente aparecera aqui cuando envies el primer requerimiento."}
              </pre>
            </details>
          </div>
        </div>

        <div className="agent-runtime-shell">
          <div className="toolbar-group">
            <span className="toolbar-label">Preflight HABLA y LACE</span>
            <div className="habla-pill-row">
              <span className={`socket-pill ${hablaRuntimeAvailable ? "is-online" : "is-offline"}`}>
                {hablaRuntimeAvailable ? "HABLA activo" : "HABLA ausente"}
              </span>
              <span className="meta-pill">{hablaRuntimeLabel}</span>
              <span className={`socket-pill ${lacePolicyLoaded ? "is-online" : "is-offline"}`}>
                LACE policy: {booleanLabel(lacePolicyLoaded)}
              </span>
              <span className="meta-pill">LACE runtime: {laceRuntimeLabel}</span>
              <span className="meta-pill">{hablaState?.knowledgeType || "sin clasificar"}</span>
              <span className="meta-pill">{hablaState?.toolRequired || "sin herramienta"}</span>
              <span className="meta-pill">safe: {booleanLabel(hablaState?.safeToAnswer)}</span>
              <span className={`socket-pill ${hablaState?.blocked ? "is-offline" : "is-online"}`}>
                bloqueado: {booleanLabel(hablaState?.blocked)}
              </span>
              <span className="meta-pill">{getLaceProgress(session)}</span>
              <button type="button" className="tool-button" onClick={loadHablaRuntimeStatus}>
                Actualizar motor
              </button>
            </div>

            <div className="agent-project-meta habla-meta-grid">
              <strong>{hablaState?.strategy || hablaRuntimeLabel}</strong>
              <span>{hablaState?.triangulatedText || hablaState?.answerPreview || "Todavia no hay triangulacion visible del motor."}</span>
              <small>
                {hablaConfidence
                  ? `Confianza global ${Number(hablaConfidence.global || 0).toFixed(1)} · dato ${hablaConfidence.dato || 0} · fuente ${hablaConfidence.fuente || 0}`
                  : "Sin confianza calculada"}
              </small>
              {session?.hablaPreflightPath ? <small>{session.hablaPreflightPath}</small> : null}
              {hablaRuntimeState?.engineRoot ? <small>root: {hablaRuntimeState.engineRoot}</small> : null}
              {lacePolicyPath ? <small>LACE: {lacePolicyPath}</small> : null}
              {hablaRuntimeState?.memoryPath ? <small>{hablaRuntimeState.memoryPath}</small> : null}
              {hablaState?.error ? <p className="agent-error">{hablaState.error}</p> : null}
              {hablaRuntimeError ? <p className="agent-error">{hablaRuntimeError}</p> : null}
            </div>

            {hablaState?.debug?.length ? (
              <div className="agent-debug-list">
                {hablaState.debug.map((item, index) => (
                  <code key={`${index}-${item}`}>{item}</code>
                ))}
              </div>
            ) : null}

            {laceCycles.length ? (
              <div className="agent-cycle-grid">
                {laceCycles.map((cycle) => (
                  <article
                    key={cycle.cycle}
                    className={[
                      "agent-cycle-card",
                      `is-${cycle.stage || "pending"}`,
                      cycle.isCurrent ? "is-current" : "",
                    ].filter(Boolean).join(" ")}
                  >
                    <strong>Ciclo {String(cycle.cycle).padStart(2, "0")}</strong>
                    <span>{cycle.stage || "pending"}</span>
                    <small>{cycle.focus || "sin foco"}</small>
                    <p>{cycle.description || "Sin evidencia registrada todavía."}</p>
                  </article>
                ))}
              </div>
            ) : null}

            {hablaState?.subTasks?.length ? (
              <div className="agent-cycle-grid">
                {hablaState.subTasks.map((task) => (
                  <article key={task.taskId} className={`agent-cycle-card is-${task.status || "pending"}`}>
                    <strong>{task.taskId}</strong>
                    <span>{task.status || "pending"}</span>
                    <small>{task.toolName || "sin tool"}</small>
                    <p>{task.description || task.resultText || "Sin detalle."}</p>
                  </article>
                ))}
              </div>
            ) : null}

            {hablaState?.directive ? (
              <label className="editor-field">
                <span>Directiva HABLA para Codex</span>
                <textarea className="code-editor" rows={7} value={hablaState.directive} readOnly />
              </label>
            ) : null}

            {habla?.prompt ? (
              <label className="editor-field">
                <span>Prompt HABLA BASIC procedural</span>
                <textarea className="code-editor" rows={10} value={habla.prompt} readOnly />
              </label>
            ) : null}
          </div>
        </div>
      </div>
    </section>
    {closureModalOpen ? (
      <div className="session-closure-overlay" role="dialog" aria-modal="true" aria-label={closureCertificate.title}>
        <div className={`session-closure-modal ${closureCertificate.completed ? "is-success" : "is-failure"}`}>
          <div className="session-closure-icon" aria-hidden="true">
            {closureCertificate.completed ? "✓" : "×"}
          </div>
          <div className="session-closure-body">
            <span className="toolbar-label">Certificado del runtime</span>
            <h2>{closureCertificate.title}</h2>
            <p>{closureCertificate.message}</p>
            <div className="session-closure-grid">
              <div>
                <strong>Estado</strong>
                <span>{closureCertificate.statusLabel}</span>
              </div>
              <div>
                <strong>Proyecto</strong>
                <span>{closureCertificate.project}</span>
              </div>
              <div>
                <strong>Tarea final</strong>
                <span>{closureCertificate.taskId}</span>
              </div>
              <div>
                <strong>Validacion</strong>
                <span>{closureCertificate.validationLabel}</span>
              </div>
              <div>
                <strong>Evidencia encontrada</strong>
                <span>{closureCertificate.foundLabel}</span>
              </div>
              <div>
                <strong>Evidencia faltante</strong>
                <span>{closureCertificate.missingLabel}</span>
              </div>
              <div className="session-closure-wide">
                <strong>Checkpoint</strong>
                <span>{closureCertificate.checkpointPath || "sin checkpoint final registrado"}</span>
              </div>
              {!closureCertificate.completed ? (
                <div className="session-closure-wide">
                  <strong>Bloqueo</strong>
                  <span>{closureCertificate.blockerLabel}</span>
                </div>
              ) : null}
            </div>
            <div className="reviewer-actions">
              <button type="button" className="tool-button primary" onClick={() => setDismissedClosureKey(closureCertificate.key)}>
                Cerrar certificado
              </button>
              {!closureCertificate.completed ? (
                <button
                  type="button"
                  className="tool-button"
                  onClick={() => {
                    reviewerUserMinimizedRef.current = false;
                    setReviewerOpen(true);
                    setReviewerMinimized(false);
                    setDismissedClosureKey(closureCertificate.key);
                  }}
                >
                  Ver supervisor
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    ) : null}
    {emailConfigOpen ? (
      <div className="email-config-overlay" role="dialog" aria-label="Configurar correo entrante HABLA">
        <div className="email-config-modal">
          <div className="reviewer-header">
            <div>
              <h2>Correo Entrante HABLA</h2>
              <p>Configura el buzon que convierte emails autorizados en proyectos nuevos del runtime.</p>
            </div>
            <div className="reviewer-actions">
              <button type="button" className="tool-button" onClick={() => setEmailConfigOpen(false)}>Cerrar</button>
            </div>
          </div>

          <div className="email-config-grid">
            <label className="observer-rule email-config-toggle">
              <input
                type="checkbox"
                checked={emailConfig?.enabled === true}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), enabled: event.target.checked }))}
              />
              <span>Activar lectura de correo entrante</span>
            </label>

            <label className="editor-field small">
              <span>Prefijo de asunto</span>
              <input
                value={emailConfig?.subjectPrefix || ""}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), subjectPrefix: event.target.value }))}
                placeholder="[HABLA]"
              />
            </label>

            <label className="editor-field small">
              <span>Modo por defecto</span>
              <select
                value={emailConfig?.defaultRuntimeMode || "long-run"}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), defaultRuntimeMode: event.target.value }))}
              >
                <option value="smoke">smoke</option>
                <option value="build">build</option>
                <option value="medium">medium</option>
                <option value="long-run">long-run</option>
              </select>
            </label>

            <label className="editor-field small">
              <span>Token de orden</span>
              <input
                value={emailConfig?.commandToken || ""}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), commandToken: event.target.value }))}
                placeholder="clave-secreta"
              />
            </label>

            <label className="editor-field small grow email-config-wide">
              <span>Remitentes autorizados</span>
              <textarea
                rows={3}
                value={(emailConfig?.allowedSenders || []).join("\n")}
                onChange={(event) => setEmailConfig((current) => ({
                  ...(current || {}),
                  allowedSenders: event.target.value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean),
                }))}
                placeholder="tu-correo@dominio.com"
              />
            </label>

            <label className="editor-field small">
              <span>IMAP host</span>
              <input
                value={emailConfig?.imapHost || ""}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), imapHost: event.target.value }))}
                placeholder="imap.tucorreo.com"
              />
            </label>

            <label className="editor-field small">
              <span>IMAP puerto</span>
              <input
                type="number"
                value={emailConfig?.imapPort || 993}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), imapPort: Number(event.target.value || 993) }))}
              />
            </label>

            <label className="editor-field small">
              <span>Usuario IMAP</span>
              <input
                value={emailConfig?.imapUsername || ""}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), imapUsername: event.target.value }))}
                placeholder="usuario@dominio.com"
              />
            </label>

            <label className="editor-field small">
              <span>Clave IMAP</span>
              <input
                type="password"
                value={emailConfig?.imapPassword || ""}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), imapPassword: event.target.value }))}
                placeholder={emailConfig?.hasImapPassword ? "guardada; escribe para cambiar" : "clave o app password"}
              />
            </label>

            <label className="editor-field small">
              <span>Mailbox</span>
              <input
                value={emailConfig?.imapMailbox || "INBOX"}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), imapMailbox: event.target.value }))}
              />
            </label>

            <label className="observer-rule email-config-toggle">
              <input
                type="checkbox"
                checked={emailConfig?.imapSsl !== false}
                onChange={(event) => setEmailConfig((current) => ({ ...(current || {}), imapSsl: event.target.checked }))}
              />
              <span>Usar SSL IMAP</span>
            </label>
          </div>

          <div className="email-config-example">
            <strong>Formato de correo</strong>
            <code>Asunto: {emailConfig?.subjectPrefix || "[HABLA]"} nombre-del-proyecto</code>
            <code>Token: {emailConfig?.commandToken || "clave-secreta"}</code>
            <code>Proyecto: nombre-del-proyecto</code>
            <code>Modo: {emailConfig?.defaultRuntimeMode || "long-run"}</code>
            <code>Prompt: Construye el sistema completo...</code>
          </div>

          <div className="toolbar-inline">
            <button type="button" className="tool-button primary" onClick={saveEmailCommandConfig} disabled={isSavingEmailConfig}>
              {isSavingEmailConfig ? "Guardando..." : "Guardar setup de correo"}
            </button>
            <button type="button" className="tool-button" onClick={loadEmailCommandConfig}>Recargar</button>
            <span className="meta-pill">{emailCommandStatus?.imapConfigured ? "IMAP listo" : "faltan datos IMAP"}</span>
          </div>
        </div>
      </div>
    ) : null}
    {workspaceCleanOpen ? (
      <div className="workspace-clean-overlay" role="dialog" aria-label="Blanquear workspace HABLA">
        <div className="workspace-clean-modal">
          <div className="reviewer-header">
            <div>
              <h2>Blanquear Workspace</h2>
              <p>Esta operacion elimina proyectos, colas, historiales y mapas guardados para iniciar una prueba desde cero.</p>
            </div>
            <div className="reviewer-actions">
              <button
                type="button"
                className="tool-button"
                onClick={() => {
                  setWorkspaceCleanOpen(false);
                  setWorkspaceCleanConfirmation("");
                }}
              >
                Cancelar
              </button>
            </div>
          </div>

          {workspaceCleanStep === 1 ? (
            <div className="workspace-clean-warning">
              <strong>Primera validacion</strong>
              <p>El protocolo creara backup, registrara justificacion, escribira auditoria y creara POST-BLANQUEO-RECOVERY antes de eliminar proyectos.</p>
              <div className="toolbar-inline">
                <button type="button" className="tool-button danger" onClick={() => setWorkspaceCleanStep(2)}>
                  Si, continuar
                </button>
                <button type="button" className="tool-button" onClick={() => setWorkspaceCleanOpen(false)}>
                  No borrar
                </button>
              </div>
            </div>
          ) : (
            <div className="workspace-clean-warning">
              <strong>Segunda validacion</strong>
              <p>Escribe la palabra clave exacta. En modo medium o long-run tambien escribe si o confirmar para cumplir el safety gate humano.</p>
              <label className="editor-field small">
                <span>Palabra clave</span>
                <input
                  value={workspaceCleanKeyword}
                  onChange={(event) => setWorkspaceCleanKeyword(event.target.value)}
                  placeholder="HABLA"
                  autoFocus
                />
              </label>
              {workspaceCleanNeedsSafetyPhrase ? (
                <label className="editor-field small">
                  <span>Confirmacion safety gate</span>
                  <input
                    value={workspaceCleanConfirmation}
                    onChange={(event) => setWorkspaceCleanConfirmation(event.target.value)}
                    placeholder="si / confirmar"
                  />
                </label>
              ) : null}
              <div className="toolbar-inline">
                <button
                  type="button"
                  className="tool-button danger"
                  onClick={handleCleanWorkspace}
                  disabled={isCleaningWorkspace || !workspaceCleanReady}
                >
                  {isCleaningWorkspace ? "Eliminando..." : "Eliminar todo y blanquear"}
                </button>
                <button type="button" className="tool-button" onClick={() => setWorkspaceCleanStep(1)}>
                  Volver
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    ) : null}
    <LiveReviewerPanel
      session={session}
      status={reviewerStatus}
      events={reviewerEvents}
      isOpen={reviewerOpen}
      isMinimized={reviewerMinimized}
      isExpanded={reviewerExpanded}
      onOpen={() => {
        reviewerUserMinimizedRef.current = false;
        setReviewerOpen(true);
        setReviewerMinimized(false);
      }}
      onClose={() => {
        reviewerUserMinimizedRef.current = false;
        setReviewerOpen(false);
      }}
      onMinimize={() => {
        setReviewerMinimized((value) => {
          const nextValue = !value;
          reviewerUserMinimizedRef.current = nextValue;
          return nextValue;
        });
      }}
      onExpand={() => setReviewerExpanded((value) => !value)}
      onCopy={handleCopyReviewerLog}
      onExport={handleExportReviewerLog}
    />
    <div className="agent-burst-stack" aria-live="polite">
      {agentBursts.map((burst) => (
        <article key={burst.id} className={`agent-burst is-${burst.tone || "middle"}`}>
          <strong>{burst.source}</strong>
          <p>{burst.message}</p>
        </article>
      ))}
    </div>
    </>
  );
}
