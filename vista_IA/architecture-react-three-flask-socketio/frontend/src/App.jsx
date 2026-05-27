import { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";
import ArchitectureCanvas from "./components/ArchitectureCanvas.jsx";
import AlgorithmFlow from "./components/AlgorithmFlow.jsx";
import AppAgentPresenceLayer from "./components/AppAgentPresenceLayer.jsx";
import AppLintPanel from "./components/AppLintPanel.jsx";
import AppObserverPanel from "./components/AppObserverPanel.jsx";
import AppRuntimeWorkbenches from "./components/AppRuntimeWorkbenches.jsx";
import HarnessEngineeringStudio from "./components/HarnessEngineeringStudio.jsx";
import RuntimeDashboardSidebar from "./components/RuntimeDashboardSidebar.jsx";
import CyberLACEPanel from "./components/CyberLACEPanel.jsx";
import AppStatusbar from "./components/AppStatusbar.jsx";
import AppTopbar from "./components/AppTopbar.jsx";
import SectionDividerMenu from "./components/SectionDividerMenu.jsx";
import WelcomeAuthGate from "./components/WelcomeAuthGate.jsx";

import {
  AGENT_PRESENCE_ACTION_DELAYS_MS,
  AGENT_PRESENCE_STEPS,
  BASE_LAYER_ORDER,
  CLOSED_AGENT_VISUAL_OPS,
  EDGE_TYPES,
  EMPTY_EMBEDDED_SANDBOX,
  EMPTY_GRAPH,
  EMPTY_LINT_REPORT,
  FLOW_BUTTONS,
  HABLA_OBSERVER_LOGO_SRC,
  SEQUENCE_EDGE_PRIORITY,
  SEQUENCE_LAYER_PRIORITY,
  SOCKET_URL,
  applyDefaultLayout,
  buildLocalClearedGraph,
  buildSequencePlan,
  chooseRandom,
  collectWorkspaceProjectScenes,
  compareSequenceNodes,
  computeGraphMetadata,
  createNodeFromDraft,
  createProgramBundle,
  dedupeReferences,
  defaultColorForLayer,
  detectLanguageFromName,
  emitWithAck,
  filterGraphByScene,
  findAgentPresenceStepIndex,
  formatStatus,
  getFindingVisualSeverity,
  humanizeReverseError,
  isEditableShortcutTarget,
  parseWorkspaceEditorTarget,
  sanitizeGraphForVisualScope,
  severityWeight,
  slugify,
  titleizeLayer,
} from "./appUtils.js";

const HABLA_AUTH_TOKEN_STORAGE_KEY = "hablaAuthToken";

function readHablaAuthToken() {
  try {
    return window.localStorage.getItem(HABLA_AUTH_TOKEN_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

export default function App() {
  const socketRef = useRef(null);
  const autonomousModeRef = useRef(false);
  const harnessTrainingAutomationRef = useRef({ active: false, autoAcceptSafeAlternative: false });
  const cyberlaceAutoAcceptKeyRef = useRef("");
  const cyberlaceMathBoardRef = useRef(null);
  const observerPinnedRef = useRef(false);
  const agentPresenceModeTimerRef = useRef(null);
  const agentPresenceBurstTimerRef = useRef(null);
  const agentPresenceActionTimerRef = useRef(null);
  const [graph, setGraph] = useState(EMPTY_GRAPH);
  const [activeWorkspaceScene, setActiveWorkspaceScene] = useState("");
  const [viewAllWorkspaceScenes, setViewAllWorkspaceScenes] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState(null);
  const [selectedStepId, setSelectedStepId] = useState(null);
  const [sequencePlan, setSequencePlan] = useState(null);
  const [sequenceCursor, setSequenceCursor] = useState(0);
  const [connected, setConnected] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [analysisSessions, setAnalysisSessions] = useState([]);
  const [analysisTargetPath, setAnalysisTargetPath] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isAgentTranscribing, setIsAgentTranscribing] = useState(false);
  const [agentVisual, setAgentVisual] = useState(null);
  const [agentPresenceActive, setAgentPresenceActive] = useState(false);
  const [agentPresenceStep, setAgentPresenceStep] = useState(0);
  const [agentPresenceMode, setAgentPresenceMode] = useState("");
  const [autonomousMode, setAutonomousMode] = useState(false);
  const [observerStatus, setObserverStatus] = useState(null);
  const [observerTimeline, setObserverTimeline] = useState([]);
  const [observerBehaviorTree, setObserverBehaviorTree] = useState(null);
  const [observerActionStatus, setObserverActionStatus] = useState("");
  const [lintReport, setLintReport] = useState(EMPTY_LINT_REPORT);
  const [lintError, setLintError] = useState("");
  const [isLinting, setIsLinting] = useState(false);
  const [embeddedSandbox, setEmbeddedSandbox] = useState(EMPTY_EMBEDDED_SANDBOX);
  const [embeddedSandboxOpen, setEmbeddedSandboxOpen] = useState(false);
  const [embeddedSandboxBusy, setEmbeddedSandboxBusy] = useState(false);
  const [embeddedSandboxError, setEmbeddedSandboxError] = useState("");
  const [embeddedSandboxFrameKey, setEmbeddedSandboxFrameKey] = useState(0);
  const [cyberlaceBlockingAlert, setCyberlaceBlockingAlert] = useState(null);
  const [cyberlaceMathWriter, setCyberlaceMathWriter] = useState({ lineIndex: 0, charIndex: 0 });
  const [harnessTrainingAutomationState, setHarnessTrainingAutomationState] = useState({ active: false, autoAcceptSafeAlternative: false });
  const [runtimeDashboardWidth, setRuntimeDashboardWidth] = useState(318);
  const [agentProjects, setAgentProjects] = useState([]);
  const [agentProjectsLoading, setAgentProjectsLoading] = useState(false);
  const [projectActionStatus, setProjectActionStatus] = useState("");
  const [harnessStudioOpen, setHarnessStudioOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [editorJumpTarget, setEditorJumpTarget] = useState(null);
  const [editorExpanded, setEditorExpanded] = useState(false);
  const [mapTool, setMapTool] = useState("select");
  const [flowTool, setFlowTool] = useState("select");
  const [edgeType, setEdgeType] = useState("uses");
  const [newProgramName, setNewProgramName] = useState("analytics-hub");
  const [nodeDraft, setNodeDraft] = useState({
    name: "nuevo-bloque.js",
    layer: "frontend",
    layerLabel: "Frontend",
    color: "#60a5fa",
    codeLanguage: "javascript",
    code: "",
    description: "",
  });

  function focusWorkspaceScene(sceneKey) {
    setViewAllWorkspaceScenes(false);
    setActiveWorkspaceScene(String(sceneKey || "").trim());
  }

  function clearAgentPresenceTimers({ keepRepairMode = false } = {}) {
    if (agentPresenceBurstTimerRef.current) {
      window.clearTimeout(agentPresenceBurstTimerRef.current);
      agentPresenceBurstTimerRef.current = null;
    }
    if (agentPresenceActionTimerRef.current) {
      window.clearTimeout(agentPresenceActionTimerRef.current);
      agentPresenceActionTimerRef.current = null;
    }
    if (!keepRepairMode && agentPresenceModeTimerRef.current) {
      window.clearTimeout(agentPresenceModeTimerRef.current);
      agentPresenceModeTimerRef.current = null;
    }
  }

  function getCyberlaceBlockSource(payload) {
    if (payload?.securityBlock && typeof payload.securityBlock === "object") return payload.securityBlock;
    if (payload?.security_block && typeof payload.security_block === "object") return payload.security_block;
    if (payload?.decision && typeof payload.decision === "object") return payload.decision;
    const decisions = payload?.cyberlace?.decisions;
    if (Array.isArray(decisions) && decisions[0] && typeof decisions[0] === "object") return decisions[0];
    return payload || {};
  }

  function buildCyberlaceMathTrace(source, payload, action, paths, evidenceCount, safeAlternative) {
    const combined = [
      source?.message,
      source?.reason,
      source?.deniedAction,
      payload?.message,
      payload?.errorCode,
      payload?.op,
      ...(Array.isArray(source?.evidence) ? source.evidence.map((item) => `${item?.pattern || ""} ${item?.domain || ""} ${item?.type || ""}`) : []),
      ...(Array.isArray(paths) ? paths : []),
    ].filter(Boolean).join(" ").toLowerCase();
    const hasSecret = /secret|token|api[_-]?key|password|passwd|pwd|cvv|cvc|pin|tarjeta|card|bank|banco|cuenta|credential/.test(combined);
    const hasExfil = /exfil|upload|subir|send|enviar|correo|email|external|nube|cloud|transfer/.test(combined);
    const hasExternal = /ssh|aws|github|stripe|openai|codex|api|login|correo|email|imap|smtp/.test(combined);
    const hasLogin = /login|entrar|correo|email|password|inbox|mensajes|adjuntos/.test(combined);
    const hasObfuscation = /base64|hex|rot13|decode|decodifica|normaliza|ofusc/.test(combined);
    const uiRisk = safeAlternative ? 0 : 1;
    const zombieRisk = /zombie|running|null|pid/.test(combined) ? 1 : 0;
    const latencyRisk = /timeout|latency|lento|5s/.test(combined) ? 1 : 0;
    const riskVector = {
      s: hasSecret ? 1 : 0,
      e: hasExfil ? 1 : 0,
      x: hasExternal ? 1 : 0,
      l: hasLogin ? 1 : 0,
      o: hasObfuscation ? 1 : 0,
      u: uiRisk,
      z: zombieRisk,
      t: latencyRisk,
    };
    const weights = { s: 2.0, e: 2.0, x: 1.5, l: 1.7, o: 1.4, u: 0.8, z: 1.6, t: 0.9 };
    const computedRisk = Object.entries(riskVector).reduce((sum, [key, value]) => sum + value * weights[key], 0);
    const sourceRisk = Number(source?.riskScore ?? source?.risk_score ?? source?.risk ?? payload?.riskScore ?? NaN);
    const riskScore = Number.isFinite(sourceRisk) ? sourceRisk : Number(computedRisk.toFixed(2));
    const threshold = 1;
    const blockSet = "{BLOCK, QUARANTINE, HUMAN_REVIEW, REDACT}";
    const invariantViolations = [];
    if (riskScore >= threshold && !["BLOCK", "QUARANTINE", "HUMAN_REVIEW", "REDACT"].includes(action)) invariantViolations.push("I1_FAIL_CLOSED");
    if (hasExfil && !["BLOCK", "QUARANTINE", "HUMAN_REVIEW", "REDACT"].includes(action)) invariantViolations.push("I2_NO_EXFILTRATION");
    if (!safeAlternative) invariantViolations.push("I4_SAFE_GUIDANCE_VISIBILITY");
    const loss = Number((Math.max(0, riskScore - threshold) + invariantViolations.length * 0.7 + (safeAlternative ? 0 : 0.8)).toFixed(2));
    const repairOperator = invariantViolations.includes("I1_FAIL_CLOSED")
      ? "R1_PATCH_GUARD"
      : invariantViolations.includes("I4_SAFE_GUIDANCE_VISIBILITY")
        ? "R2_PATCH_UI_SAFE_GUIDANCE"
        : "R0_BLOCK_AND_REWRITE_SAFE";
    const failureNode = invariantViolations.includes("I1_FAIL_CLOSED")
      ? "cyberlace.document_guard"
      : invariantViolations.includes("I4_SAFE_GUIDANCE_VISIBILITY")
        ? "frontend.cyberlace_safe_guidance"
        : "policy.safe_rewrite";
    const vectorText = `[${riskVector.s}, ${riskVector.e}, ${riskVector.x}, ${riskVector.l}, ${riskVector.o}, ${riskVector.u}, ${riskVector.z}, ${riskVector.t}]`;
    const safeEquation = safeAlternative?.suggestedRequirement
      ? "rewrite(P) = P_safe; P_sensitive ∩ P_safe = ∅"
      : "rewrite(P) -> synthetic_data + redaction + audit";
    return {
      riskVector,
      riskScore,
      threshold,
      invariantViolations,
      loss,
      repairOperator,
      failureNode,
      rows: [
        { label: "Estado", equation: "S_t = (P, R, C, U, E, M)" },
        { label: "Vector", equation: `r = [s,e,x,l,o,u,z,t] = ${vectorText}` },
        { label: "Riesgo", equation: `Risk(P) = w · r = ${riskScore} >= θ=${threshold}` },
        { label: "Invariante I1", equation: `Risk(P) >= θ => action(C) ∈ ${blockSet}; action=${action}` },
        { label: "No exfiltracion", equation: "secret(x) => output(x) = REDACTED" },
        { label: "Perdida", equation: `L = αL_sec + βL_run + γL_ui + δL_evidence = ${loss}` },
        { label: "Solucion", equation: `R* = argmin_R L(apply(R,S_t)) + Cost(R) = ${repairOperator}` },
        { label: "Ruta segura", equation: safeEquation },
      ],
    };
  }

  function buildFallbackCyberlaceGuidance(source, payload) {
    const combined = [
      source?.message,
      source?.reason,
      source?.deniedAction,
      payload?.message,
      payload?.errorCode,
      payload?.op,
      ...(Array.isArray(source?.evidence) ? source.evidence.map((item) => `${item?.pattern || ""} ${item?.domain || ""} ${item?.type || ""}`) : []),
    ].filter(Boolean).join(" ").toLowerCase();
    const isFinancial = /pago|pagos|payment|tarjeta|card|cvv|cvc|pin|banco|bank|cuenta|transfer/.test(combined);
    if (isFinancial) {
      return {
        deniedAction: "Validar, copiar, almacenar, transportar o preparar pagos/transferencias usando PAN, CVV, PIN, cuentas bancarias, passwords o tokens sensibles.",
        safeAlternative: {
          title: "Alternativa segura permitida",
          summary: "HABLA no procesa CVV, PIN, passwords bancarias ni transferencias con datos sensibles. Si puede ayudar a disenar un flujo seguro con tokenizacion, checkout hospedado, recibos, ultimos 4 digitos, controles de acceso y datos sinteticos.",
          allowedActions: [
            "Disenar arquitectura PCI-style sin que la app vea ni almacene CVV/PIN.",
            "Usar tokenizacion o checkout hospedado por el proveedor de pagos.",
            "Mostrar solo recibos, IDs de transaccion y ultimos 4 digitos.",
            "Usar datos sinteticos para QA y pruebas automatizadas.",
            "Definir auditoria, permisos y monitoreo sin exponer secretos financieros.",
          ],
          suggestedRequirement: "Disenar una arquitectura segura de pagos con tokenizacion, checkout hospedado, recibos, auditoria, datos sinteticos y sin procesar ni transportar PAN/CVV/PIN/passwords/tokens sensibles.",
        },
        safeNextSteps: [
          "Reformular la tarea hacia arquitectura segura de pagos.",
          "Eliminar validacion directa de CVV/PIN/passwords/cuentas del flujo de la app.",
          "Trabajar solo con tokens del proveedor, recibos, ultimos 4 digitos y datos sinteticos.",
        ],
      };
    }
    return {
      deniedAction: "Procesar, exponer, transportar o ejecutar acciones con informacion sensible detectada por CyberLACE.",
      safeAlternative: {
        title: "Alternativa segura permitida",
        summary: "HABLA bloqueo el camino inseguro, pero puede ayudar a redisenar el flujo para trabajar con datos sinteticos, evidencia redactada, controles de acceso y procedimientos auditables.",
        allowedActions: [
          "Redisenar el flujo para no leer ni transportar secretos.",
          "Usar datos sinteticos o placeholders no sensibles.",
          "Crear validaciones de seguridad y auditoria sin exponer valores reales.",
        ],
        suggestedRequirement: "Redisenar esta tarea con datos sinteticos, evidencia redactada, controles de acceso y sin procesar informacion sensible local.",
      },
      safeNextSteps: [
        "Quitar del alcance cualquier secreto o dato sensible.",
        "Reformular con datos sinteticos.",
        "Documentar el bloqueo y la alternativa segura.",
      ],
    };
  }

  function dispatchCyberlaceSafeAlternative(alert, { auto = false } = {}) {
    const safeAlternative = alert?.safeAlternative;
    const suggestedRequirement = String(safeAlternative?.suggestedRequirement || "").trim();
    if (!suggestedRequirement) return false;
    window.dispatchEvent(new CustomEvent("habla:safe-alternative-accepted", {
      detail: {
        requirement: suggestedRequirement,
        projectSlug: alert.projectSlug,
        sourceSessionId: alert.sessionId,
        title: safeAlternative.title || "Alternativa segura CyberLACE",
        autoAccepted: Boolean(auto),
        source: auto ? "harness-autonomous-training" : "human",
      },
    }));
    return true;
  }

  function showCyberlaceBlockingAlert(payload) {
    const source = getCyberlaceBlockSource(payload);
    const fallback = buildFallbackCyberlaceGuidance(source, payload);
    const action = String(source.runtimeAction || source.action || payload?.runtimeAction || payload?.action || "QUARANTINE").toUpperCase();
    const paths = Array.isArray(source.blockedPaths) ? source.blockedPaths.filter(Boolean).slice(0, 6) : [];
    const evidenceCount = Array.isArray(source.evidence) ? source.evidence.length : 0;
    const sourceSafeAlternative = source.safeAlternative && typeof source.safeAlternative === "object" ? source.safeAlternative : null;
    const sourceSafeNextSteps = Array.isArray(source.safeNextSteps) ? source.safeNextSteps.filter(Boolean).slice(0, 5) : [];
    const projectSlug = payload?.projectSlug || source.projectSlug || "";
    const sessionId = payload?.sessionId || source.sessionId || "";
    setCyberlaceBlockingAlert((current) => {
      const sameBlock = current && (
        (sessionId && current.sessionId === sessionId) ||
        (projectSlug && current.projectSlug === projectSlug)
      );
      const safeAlternative = sourceSafeAlternative || (sameBlock ? current.safeAlternative : null) || fallback.safeAlternative;
      const safeNextSteps = sourceSafeNextSteps.length ? sourceSafeNextSteps : (sameBlock && current.safeNextSteps?.length ? current.safeNextSteps : fallback.safeNextSteps);
      const mathTrace = buildCyberlaceMathTrace(source, payload, action, paths, evidenceCount, safeAlternative);
      const nextAlert = {
        action,
        projectSlug,
        sessionId,
        message: payload?.message || source.message || "CyberLACE bloqueo esta accion antes de ejecutar el runtime.",
        reason: source.reason || "Se detectaron patrones compatibles con informacion sensible en documentos locales.",
        deniedAction: source.deniedAction || (sameBlock ? current.deniedAction : "") || fallback.deniedAction,
        safeAlternative,
        safeNextSteps,
        mathTrace,
        paths,
        evidenceCount,
        timestamp: new Date().toISOString(),
      };
      return nextAlert;
    });
  }

  function acceptCyberlaceSafeAlternative() {
    const automation = harnessTrainingAutomationRef.current || {};
    const auto = Boolean(automation.active && automation.autoAcceptSafeAlternative);
    if (!dispatchCyberlaceSafeAlternative(cyberlaceBlockingAlert, { auto })) return;
    setCyberlaceBlockingAlert(null);
    if (!auto) {
      window.setTimeout(() => {
        document.getElementById("section-agents")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    }
  }

  function syncObserverStatus(nextObserver) {
    if (!nextObserver || typeof nextObserver !== "object") return;
    setObserverStatus(nextObserver);
    observerPinnedRef.current = Boolean(nextObserver.humanPinned);
    if (nextObserver.enabled && nextObserver.humanPinned) {
      autonomousModeRef.current = true;
      setAutonomousMode(true);
    } else if (nextObserver.enabled === false && !nextObserver.humanPinned) {
      autonomousModeRef.current = false;
      setAutonomousMode(false);
    }
    if (Array.isArray(nextObserver.timeline)) {
      setObserverTimeline(nextObserver.timeline.slice(-24).reverse());
    }
    if (nextObserver.behaviorTree) {
      setObserverBehaviorTree(nextObserver.behaviorTree);
    }
  }

  async function loadObserverStatus() {
    try {
      const response = await fetch(`${SOCKET_URL}/api/observer/status`);
      const payload = await response.json();
      if (payload?.observer) syncObserverStatus(payload.observer);
    } catch (error) {
      setObserverActionStatus(error?.message || "No fue posible cargar Observer Plane.");
    }
  }

  async function loadAgentProjects({ silent = false } = {}) {
    if (!silent) setAgentProjectsLoading(true);
    try {
      const response = await fetch(`${SOCKET_URL}/api/agent/projects`);
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "No fue posible cargar proyectos.");
      }
      setAgentProjects(Array.isArray(payload?.projects) ? payload.projects : []);
      if (!silent) setProjectActionStatus("");
      return payload?.projects || [];
    } catch (error) {
      setProjectActionStatus(error?.message || "No fue posible cargar proyectos.");
      return [];
    } finally {
      if (!silent) setAgentProjectsLoading(false);
    }
  }

  async function createSidebarProject() {
    const name = newProjectName.trim();
    if (!name) {
      setProjectActionStatus("Escribe un nombre de proyecto.");
      return;
    }
    setAgentProjectsLoading(true);
    setProjectActionStatus("Creando proyecto...");
    try {
      const response = await fetch(`${SOCKET_URL}/api/agent/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, ensureUnique: true, bootstrapProject: true }),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "No fue posible crear el proyecto.");
      }
      setAgentProjects(Array.isArray(payload?.projects) ? payload.projects : []);
      setNewProjectName("");
      if (payload?.project?.slug) {
        focusWorkspaceScene(payload.project.slug);
        socketRef.current?.emit("architecture:request");
      }
      setProjectActionStatus(`Proyecto creado: ${payload?.project?.slug || name}`);
    } catch (error) {
      setProjectActionStatus(error?.message || "No fue posible crear el proyecto.");
    } finally {
      setAgentProjectsLoading(false);
    }
  }

  async function archiveSidebarProject(projectSlug) {
    const slug = String(projectSlug || "").trim();
    if (!slug) return;
    if (slug === "sesion-20260524210420" || slug === "sesion-20260524233805") {
      setProjectActionStatus("Proyecto protegido: no se puede archivar desde la UI.");
      return;
    }
    const accepted = window.confirm(`Archivar proyecto ${slug}? Se movera a backup, no se borrara directo.`);
    if (!accepted) return;
    setAgentProjectsLoading(true);
    setProjectActionStatus(`Archivando ${slug}...`);
    try {
      const response = await fetch(`${SOCKET_URL}/api/agent/projects/${encodeURIComponent(slug)}/archive`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "No fue posible archivar el proyecto.");
      }
      setAgentProjects(Array.isArray(payload?.projects) ? payload.projects : []);
      if (effectiveWorkspaceScene === slug) {
        setActiveWorkspaceScene("");
      }
      socketRef.current?.emit("architecture:request");
      setProjectActionStatus(`Proyecto archivado con backup: ${payload?.backupRelativePath || slug}`);
    } catch (error) {
      setProjectActionStatus(error?.message || "No fue posible archivar el proyecto.");
    } finally {
      setAgentProjectsLoading(false);
    }
  }

  async function deleteSidebarProject(projectSlug, password) {
    const slug = String(projectSlug || "").trim();
    if (!slug) throw new Error("Proyecto invalido.");
    if (slug === "sesion-20260524210420" || slug === "sesion-20260524233805") {
      throw new Error("Proyecto protegido: no se puede eliminar.");
    }
    setAgentProjectsLoading(true);
    setProjectActionStatus(`Eliminando ${slug}...`);
    try {
      const token = readHablaAuthToken();
      const response = await fetch(`${SOCKET_URL}/api/agent/projects/${encodeURIComponent(slug)}/delete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ password, confirmDelete: true, projectSlug: slug }),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "No fue posible eliminar el proyecto.");
      }
      setAgentProjects(Array.isArray(payload?.projects) ? payload.projects : []);
      if (effectiveWorkspaceScene === slug) {
        setActiveWorkspaceScene("");
      }
      socketRef.current?.emit("architecture:request");
      setProjectActionStatus(`Proyecto eliminado. Backup: ${payload?.backupRelativePath || slug}`);
      return true;
    } catch (error) {
      setProjectActionStatus(error?.message || "No fue posible eliminar el proyecto.");
      throw error;
    } finally {
      setAgentProjectsLoading(false);
    }
  }

  function openHarnessEngineeringStudio() {
    setHarnessStudioOpen(true);
    setProjectActionStatus("Harness Engineering Studio abierto.");
    document.getElementById("section-runtime")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function saveObserverBehaviorTree(nextTree = observerBehaviorTree) {
    if (!nextTree) return;
    setObserverActionStatus("Guardando behavior tree...");
    try {
      const response = await fetch(`${SOCKET_URL}/api/observer/behavior`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ behaviorTree: nextTree }),
      });
      const payload = await response.json();
      if (payload?.observer) syncObserverStatus(payload.observer);
      setObserverActionStatus(payload?.ok === false ? "No se pudo guardar behavior tree." : "Behavior tree actualizado.");
    } catch (error) {
      setObserverActionStatus(error?.message || "No se pudo guardar behavior tree.");
    }
  }

  async function runObserverAction(action, payload = {}) {
    setObserverActionStatus(`Observer ejecutando ${action}...`);
    try {
      const response = await fetch(`${SOCKET_URL}/api/observer/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, payload }),
      });
      const result = await response.json();
      if (result?.observer) syncObserverStatus(result.observer);
      if (result?.report) setLintReport(result.report);
      if (result?.graph) setGraph(applyDefaultLayout(result.graph));
      setObserverActionStatus(result?.ok ? `Observer completo: ${action}` : result?.error || `Observer fallo: ${action}`);
    } catch (error) {
      setObserverActionStatus(error?.message || `Observer fallo: ${action}`);
    }
  }

  async function observeNow() {
    setObserverActionStatus("Observer tomando decision...");
    try {
      const response = await fetch(`${SOCKET_URL}/api/observer/observe-once`, { method: "POST" });
      const payload = await response.json();
      if (payload?.observer) syncObserverStatus(payload.observer);
      if (payload?.event) {
        setObserverTimeline((current) => [payload.event, ...current].slice(0, 24));
        applyObserverAction(payload.event);
      }
      setObserverActionStatus("Observer actualizo decision.");
    } catch (error) {
      setObserverActionStatus(error?.message || "Observer no pudo decidir.");
    }
  }

  function updateObserverRule(ruleId, enabled) {
    if (!observerBehaviorTree?.rules) return;
    const nextTree = {
      ...observerBehaviorTree,
      rules: observerBehaviorTree.rules.map((rule) => (
        rule.id === ruleId ? { ...rule, enabled } : rule
      )),
    };
    setObserverBehaviorTree(nextTree);
    saveObserverBehaviorTree(nextTree);
  }

  function toggleAutonomousMode(source = "button") {
    setAutonomousMode((current) => {
      const next = !current;
      const sourceLabel = source === "keyboard" ? "tecla A" : "boton Modo autonomo";
      autonomousModeRef.current = next;
      observerPinnedRef.current = next;
      socketRef.current?.emit("observer:enabled", {
        enabled: next,
        source: "human",
        allowIdle: true,
        reason: next ? `Activado con ${sourceLabel}.` : `Desactivado con ${sourceLabel}.`,
      });
      setObserverActionStatus(`Modo autonomo ${next ? "activado" : "desactivado"} con ${sourceLabel}.`);
      if (!next) {
        clearAgentPresenceTimers();
        setAgentPresenceActive(false);
        setAgentPresenceMode("");
      }
      return next;
    });
  }

  useEffect(() => {
    function handleAutonomousModeShortcut(event) {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
      if (String(event.key || "").toLowerCase() !== "a") return;
      if (isEditableShortcutTarget(event.target)) return;
      event.preventDefault();
      toggleAutonomousMode("keyboard");
    }

    window.addEventListener("keydown", handleAutonomousModeShortcut);
    return () => window.removeEventListener("keydown", handleAutonomousModeShortcut);
  }, []);

  function shutdownAutonomousObserver(reason = "Runtime cerrado: Observer Plane apagado.") {
    if (observerPinnedRef.current || autonomousModeRef.current) {
      setObserverActionStatus(`${reason} Modo autonomo humano sigue activo para inspeccion real.`);
      return false;
    }
    autonomousModeRef.current = false;
    observerPinnedRef.current = false;
    setAutonomousMode(false);
    clearAgentPresenceTimers();
    setAgentPresenceActive(false);
    setAgentPresenceMode("");
    setObserverActionStatus(reason);
    socketRef.current?.emit("observer:enabled", { enabled: false, reason });
    return true;
  }

  function applyObserverAction(payload = {}) {
    if (!autonomousModeRef.current) return;
    const uiAction = payload.uiAction && typeof payload.uiAction === "object" ? payload.uiAction : {};
    const stepIndex = findAgentPresenceStepIndex(uiAction.type || payload.action, uiAction.targetId);
    const targetId = uiAction.targetId || AGENT_PRESENCE_STEPS[stepIndex]?.targetId || "code-workbench";
    clearAgentPresenceTimers({ keepRepairMode: true });
    setAgentPresenceStep(stepIndex);
    setAgentPresenceMode("Observer Plane real");
    setAgentPresenceActive(true);
    if (payload.focusNodeId) {
      setSelectedId(payload.focusNodeId);
      setSelectedEdgeId(null);
    }
    if (payload.stepId) {
      setSelectedStepId(payload.stepId);
    }
    if (payload.projectSlug) {
      focusWorkspaceScene(payload.projectSlug);
    }
    window.setTimeout(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 30);
    agentPresenceModeTimerRef.current = window.setTimeout(() => {
      setAgentPresenceActive(false);
      setAgentPresenceMode("");
      agentPresenceModeTimerRef.current = null;
    }, 18000);
  }

  useEffect(() => {
    autonomousModeRef.current = autonomousMode;
  }, [autonomousMode]);

  useEffect(() => {
    function handleCyberlaceBlockedEvent(event) {
      showCyberlaceBlockingAlert(event?.detail || {});
    }

    function handleHarnessTrainingAutomation(event) {
      const detail = event?.detail || {};
      const automationState = {
        active: Boolean(detail.active),
        autoAcceptSafeAlternative: Boolean(detail.autoAcceptSafeAlternative),
        runId: detail.runId || "",
        campaignId: detail.campaignId || "",
      };
      harnessTrainingAutomationRef.current = automationState;
      setHarnessTrainingAutomationState(automationState);
      if (detail.active && detail.autoAcceptSafeAlternative) {
        setProjectActionStatus("Harness Autopilot activo: alternativas seguras se aceptan automaticamente durante la campana.");
      } else if (detail.active === false) {
        setProjectActionStatus("Harness Autopilot finalizado: autoaceptacion segura desactivada.");
      }
    }

    window.addEventListener("habla:cyberlace-blocked", handleCyberlaceBlockedEvent);
    window.addEventListener("habla:harness-training-automation", handleHarnessTrainingAutomation);
    return () => {
      window.removeEventListener("habla:cyberlace-blocked", handleCyberlaceBlockedEvent);
      window.removeEventListener("habla:harness-training-automation", handleHarnessTrainingAutomation);
    };
  }, []);

  useEffect(() => {
    const automation = harnessTrainingAutomationState || {};
    if (!cyberlaceBlockingAlert || !automation.active || !automation.autoAcceptSafeAlternative) return undefined;
    if (!cyberlaceBlockingAlert.safeAlternative?.suggestedRequirement) return undefined;
    const acceptKey = [
      cyberlaceBlockingAlert.sessionId || "session",
      cyberlaceBlockingAlert.projectSlug || "project",
      cyberlaceBlockingAlert.timestamp || "time",
    ].join("|");
    if (cyberlaceAutoAcceptKeyRef.current === acceptKey) return undefined;
    cyberlaceAutoAcceptKeyRef.current = acceptKey;
    const timer = window.setTimeout(() => {
      const button = document.querySelector('[data-cyberlace-safe-accept="primary"]');
      if (button instanceof HTMLButtonElement) {
        button.dataset.autoClicking = "true";
        button.click();
        setProjectActionStatus("Harness Autopilot oprimio automaticamente Aceptar alternativa segura; la accion peligrosa sigue bloqueada.");
        return;
      }
      const accepted = dispatchCyberlaceSafeAlternative(cyberlaceBlockingAlert, { auto: true });
      if (accepted) {
        setCyberlaceBlockingAlert(null);
        setProjectActionStatus("Harness Autopilot acepto automaticamente la alternativa segura; la accion peligrosa sigue bloqueada.");
      }
    }, 1400);
    return () => window.clearTimeout(timer);
  }, [cyberlaceBlockingAlert, harnessTrainingAutomationState]);

  useEffect(() => {
    const socket = io(SOCKET_URL, {
      transports: ["polling"],
      upgrade: false,
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      setConnected(true);
      socket.emit("architecture:request");
      socket.emit("reverse:request");
      loadObserverStatus();
      loadAgentProjects({ silent: true });
    });

    socket.on("disconnect", () => {
      setConnected(false);
    });

    socket.on("architecture:update", (nextGraph) => {
      const hydrated = applyDefaultLayout(nextGraph || EMPTY_GRAPH);
      setGraph({
        ...hydrated,
        metadata: computeGraphMetadata(hydrated),
      });
      const firstNode = hydrated.nodes[0];
      setSelectedId((current) => current && hydrated.nodes.some((node) => node.id === current) ? current : firstNode?.id || null);
      setDirty(false);
    });

    socket.on("agent:visual", (payload) => {
      if (!payload) return;
      const visualOp = String(payload.op || "").toLowerCase();
      if (
        visualOp === "cyberlace_document_blocked" ||
        (visualOp === "session_blocked" && String(payload.errorCode || "").includes("cyberlace"))
      ) {
        showCyberlaceBlockingAlert(payload);
      }
      setAgentVisual(payload);
      if (payload.projectSlug) {
        focusWorkspaceScene(payload.projectSlug);
      }
      if (visualOp === "sandbox_started" || visualOp === "sandbox_stopped") {
        loadEmbeddedSandbox(payload.projectSlug || effectiveWorkspaceScene, { silent: true }).then((nextSandbox) => {
          if (visualOp === "sandbox_started" && nextSandbox?.running && nextSandbox?.embedUrl) {
            setEmbeddedSandboxOpen(true);
            setEmbeddedSandboxFrameKey((current) => current + 1);
          }
          if (visualOp === "sandbox_stopped") {
            setEmbeddedSandboxOpen(false);
          }
        });
      }
      if (visualOp === "observer_action") {
        return;
      }
      if (CLOSED_AGENT_VISUAL_OPS.has(visualOp)) {
        const stoppedObserver = shutdownAutonomousObserver("Runtime cerrado: observer y movimiento autonomo detenidos.");
        if (stoppedObserver) {
          setSelectedId(null);
          setSelectedEdgeId(null);
          setSelectedStepId(null);
          setMapTool("select");
          setFlowTool("select");
        }
        return;
      }
      if (payload.focusNodeId) {
        setSelectedId(payload.focusNodeId);
        setSelectedEdgeId(null);
      }
      if (payload.stepId) {
        setSelectedStepId(payload.stepId);
      }
    });

    socket.on("agent:cyberlace", (payload) => {
      const action = String(payload?.action || payload?.runtimeAction || "").toUpperCase();
      if (["BLOCK", "QUARANTINE", "HUMAN_REVIEW"].includes(action)) {
        showCyberlaceBlockingAlert(payload);
      }
    });

    socket.on("agent:projects", (payload) => {
      if (Array.isArray(payload?.projects)) {
        setAgentProjects(payload.projects);
      }
    });

    socket.on("agent:observer", (payload) => {
      if (!payload) return;
      if (payload.observer) {
        syncObserverStatus(payload.observer);
      }
      if (payload.op === "observer_status") {
        setObserverStatus((current) => ({ ...(current || {}), enabled: payload.enabled, state: payload.state }));
        if (payload.enabled === false && !payload.observer?.humanPinned) {
          clearAgentPresenceTimers();
          setAgentPresenceActive(false);
          setAgentPresenceMode("");
          autonomousModeRef.current = false;
          observerPinnedRef.current = false;
          setAutonomousMode(false);
        }
      }
      if (payload.op === "observer_auto_disabled") {
        if (!payload.observer?.humanPinned) {
          clearAgentPresenceTimers();
          setAgentPresenceActive(false);
          setAgentPresenceMode("");
          autonomousModeRef.current = false;
          observerPinnedRef.current = false;
          setAutonomousMode(false);
        }
        setObserverActionStatus(payload.message || "Observer Plane apagado por cierre del runtime.");
      }
      if (payload.op === "observer_auto_disable_skipped") {
        autonomousModeRef.current = true;
        observerPinnedRef.current = true;
        setAutonomousMode(true);
        setObserverActionStatus(payload.message || "Observer Plane sigue activo por activacion humana.");
      }
      if (payload.op === "observer_behavior_updated" && payload.behaviorTree) {
        setObserverBehaviorTree(payload.behaviorTree);
      }
      if (payload.op === "observer_action") {
        setObserverTimeline((current) => [payload, ...current].slice(0, 24));
        setObserverStatus((current) => ({
          ...(current || {}),
          state: payload.state,
          memory: payload.memorySummary || current?.memory,
        }));
        applyObserverAction(payload);
      }
    });

    socket.on("reverse:sessions", (payload) => {
      setAnalysisSessions(payload?.sessions || []);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  const workspaceSceneOptions = useMemo(() => collectWorkspaceProjectScenes(graph), [graph]);
  const defaultWorkspaceScene = workspaceSceneOptions[0]?.key || "";
  const effectiveWorkspaceScene = viewAllWorkspaceScenes ? "" : (activeWorkspaceScene || defaultWorkspaceScene);

  const visibleGraph = useMemo(
    () => filterGraphByScene(graph, effectiveWorkspaceScene),
    [graph, effectiveWorkspaceScene]
  );
  const agentPresence = AGENT_PRESENCE_STEPS[agentPresenceStep % AGENT_PRESENCE_STEPS.length];

  useEffect(() => {
    const selectedNode = visibleGraph.nodes.find((node) => node.id === selectedId);
    if (!selectedNode?.algorithm?.steps?.length) {
      setSelectedStepId(null);
      return;
    }
    setSelectedStepId((current) => selectedNode.algorithm.steps.some((step) => step.id === current) ? current : selectedNode.algorithm.steps[0].id);
  }, [visibleGraph.nodes, selectedId]);

  useEffect(() => {
    if (!visibleGraph.nodes.length) {
      setSelectedId(null);
      setSelectedEdgeId(null);
      setSelectedStepId(null);
      setSequencePlan(null);
      setSequenceCursor(0);
      return;
    }

    if (!selectedId || !visibleGraph.nodes.some((node) => node.id === selectedId)) {
      setSelectedId(visibleGraph.nodes[0].id);
      setSelectedEdgeId(null);
      setSelectedStepId(null);
    }
  }, [selectedId, visibleGraph.nodes]);

  useEffect(() => {
    if (!connected || !visibleGraph.nodes.length || !autonomousMode) {
      clearAgentPresenceTimers();
      setAgentPresenceActive(false);
    }
    return undefined;
  }, [autonomousMode, connected, visibleGraph.nodes.length]);

  useEffect(() => {
    return () => {
      clearAgentPresenceTimers();
    };
  }, []);

  useEffect(() => {
    if (!agentPresenceActive || agentPresenceMode === "Observer Plane real") return undefined;
    let cancelled = false;
    const advanceAction = () => {
      if (cancelled) return;
      setAgentPresenceStep((current) => {
        if (AGENT_PRESENCE_STEPS.length <= 1) return current;
        const jump = 1 + Math.floor(Math.random() * (AGENT_PRESENCE_STEPS.length - 1));
        return (current + jump) % AGENT_PRESENCE_STEPS.length;
      });
      agentPresenceActionTimerRef.current = window.setTimeout(
        advanceAction,
        chooseRandom(AGENT_PRESENCE_ACTION_DELAYS_MS, 2600)
      );
    };
    agentPresenceActionTimerRef.current = window.setTimeout(advanceAction, chooseRandom([800, 1400, 2100], 1200));
    return () => {
      cancelled = true;
      if (agentPresenceActionTimerRef.current) {
        window.clearTimeout(agentPresenceActionTimerRef.current);
        agentPresenceActionTimerRef.current = null;
      }
    };
  }, [agentPresenceActive, agentPresenceMode]);

  useEffect(() => {
    if (!agentPresenceActive || !visibleGraph.nodes.length) return;
    const nextNode = visibleGraph.nodes[agentPresenceStep % visibleGraph.nodes.length];
    if (nextNode) {
      setSelectedId(nextNode.id);
      setSelectedEdgeId(null);
      if (nextNode.algorithm?.steps?.length) {
        setSelectedStepId(nextNode.algorithm.steps[agentPresenceStep % nextNode.algorithm.steps.length].id);
      }
    }
    const target = document.getElementById(agentPresence.targetId);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [agentPresenceActive, agentPresenceStep, agentPresence.targetId, visibleGraph.nodes]);

  function triggerRepairPresence(target = {}) {
    if (!autonomousMode) return;
    clearAgentPresenceTimers();
    if (agentPresenceModeTimerRef.current) {
      window.clearTimeout(agentPresenceModeTimerRef.current);
      agentPresenceModeTimerRef.current = null;
    }
    const line = Math.max(1, Number(target.line || 1) || 1);
    const path = target.path || "archivo seleccionado";
    const detail = `escaneando ${path}:${line} antes de reparar`;
    setAgentPresenceStep(0);
    setAgentPresenceMode("Escaneo pre reparacion");
    setAgentPresenceActive(true);
    setAgentVisual({
      op: "repair_pre_scan",
      phase: "escaneo-pre-reparacion",
      message: detail,
      status: "active",
    });
    window.setTimeout(() => {
      document.getElementById("code-workbench")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 20);
    agentPresenceModeTimerRef.current = window.setTimeout(() => {
      setAgentPresenceMode("");
      agentPresenceModeTimerRef.current = null;
    }, 22000);
    agentPresenceBurstTimerRef.current = window.setTimeout(() => {
      setAgentPresenceActive(false);
      setAgentPresenceMode("");
      agentPresenceBurstTimerRef.current = null;
    }, 26000);
  }

  const orderedLayers = useMemo(() => {
    const unique = [...new Set(visibleGraph.nodes.map((node) => node.layer))];
    const known = BASE_LAYER_ORDER.filter((layer) => unique.includes(layer));
    const custom = unique.filter((layer) => !known.includes(layer)).sort();
    return [...known, ...custom];
  }, [visibleGraph.nodes]);

  const selectedNode = useMemo(
    () => visibleGraph.nodes.find((node) => node.id === selectedId) || null,
    [visibleGraph.nodes, selectedId]
  );

  const selectedEdge = useMemo(
    () => visibleGraph.edges.find((edge) => edge.id === selectedEdgeId) || null,
    [visibleGraph.edges, selectedEdgeId]
  );

  const selectedStep = useMemo(
    () => selectedNode?.algorithm?.steps?.find((step) => step.id === selectedStepId) || null,
    [selectedNode, selectedStepId]
  );
  const isReadOnlyNode = Boolean(selectedNode?.readOnly);

  const isSequenceMode = Boolean(sequencePlan?.nodeIds?.length);
  const activeSequenceNodeId = isSequenceMode ? sequencePlan.nodeIds[Math.min(sequenceCursor, sequencePlan.nodeIds.length - 1)] : null;
  const sequenceBlocks = useMemo(() => {
    if (!sequencePlan?.nodeIds?.length) return [];

    const nodeMap = new Map(visibleGraph.nodes.map((node) => [node.id, node]));
    return sequencePlan.nodeIds
      .slice(0, sequenceCursor + 1)
      .map((nodeId) => {
        const node = nodeMap.get(nodeId);
        if (!node) return null;
        return {
          nodeId: node.id,
          nodeName: node.name,
          nodePath: node.path,
          layer: node.layer,
          layerLabel: node.layerLabel,
          color: node.color,
          algorithm: node.algorithm,
        };
      })
      .filter(Boolean);
  }, [visibleGraph.nodes, sequenceCursor, sequencePlan]);

  const sequenceTransitions = useMemo(
    () => sequencePlan?.links?.slice(0, Math.max(sequenceCursor, 0)) || [],
    [sequenceCursor, sequencePlan]
  );

  const lintScopeScene = selectedNode?.workspaceScene || effectiveWorkspaceScene || "";
  const lintScopeLabel = selectedNode?.workspaceSceneLabel || lintReport.scope?.label || "Mapa completo";

  const nodesByLayer = useMemo(() => {
    const grouped = Object.fromEntries(orderedLayers.map((layer) => [layer, []]));
    for (const node of visibleGraph.nodes) {
      if (!grouped[node.layer]) grouped[node.layer] = [];
      grouped[node.layer].push(node);
    }
    return grouped;
  }, [visibleGraph.nodes, orderedLayers]);

  const lintIssueMaps = useMemo(() => {
    const nodeIssuesById = {};
    const stepIssuesByNodeId = {};

    for (const finding of lintReport.findings || []) {
      const nodeId = String(finding.nodeId || "");
      const visualSeverity = getFindingVisualSeverity(finding);
      if (nodeId) {
        if (!nodeIssuesById[nodeId]) {
          nodeIssuesById[nodeId] = { count: 0, severity: "info", findings: [] };
        }
        nodeIssuesById[nodeId].count += 1;
        nodeIssuesById[nodeId].findings.push(finding);
        if (severityWeight(visualSeverity) > severityWeight(nodeIssuesById[nodeId].severity)) {
          nodeIssuesById[nodeId].severity = visualSeverity;
        }
      }

      const stepId = String(finding.stepId || "");
      if (nodeId && stepId) {
        if (!stepIssuesByNodeId[nodeId]) {
          stepIssuesByNodeId[nodeId] = {};
        }
        if (!stepIssuesByNodeId[nodeId][stepId]) {
          stepIssuesByNodeId[nodeId][stepId] = { count: 0, severity: "info", findings: [] };
        }
        stepIssuesByNodeId[nodeId][stepId].count += 1;
        stepIssuesByNodeId[nodeId][stepId].findings.push(finding);
        if (severityWeight(visualSeverity) > severityWeight(stepIssuesByNodeId[nodeId][stepId].severity)) {
          stepIssuesByNodeId[nodeId][stepId].severity = visualSeverity;
        }
      }
    }

    return { nodeIssuesById, stepIssuesByNodeId };
  }, [lintReport]);

  function handleFindingNavigation(finding, context = {}) {
    const contextNode =
      context.node
      || visibleGraph.nodes.find((node) => node.id === context.nodeId)
      || selectedNode
      || null;
    const target = parseWorkspaceEditorTarget(
      finding?.path || contextNode?.path,
      contextNode?.workspaceProject || effectiveWorkspaceScene
    );
    if (!target?.projectId || !target?.path) {
      setAgentVisual({
        op: "issue_navigation_failed",
        phase: "code-editor",
        message: "El hallazgo visual no tiene ruta de archivo navegable.",
        status: "warning",
      });
      return;
    }

    const line = Math.max(1, Number(finding?.line || context.line || context.step?.line || 1) || 1);
    setEditorJumpTarget({
      id: `${Date.now()}-${target.projectId}-${target.path}-${line}`,
      projectId: target.projectId,
      path: target.path,
      line,
      severity: finding?.severity || "warning",
      code: finding?.code || "visual_issue",
      message: finding?.message || "Hallazgo visual seleccionado.",
      hint: finding?.hint || "",
      evidence: finding?.evidence || null,
      source: finding?.source || "",
    });
    focusWorkspaceScene(target.projectId);
    setAgentVisual({
      op: "issue_navigation",
      phase: "code-editor",
      message: `Saltando a ${target.path}:${line}`,
      status: "active",
    });

    window.setTimeout(() => {
      document.getElementById("code-workbench")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 40);
  }

  function handleIssueNavigation(issue, context = {}) {
    const findings = Array.isArray(issue?.findings) && issue.findings.length ? issue.findings : [issue];
    const preferredFinding =
      findings.find((finding) => finding?.path && finding?.line)
      || findings.find((finding) => finding?.path)
      || findings[0];
    handleFindingNavigation(preferredFinding, context);
  }

  function replaceGraph(updater) {
    setGraph((current) => {
      const next = updater(current);
      const withMeta = { ...next, metadata: computeGraphMetadata(next) };
      setDirty(true);
      return withMeta;
    });
  }

  function handleAddNode(position) {
    const node = createNodeFromDraft(nodeDraft, position);
    replaceGraph((current) => ({
      ...current,
      nodes: [...current.nodes, node],
    }));
    setSelectedId(node.id);
    setMapTool("select");
  }

  function handleCreateProgram() {
    const bundle = createProgramBundle(newProgramName, graph, selectedNode);
    replaceGraph((current) => ({
      ...current,
      nodes: [...current.nodes, ...bundle.nodes],
      edges: [...current.edges, ...bundle.edges],
    }));
    setSelectedId(bundle.nodes[0]?.id || null);
  }

  function handleMoveNode(nodeId, position) {
    const targetNode = graph.nodes.find((node) => node.id === nodeId);
    if (targetNode?.readOnly) return;
    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.map((node) => (
        node.id === nodeId
          ? {
            ...node,
            position,
          }
          : node
      )),
    }));
  }

  function handleAddEdge(fromId, toId, type) {
    const fromNode = graph.nodes.find((node) => node.id === fromId);
    const toNode = graph.nodes.find((node) => node.id === toId);
    if (fromNode?.readOnly || toNode?.readOnly) return;
    replaceGraph((current) => {
      if (current.edges.some((edge) => edge.from === fromId && edge.to === toId)) {
        return current;
      }

      const fromNode = current.nodes.find((node) => node.id === fromId);
      const toNode = current.nodes.find((node) => node.id === toId);
      const nextEdges = [
        ...current.edges,
        {
          id: `edge-${fromId}-${toId}-${Date.now()}`,
          from: fromId,
          to: toId,
          type,
          label: type === "socket" ? "sincroniza" : type === "reference" ? "referencia" : type === "import" ? "importa" : "usa",
          dashed: false,
        },
      ];

      const nextNodes = current.nodes.map((node) => {
        if (node.id === fromId && toNode) {
          return { ...node, imports: dedupeReferences([...node.imports, toNode.path]) };
        }
        if (node.id === toId && fromNode) {
          return { ...node, dependents: dedupeReferences([...node.dependents, fromNode.path]) };
        }
        return node;
      });

      return {
        ...current,
        nodes: nextNodes,
        edges: nextEdges,
      };
    });
  }

  function updateSelectedNodeField(field, value) {
    if (!selectedNode || selectedNode.readOnly) return;
    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.map((node) => {
        if (node.id !== selectedNode.id) return node;
        const nextNode = { ...node, [field]: value };
        if (field === "layerLabel") {
          nextNode.layer = slugify(value) || node.layer;
          nextNode.color = nextNode.color || defaultColorForLayer(nextNode.layer);
        }
        if (field === "layer") {
          nextNode.layer = slugify(value) || "script";
          nextNode.layerLabel = titleizeLayer(nextNode.layer);
          nextNode.color = defaultColorForLayer(nextNode.layer);
        }
        if (field === "code") {
          nextNode.lines = Math.max(1, String(value).split("\n").length);
        }
        if (field === "name" && (!node.codeLanguage || node.codeLanguage === "text")) {
          nextNode.codeLanguage = detectLanguageFromName(value);
        }
        return nextNode;
      }),
    }));
  }

  function updateSelectedEdgeField(field, value) {
    if (!selectedEdge) return;
    const fromNode = graph.nodes.find((node) => node.id === selectedEdge.from);
    const toNode = graph.nodes.find((node) => node.id === selectedEdge.to);
    if (fromNode?.readOnly || toNode?.readOnly) return;
    replaceGraph((current) => ({
      ...current,
      edges: current.edges.map((edge) => edge.id === selectedEdge.id ? { ...edge, [field]: value } : edge),
    }));
  }

  function deleteSelectedEdge() {
    if (!selectedEdge) return;
    const fromNode = graph.nodes.find((node) => node.id === selectedEdge.from);
    const toNode = graph.nodes.find((node) => node.id === selectedEdge.to);
    if (fromNode?.readOnly || toNode?.readOnly) return;
    replaceGraph((current) => ({
      ...current,
      edges: current.edges.filter((edge) => edge.id !== selectedEdge.id),
    }));
    setSelectedEdgeId(null);
  }

  function deleteSelectedNode() {
    if (!selectedNode || selectedNode.readOnly) return;
    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.filter((node) => node.id !== selectedNode.id),
      edges: current.edges.filter((edge) => edge.from !== selectedNode.id && edge.to !== selectedNode.id),
    }));
    setSelectedId(null);
    setSelectedEdgeId(null);
  }

  function handleAddStep(position, type) {
    if (!selectedNode || selectedNode.readOnly) return;

    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.map((node) => {
        if (node.id !== selectedNode.id) return node;
        const stepId = `${type}-${Date.now()}`;
        const nextStep = {
          id: stepId,
          type,
          label: type === "start" ? "Inicio" : type === "end" ? "Fin" : "Nuevo bloque",
          x: position.x,
          y: position.y,
          code: "",
          codeLanguage: node.codeLanguage || "text",
          color: null,
        };
        return {
          ...node,
          algorithm: {
            ...node.algorithm,
            source: "editor",
            steps: [...node.algorithm.steps, nextStep],
          },
        };
      }),
    }));
    setFlowTool("select");
  }

  function handleMoveStep(stepId, position) {
    if (!selectedNode || selectedNode.readOnly) return;
    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.map((node) => {
        if (node.id !== selectedNode.id) return node;
        return {
          ...node,
          algorithm: {
            ...node.algorithm,
            steps: node.algorithm.steps.map((step) => step.id === stepId ? { ...step, ...position } : step),
          },
        };
      }),
    }));
  }

  function handleAddStepEdge(fromStepId, toStepId) {
    if (!selectedNode || selectedNode.readOnly) return;
    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.map((node) => {
        if (node.id !== selectedNode.id) return node;
        if (node.algorithm.edges.some((edge) => edge.from === fromStepId && edge.to === toStepId)) {
          return node;
        }
        return {
          ...node,
          algorithm: {
            ...node.algorithm,
            source: "editor",
            edges: [
              ...node.algorithm.edges,
              {
                id: `flow-${fromStepId}-${toStepId}-${Date.now()}`,
                from: fromStepId,
                to: toStepId,
                label: "",
              },
            ],
          },
        };
      }),
    }));
    setFlowTool("select");
  }

  function updateSelectedStepField(field, value) {
    if (!selectedNode || selectedNode.readOnly || !selectedStep) return;
    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.map((node) => {
        if (node.id !== selectedNode.id) return node;
        return {
          ...node,
          algorithm: {
            ...node.algorithm,
            source: "editor",
            steps: node.algorithm.steps.map((step) => (
              step.id === selectedStep.id
                ? { ...step, [field]: value }
                : step
            )),
          },
        };
      }),
    }));
  }

  function deleteSelectedStep() {
    if (!selectedNode || selectedNode.readOnly || !selectedStep) return;
    replaceGraph((current) => ({
      ...current,
      nodes: current.nodes.map((node) => {
        if (node.id !== selectedNode.id) return node;
        return {
          ...node,
          algorithm: {
            ...node.algorithm,
            steps: node.algorithm.steps.filter((step) => step.id !== selectedStep.id),
            edges: node.algorithm.edges.filter((edge) => edge.from !== selectedStep.id && edge.to !== selectedStep.id),
          },
        };
      }),
    }));
    setSelectedStepId(null);
  }

  async function loadLintReport(scene = lintScopeScene, options = {}) {
    const { signal } = options;
    setIsLinting(true);
    setLintError("");

    try {
      const params = new URLSearchParams();
      if (scene) {
        params.set("scene", scene);
      }
      const query = params.toString() ? `?${params.toString()}` : "";
      const response = await fetch(`${SOCKET_URL}/api/architecture/lint${query}`, { signal });
      if (!response.ok) {
        throw new Error(`No fue posible auditar el mapa (${response.status})`);
      }
      const payload = await response.json();
      if (signal?.aborted) return;
      setLintReport(payload.report || EMPTY_LINT_REPORT);
    } catch (error) {
      if (error?.name === "AbortError") return;
      setLintError(error?.message || "No fue posible auditar el mapa.");
    } finally {
      if (!signal?.aborted) {
        setIsLinting(false);
      }
    }
  }

  async function handleAnalyzePath() {
    const targetPath = analysisTargetPath.trim();
    if (!targetPath) return;

    setIsAnalyzing(true);
    setAnalysisError("");
    try {
      const payload = await emitWithAck(socketRef.current, "reverse:analyze", { targetPath });
      setAnalysisSessions(payload.sessions || []);
      setSequencePlan(null);
      setSequenceCursor(0);
      setMapTool("select");
      setFlowTool("select");
      if (payload.entry?.primaryNodeId) {
        setSelectedId(payload.entry.primaryNodeId);
        setSelectedEdgeId(null);
        setSelectedStepId(null);
      }
    } catch (error) {
      setAnalysisError(humanizeReverseError(error) || "No fue posible analizar la ruta.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleRemoveAnalysis(sessionId) {
    if (!sessionId) return;

    setAnalysisError("");
    try {
      const payload = await emitWithAck(socketRef.current, "reverse:remove", { analysisId: sessionId });
      setAnalysisSessions(payload.sessions || []);
      if (selectedNode?.analysisId === sessionId) {
        setSelectedId(null);
        setSelectedEdgeId(null);
        setSelectedStepId(null);
        setSequencePlan(null);
        setSequenceCursor(0);
      }
    } catch (error) {
      setAnalysisError(humanizeReverseError(error) || "No fue posible quitar la escena analizada.");
    }
  }

  async function handleTranscribePathWithAgent() {
    const targetPath = analysisTargetPath.trim();
    if (!targetPath) return;

    setIsAgentTranscribing(true);
    setAnalysisError("");
    try {
      await emitWithAck(socketRef.current, "reverse:agent-transcribe", { targetPath });
      setSequencePlan(null);
      setSequenceCursor(0);
      setMapTool("select");
      setFlowTool("select");
      setSelectedEdgeId(null);
      setSelectedStepId(null);
    } catch (error) {
      setAnalysisError(humanizeReverseError(error) || "No fue posible transcribir la ruta con el agente.");
    } finally {
      setIsAgentTranscribing(false);
    }
  }

  function handleStartSequence() {
    const anchorNode = selectedNode || visibleGraph.nodes[0];
    if (!anchorNode) return;

    const nextPlan = buildSequencePlan(visibleGraph, anchorNode.id);
    if (!nextPlan?.nodeIds?.length) return;

    setSequencePlan(nextPlan);
    setSequenceCursor(0);
    setFlowTool("select");
    setSelectedEdgeId(null);
    setSelectedId(nextPlan.nodeIds[0] || null);
  }

  function moveSequenceCursor(nextIndex) {
    if (!sequencePlan?.nodeIds?.length) return;

    const clampedIndex = Math.max(0, Math.min(nextIndex, sequencePlan.nodeIds.length - 1));
    setSequenceCursor(clampedIndex);
    setFlowTool("select");
    setSelectedEdgeId(null);
    setSelectedId(sequencePlan.nodeIds[clampedIndex] || null);
  }

  function handleExitSequence() {
    setSequencePlan(null);
    setSequenceCursor(0);
    setSelectedEdgeId(null);
    setFlowTool("select");
  }

  function normalizeEmbeddedSandbox(payload = {}) {
    const sandbox = payload.sandbox && typeof payload.sandbox === "object" ? payload.sandbox : payload;
    const embedUrl = String(sandbox.embedUrl || sandbox.url || "");
    const logs = Array.isArray(sandbox.logs) ? sandbox.logs : Array.isArray(payload.logs) ? payload.logs : [];
    return {
      ...EMPTY_EMBEDDED_SANDBOX,
      ...sandbox,
      embedUrl,
      url: String(sandbox.url || embedUrl),
      project: String(sandbox.project || sandbox.projectId || payload.projectId || ""),
      logs,
    };
  }

  async function loadEmbeddedSandbox(projectSlug = effectiveWorkspaceScene, options = {}) {
    const projectId = String(projectSlug || "").trim();
    if (!projectId || viewAllWorkspaceScenes) {
      setEmbeddedSandbox(EMPTY_EMBEDDED_SANDBOX);
      setEmbeddedSandboxOpen(false);
      setEmbeddedSandboxError("");
      return null;
    }

    if (!options.silent) {
      setEmbeddedSandboxBusy(true);
    }
    setEmbeddedSandboxError("");

    try {
      const response = await fetch(`${SOCKET_URL}/api/projects/${encodeURIComponent(projectId)}/sandbox`, {
        signal: options.signal,
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || `sandbox_status_failed_${response.status}`);
      }
      if (options.signal?.aborted) return null;
      const nextSandbox = normalizeEmbeddedSandbox(payload);
      setEmbeddedSandbox(nextSandbox);
      if (nextSandbox.running && nextSandbox.embedUrl) {
        setEmbeddedSandboxOpen(true);
      }
      return nextSandbox;
    } catch (error) {
      if (error?.name === "AbortError") return null;
      if (!options.silent) {
        setEmbeddedSandboxError(error?.message || "No fue posible leer el sandbox.");
      }
      return null;
    } finally {
      if (!options.signal?.aborted && !options.silent) {
        setEmbeddedSandboxBusy(false);
      }
    }
  }

  async function startEmbeddedSandbox(projectSlug = effectiveWorkspaceScene) {
    const projectId = String(projectSlug || "").trim();
    if (!projectId || viewAllWorkspaceScenes) return;
    setEmbeddedSandboxBusy(true);
    setEmbeddedSandboxError("");

    try {
      const response = await fetch(`${SOCKET_URL}/api/projects/${encodeURIComponent(projectId)}/sandbox/start`, {
        method: "POST",
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || `sandbox_start_failed_${response.status}`);
      }
      const nextSandbox = normalizeEmbeddedSandbox(payload);
      setEmbeddedSandbox(nextSandbox);
      setEmbeddedSandboxOpen(Boolean(nextSandbox.embedUrl));
      setEmbeddedSandboxFrameKey((current) => current + 1);
    } catch (error) {
      setEmbeddedSandboxError(error?.message || "No fue posible arrancar el sandbox.");
    } finally {
      setEmbeddedSandboxBusy(false);
    }
  }

  async function stopEmbeddedSandbox(projectSlug = effectiveWorkspaceScene) {
    const projectId = String(projectSlug || "").trim();
    if (!projectId || viewAllWorkspaceScenes) return;
    setEmbeddedSandboxBusy(true);
    setEmbeddedSandboxError("");

    try {
      const response = await fetch(`${SOCKET_URL}/api/projects/${encodeURIComponent(projectId)}/sandbox/stop`, {
        method: "POST",
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || `sandbox_stop_failed_${response.status}`);
      }
      const nextSandbox = normalizeEmbeddedSandbox(payload);
      setEmbeddedSandbox(nextSandbox);
      setEmbeddedSandboxOpen(false);
    } catch (error) {
      setEmbeddedSandboxError(error?.message || "No fue posible detener el sandbox.");
    } finally {
      setEmbeddedSandboxBusy(false);
    }
  }

  useEffect(() => {
    if (!sequencePlan?.nodeIds?.length) return;

    const availableIds = new Set(graph.nodes.map((node) => node.id));
    const validNodeIds = sequencePlan.nodeIds.filter((nodeId) => availableIds.has(nodeId));
    if (!validNodeIds.length) {
      setSequencePlan(null);
      setSequenceCursor(0);
      return;
    }

    if (validNodeIds.length !== sequencePlan.nodeIds.length) {
      const validIdSet = new Set(validNodeIds);
      setSequencePlan((current) => current ? {
        ...current,
        nodeIds: validNodeIds,
        links: (current.links || []).filter((link) => validIdSet.has(link.fromNodeId) && validIdSet.has(link.toNodeId)),
      } : current);
      setSequenceCursor((current) => Math.min(current, validNodeIds.length - 1));
    }
  }, [visibleGraph.nodes, sequencePlan]);

  useEffect(() => {
    if (!sequencePlan?.nodeIds?.length) return;

    if (!selectedId) {
      handleExitSequence();
      return;
    }

    const nextIndex = sequencePlan.nodeIds.indexOf(selectedId);
    if (nextIndex === -1) {
      handleExitSequence();
      return;
    }

    setSequenceCursor((current) => current === nextIndex ? current : nextIndex);
  }, [selectedId, sequencePlan]);

  useEffect(() => {
    if (!effectiveWorkspaceScene || viewAllWorkspaceScenes) {
      setEmbeddedSandbox(EMPTY_EMBEDDED_SANDBOX);
      setEmbeddedSandboxOpen(false);
      setEmbeddedSandboxError("");
      return undefined;
    }

    const controller = new AbortController();
    const timerId = window.setTimeout(() => {
      loadEmbeddedSandbox(effectiveWorkspaceScene, { silent: true, signal: controller.signal });
    }, 300);

    return () => {
      controller.abort();
      window.clearTimeout(timerId);
    };
  }, [effectiveWorkspaceScene, viewAllWorkspaceScenes]);

  async function handleSaveGraph() {
    setIsSaving(true);
    try {
      const response = await fetch(`${SOCKET_URL}/api/architecture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(graph),
      });
      const payload = await response.json();
      const hydrated = applyDefaultLayout(payload.graph || graph);
      setGraph({ ...hydrated, metadata: computeGraphMetadata(hydrated) });
      setDirty(false);
    } finally {
      setIsSaving(false);
    }
  }

  function handleResetView() {
    setIsResetting(true);
    setAnalysisError("");
    setLintError("");
    setGraph(buildLocalClearedGraph(graph.metadata?.projectName));
    setActiveWorkspaceScene("");
    setViewAllWorkspaceScenes(false);
    setAnalysisSessions([]);
    setAnalysisTargetPath("");
    setSelectedId(null);
    setSelectedEdgeId(null);
    setSelectedStepId(null);
    setSequencePlan(null);
    setSequenceCursor(0);
    setMapTool("select");
    setFlowTool("select");
    setDirty(false);
    setLintReport(EMPTY_LINT_REPORT);
    setAgentVisual(null);
    setIsResetting(false);
  }

  function handleWorkspaceClean(payload = {}) {
    const blankGraph = payload?.graph || buildLocalClearedGraph("Vista en blanco");
    const hydrated = applyDefaultLayout(blankGraph);
    setGraph({
      ...hydrated,
      metadata: computeGraphMetadata(hydrated),
    });
    setActiveWorkspaceScene("");
    setViewAllWorkspaceScenes(false);
    setAnalysisSessions([]);
    setAnalysisTargetPath("");
    setSelectedId(null);
    setSelectedEdgeId(null);
    setSelectedStepId(null);
    setSequencePlan(null);
    setSequenceCursor(0);
    setMapTool("select");
    setFlowTool("select");
    setDirty(false);
    setLintReport(EMPTY_LINT_REPORT);
    setLintError("");
    setAgentVisual({ op: "workspace_cleaned", phase: "cleanup", message: "Workspace blanqueado." });
  }

  async function handleLoadHablaDemo() {
    setIsResetting(true);
    setAnalysisError("");
    setLintError("");
    try {
      const response = await fetch(`${SOCKET_URL}/api/architecture/demo/habla`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.error || "demo_load_failed");
      }
      const hydrated = applyDefaultLayout(payload.graph || EMPTY_GRAPH);
      setGraph({
        ...hydrated,
        metadata: computeGraphMetadata(hydrated),
      });
      setActiveWorkspaceScene("");
      setViewAllWorkspaceScenes(true);
      setAnalysisSessions([]);
      setAnalysisTargetPath("");
      setSelectedId(hydrated.nodes[0]?.id || null);
      setSelectedEdgeId(null);
      setSelectedStepId(null);
      setSequencePlan(null);
      setSequenceCursor(0);
      setMapTool("select");
      setFlowTool("select");
      setDirty(false);
      setLintReport(EMPTY_LINT_REPORT);
      setAgentVisual({ op: "habla_architecture_demo", phase: "demo", message: "Demo de arquitectura HABLA cargada." });
    } catch (error) {
      setLintError(error?.message || "No fue posible cargar demo HABLA.");
    } finally {
      setIsResetting(false);
    }
  }

  useEffect(() => {
    if (!visibleGraph.nodes.length) {
      setLintReport(EMPTY_LINT_REPORT);
      setLintError("");
      return undefined;
    }

    const controller = new AbortController();
    const timerId = window.setTimeout(() => {
      loadLintReport(lintScopeScene, { signal: controller.signal });
    }, 700);

    return () => {
      controller.abort();
      window.clearTimeout(timerId);
    };
  }, [visibleGraph.metadata?.updatedAt, lintScopeScene]);

  const agentPresenceStyle = agentPresenceActive ? {
    "--agent-map-scale": agentPresence.mapScale || 1,
    "--agent-map-pan-x": `${agentPresence.mapPanX || 0}px`,
    "--agent-map-pan-y": `${agentPresence.mapPanY || 0}px`,
    "--agent-flow-scale": agentPresence.flowScale || 1,
    "--agent-flow-pan-x": `${agentPresence.flowPanX || 0}px`,
    "--agent-flow-pan-y": `${agentPresence.flowPanY || 0}px`,
  } : undefined;
  const latestObserverEvent = observerTimeline[0] || null;
  const observerMemory = observerStatus?.memory || {};
  const observerRules = observerBehaviorTree?.rules || [];
  const embeddedSandboxUrl = embeddedSandbox.embedUrl || embeddedSandbox.url || "";
  const embeddedSandboxLabel = effectiveWorkspaceScene
    ? workspaceSceneOptions.find((scene) => scene.key === effectiveWorkspaceScene)?.label || effectiveWorkspaceScene
    : "Sin proyecto activo";
  const embeddedSandboxReady = Boolean(embeddedSandbox.running && embeddedSandbox.ready && embeddedSandboxUrl);
  const cyberlaceMathBoardLines = useMemo(() => {
    const trace = cyberlaceBlockingAlert?.mathTrace;
    if (!trace) return [];
    const rows = Array.isArray(trace.rows) ? trace.rows : [];
    const action = cyberlaceBlockingAlert?.action || "BLOCK";
    const project = cyberlaceBlockingAlert?.projectSlug || "runtime";
    const headerLines = [
      { label: "Pregunta", equation: "¿Ejecutar P o transformar P en P_safe?" },
      { label: "Contexto", equation: `project=${project}; action=${action}; evidence=${cyberlaceBlockingAlert?.evidenceCount || 0}` },
    ];
    const conclusionLines = [
      { label: "Decision", equation: `Risk=${trace.riskScore} >= θ=${trace.threshold} => ${action}; worker=DENIED; pid=null` },
      { label: "Memoria", equation: `experience -> SafetyLearningCore; repair=${trace.repairOperator}; node=${trace.failureNode}` },
    ];
    return [...headerLines, ...rows, ...conclusionLines].filter((row) => row?.label && row?.equation);
  }, [cyberlaceBlockingAlert]);

  useEffect(() => {
    setCyberlaceMathWriter({ lineIndex: 0, charIndex: 0 });
  }, [
    cyberlaceBlockingAlert?.timestamp,
    cyberlaceBlockingAlert?.sessionId,
    cyberlaceBlockingAlert?.projectSlug,
    cyberlaceBlockingAlert?.action,
    cyberlaceBlockingAlert?.mathTrace?.riskScore,
  ]);

  useEffect(() => {
    if (!cyberlaceMathBoardLines.length) return undefined;
    const activeLine = cyberlaceMathBoardLines[cyberlaceMathWriter.lineIndex];
    if (!activeLine) return undefined;
    const equation = String(activeLine.equation || "");
    const atLineEnd = cyberlaceMathWriter.charIndex >= equation.length;
    const atBoardEnd = cyberlaceMathWriter.lineIndex >= cyberlaceMathBoardLines.length - 1;
    if (atLineEnd && atBoardEnd) return undefined;
    const delay = atLineEnd ? 620 : 24 + Math.min(24, Math.floor(equation.length / 18));
    const timer = window.setTimeout(() => {
      setCyberlaceMathWriter((current) => {
        const currentLine = cyberlaceMathBoardLines[current.lineIndex];
        if (!currentLine) return current;
        const currentEquation = String(currentLine.equation || "");
        if (current.charIndex < currentEquation.length) {
          return { lineIndex: current.lineIndex, charIndex: current.charIndex + 1 };
        }
        if (current.lineIndex < cyberlaceMathBoardLines.length - 1) {
          return { lineIndex: current.lineIndex + 1, charIndex: 0 };
        }
        return current;
      });
    }, delay);
    return () => window.clearTimeout(timer);
  }, [cyberlaceMathBoardLines, cyberlaceMathWriter.lineIndex, cyberlaceMathWriter.charIndex]);

  useEffect(() => {
    const board = cyberlaceMathBoardRef.current;
    if (!board) return;
    board.scrollTop = board.scrollHeight;
  }, [cyberlaceMathWriter.lineIndex, cyberlaceMathWriter.charIndex]);

  function clampRuntimeDashboardWidth(value) {
    return Math.min(520, Math.max(248, Number(value) || 318));
  }

  function startRuntimeDashboardResize(event) {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = runtimeDashboardWidth;
    document.body.classList.add("is-runtime-dashboard-resizing");
    function handleMove(moveEvent) {
      setRuntimeDashboardWidth(clampRuntimeDashboardWidth(startWidth + moveEvent.clientX - startX));
    }
    function handleDone() {
      document.body.classList.remove("is-runtime-dashboard-resizing");
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleDone);
      window.removeEventListener("pointercancel", handleDone);
    }
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleDone);
    window.addEventListener("pointercancel", handleDone);
  }

  function handleRuntimeDashboardResizeKey(event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 24 : -24;
    setRuntimeDashboardWidth((current) => clampRuntimeDashboardWidth(current + delta));
  }

  return (
    <div
      className={`app-shell ${connected ? "is-connected" : ""} ${agentVisual?.phase || agentVisual?.op ? "is-agent-active" : ""} ${agentPresenceActive ? "is-agent-presence-active" : ""} ${agentPresenceActive ? `is-agent-action-${agentPresence.kind}` : ""}`}
      style={agentPresenceStyle}
    >
      <AppTopbar
        connected={connected}
        agentVisual={agentVisual}
        autonomousMode={autonomousMode}
        visibleGraph={visibleGraph}
        workspaceSceneOptions={workspaceSceneOptions}
        effectiveWorkspaceScene={effectiveWorkspaceScene}
        viewAllWorkspaceScenes={viewAllWorkspaceScenes}
        defaultWorkspaceScene={defaultWorkspaceScene}
        isResetting={isResetting}
        onToggleAutonomousMode={toggleAutonomousMode}
        onViewAllScenes={() => setViewAllWorkspaceScenes(true)}
        onReturnActiveProject={() => setViewAllWorkspaceScenes(false)}
        onLoadHablaDemo={handleLoadHablaDemo}
        onResetView={handleResetView}
      />

      <AppAgentPresenceLayer
        active={agentPresenceActive}
        presence={agentPresence}
        mode={agentPresenceMode}
      />

      {cyberlaceBlockingAlert ? (
        <div className="cyberlace-critical-overlay" role="dialog" aria-modal="true" aria-label="CyberLACE bloqueo critico">
          <div className="cyberlace-critical-stage">
            <div className="cyberlace-critical-modal">
              <div className="cyberlace-critical-badge">WARNING</div>
              <h2>PELIGRO: potencial informacion insegura</h2>
              <p className="cyberlace-critical-message">{cyberlaceBlockingAlert.message}</p>
              <p>CyberLACE nego esta accion antes de ejecutar Codex. No se ejecutara aunque el usuario la confirme.</p>
              {harnessTrainingAutomationState.active && harnessTrainingAutomationState.autoAcceptSafeAlternative ? (
                <p className="cyberlace-autoaccept-banner">Harness Autopilot activo: el sistema aceptara automaticamente la alternativa segura.</p>
              ) : null}
              {cyberlaceBlockingAlert.mathTrace ? (
                <div className="cyberlace-math-proof cyberlace-math-blackboard" aria-label="Pizarra matematica CyberLACE en vivo">
                  <div className="cyberlace-math-board-head">
                    <strong>Pizarra matematica en vivo</strong>
                    <span>typewriter · investigacion formal</span>
                  </div>
                  <div className="cyberlace-math-grid">
                    <code>Risk={cyberlaceBlockingAlert.mathTrace.riskScore}</code>
                    <code>θ={cyberlaceBlockingAlert.mathTrace.threshold}</code>
                    <code>Loss={cyberlaceBlockingAlert.mathTrace.loss}</code>
                    <code>R*={cyberlaceBlockingAlert.mathTrace.repairOperator}</code>
                  </div>
                  <div className="cyberlace-math-board" ref={cyberlaceMathBoardRef}>
                    {cyberlaceMathBoardLines.slice(0, cyberlaceMathWriter.lineIndex + 1).map((row, index) => {
                      const equation = String(row.equation || "");
                      const isActive = index === cyberlaceMathWriter.lineIndex;
                      const visibleEquation = isActive ? equation.slice(0, cyberlaceMathWriter.charIndex) : equation;
                      return (
                        <div className={`cyberlace-math-line ${isActive ? "is-active" : "is-complete"}`} key={`${row.label}-${index}`}>
                          <span>{String(index + 1).padStart(2, "0")} · {row.label}</span>
                          <code>
                            {visibleEquation}
                            {isActive ? <i aria-hidden="true" /> : null}
                          </code>
                        </div>
                      );
                    })}
                  </div>
                  <p>Nodo geometrico probable: <b>{cyberlaceBlockingAlert.mathTrace.failureNode}</b></p>
                </div>
              ) : null}
              {cyberlaceBlockingAlert.safeAlternative ? (
                <div className="cyberlace-safe-inline-visible">
                  <div className="cyberlace-safe-inline-head">
                    <span>DIRECCION SEGURA DISPONIBLE</span>
                    <b aria-hidden="true">✓</b>
                  </div>
                  <h3>{cyberlaceBlockingAlert.safeAlternative.title || "Alternativa segura permitida"}</h3>
                  <p>{cyberlaceBlockingAlert.safeAlternative.summary}</p>
                  {cyberlaceBlockingAlert.safeAlternative.suggestedRequirement ? (
                    <>
                      <strong>Tarea segura que HABLA si puede hacer</strong>
                      <p className="cyberlace-safe-inline-rewrite">{cyberlaceBlockingAlert.safeAlternative.suggestedRequirement}</p>
                      <button className="cyberlace-safe-inline-accept" type="button" onClick={acceptCyberlaceSafeAlternative}>
                        Aceptar alternativa segura como contexto autorizado
                      </button>
                    </>
                  ) : null}
                </div>
              ) : null}
              <dl>
                <div>
                  <dt>Accion</dt>
                  <dd>{cyberlaceBlockingAlert.action}</dd>
                </div>
                <div>
                  <dt>Proyecto</dt>
                  <dd>{cyberlaceBlockingAlert.projectSlug || "runtime"}</dd>
                </div>
                <div>
                  <dt>Evidencia</dt>
                  <dd>{cyberlaceBlockingAlert.evidenceCount} patron(es) sensible(s), valores redactados</dd>
                </div>
              </dl>
              {cyberlaceBlockingAlert.paths.length ? (
                <ul>
                  {cyberlaceBlockingAlert.paths.map((item) => <li key={item}>{item}</li>)}
                </ul>
              ) : null}
              <p className="cyberlace-critical-reason">{cyberlaceBlockingAlert.reason}</p>
              {cyberlaceBlockingAlert.deniedAction ? (
                <div className="cyberlace-denied-action">
                  <strong>Accion negada</strong>
                  <p>{cyberlaceBlockingAlert.deniedAction}</p>
                </div>
              ) : null}
              <div className="cyberlace-critical-actions">
                {cyberlaceBlockingAlert.safeAlternative ? (
                  <button
                    className="cyberlace-safe-focus-button"
                    type="button"
                    onClick={() => document.getElementById("cyberlace-safe-guidance-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" })}
                  >
                    Ver direccion segura
                  </button>
                ) : null}
                <button type="button" onClick={() => setCyberlaceBlockingAlert(null)}>Entendido</button>
              </div>
            </div>
            {cyberlaceBlockingAlert.safeAlternative ? (
              <aside id="cyberlace-safe-guidance-panel" className="cyberlace-safe-guidance-modal" aria-label="Direccion segura valida de HABLA">
                <div className="cyberlace-safe-topline">
                  <div className="cyberlace-safe-badge">DIRECCION SEGURA</div>
                  <div className="cyberlace-safe-check" aria-hidden="true">✓</div>
                </div>
                <h2>{cyberlaceBlockingAlert.safeAlternative.title || "Propuesta segura valida"}</h2>
                <p>{cyberlaceBlockingAlert.safeAlternative.summary}</p>
                {Array.isArray(cyberlaceBlockingAlert.safeAlternative.allowedActions) && cyberlaceBlockingAlert.safeAlternative.allowedActions.length ? (
                  <ul>
                    {cyberlaceBlockingAlert.safeAlternative.allowedActions.slice(0, 6).map((item) => <li key={item}>{item}</li>)}
                  </ul>
                ) : null}
                {cyberlaceBlockingAlert.mathTrace ? (
                  <div className="cyberlace-safe-math-card">
                    <strong>Ecuacion de direccion segura</strong>
                    <code>{cyberlaceBlockingAlert.mathTrace.rows.find((row) => row.label === "Ruta segura")?.equation}</code>
                    <p>La solucion valida transforma el prompt inseguro P en P_safe, removiendo secretos y manteniendo la intencion profesional permitida.</p>
                  </div>
                ) : null}
                {cyberlaceBlockingAlert.safeAlternative.suggestedRequirement ? (
                  <div className="cyberlace-safe-rewrite-card">
                    <strong>Tarea segura sugerida</strong>
                    <p>{cyberlaceBlockingAlert.safeAlternative.suggestedRequirement}</p>
                    <button
                      className="cyberlace-safe-accept-button"
                      type="button"
                      data-cyberlace-safe-accept="primary"
                      onClick={acceptCyberlaceSafeAlternative}
                    >
                      Aceptar alternativa segura
                    </button>
                  </div>
                ) : null}
                {cyberlaceBlockingAlert.safeNextSteps?.length ? (
                  <div className="cyberlace-safe-next-card">
                    <strong>Siguiente camino seguro</strong>
                    <ul>
                      {cyberlaceBlockingAlert.safeNextSteps.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </div>
                ) : null}
              </aside>
            ) : null}
          </div>
        </div>
      ) : null}

      <SectionDividerMenu id="runtime" label="01 Runtime" title="Runtime" />

      <div className="runtime-dashboard-zone" style={{ "--runtime-dashboard-width": `${runtimeDashboardWidth}px` }}>
        <RuntimeDashboardSidebar
          projects={agentProjects}
          projectsLoading={agentProjectsLoading}
          projectActionStatus={projectActionStatus}
          newProjectName={newProjectName}
          selectedProjectSlug={effectiveWorkspaceScene}
          onNewProjectNameChange={setNewProjectName}
          onCreateProject={createSidebarProject}
          onSelectProject={(projectSlug) => {
            focusWorkspaceScene(projectSlug);
            document.getElementById("section-editor")?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
          onArchiveProject={archiveSidebarProject}
          onDeleteProject={deleteSidebarProject}
          onOpenHarnessStudio={openHarnessEngineeringStudio}
        />

        <div
          className="runtime-dashboard-resizer"
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize runtime dashboard"
          tabIndex="0"
          onPointerDown={startRuntimeDashboardResize}
          onKeyDown={handleRuntimeDashboardResizeKey}
        />

        <div className="runtime-dashboard-content">
          {harnessStudioOpen ? (
            <HarnessEngineeringStudio
              socketUrl={SOCKET_URL}
              onClose={() => setHarnessStudioOpen(false)}
            />
          ) : null}

          <AppLintPanel
            visibleGraph={visibleGraph}
            lintReport={lintReport}
            lintScopeLabel={lintScopeLabel}
            lintScopeScene={lintScopeScene}
            lintError={lintError}
            isLinting={isLinting}
            agentVisual={agentVisual}
            onLoadLintReport={loadLintReport}
            onFindingNavigation={handleFindingNavigation}
          />

          <AppObserverPanel
            observerStatus={observerStatus}
            observerTimeline={observerTimeline}
            observerRules={observerRules}
            observerMemory={observerMemory}
            latestObserverEvent={latestObserverEvent}
            observerActionStatus={observerActionStatus}
            effectiveWorkspaceScene={effectiveWorkspaceScene}
            onObserveNow={observeNow}
            onRunObserverAction={runObserverAction}
            onUpdateObserverRule={updateObserverRule}
          />

          <CyberLACEPanel />
        </div>
      </div>

      <SectionDividerMenu id="input" label="03 Entrada" title="Entrada" />

      <section className="reverse-panel">
        <div className="panel-header compact">
          <div>
            <h2>Ingenieria inversa</h2>
            <p>Carga una ruta local para convertirla en escena de solo lectura con mapa conceptual, CFG y alertas visuales.</p>
          </div>
          <div className="toolbar-inline compact">
            <span className="meta-pill">{analysisSessions.length} escena(s)</span>
          </div>
        </div>

        <div className="reverse-body">
          <div className="toolbar-inline compact reverse-input-row">
            <label className="editor-field small grow">
              <span>Ruta local del archivo o carpeta</span>
              <input
                value={analysisTargetPath}
                onChange={(event) => setAnalysisTargetPath(event.target.value)}
                placeholder="/home/neurodriver/proyecto/script.py"
              />
            </label>
            <button type="button" className="tool-button primary" onClick={handleAnalyzePath} disabled={isAnalyzing || !analysisTargetPath.trim()}>
              {isAnalyzing ? "Analizando..." : "Analizar ruta"}
            </button>
            <button
              type="button"
              className="tool-button"
              onClick={handleTranscribePathWithAgent}
              disabled={isAgentTranscribing || !analysisTargetPath.trim()}
            >
              {isAgentTranscribing ? "Transcribiendo..." : "Transcribir con agente"}
            </button>
          </div>

          {analysisError ? <p className="agent-error">{analysisError}</p> : null}

          {analysisSessions.length ? (
            <div className="reverse-session-list">
              {analysisSessions.map((session) => (
                <article key={session.id} className="reverse-session-card">
                  <div>
                    <strong>{session.label}</strong>
                    <small>{session.mode === "directory" ? "Carpeta completa" : "Archivo o script"} · {session.nodeCount} nodos · {session.edgeCount} conexiones</small>
                    <code className="lint-path">{session.targetPath}</code>
                  </div>
                  <div className="reverse-session-actions">
                    <button
                      type="button"
                      className="tool-button"
                      onClick={() => {
                        setSequencePlan(null);
                        setSequenceCursor(0);
                        if (session.primaryNodeId) {
                          setSelectedId(session.primaryNodeId);
                          setSelectedEdgeId(null);
                          setSelectedStepId(null);
                        }
                      }}
                    >
                      Abrir escena
                    </button>
                    <button type="button" className="tool-button danger" onClick={() => handleRemoveAnalysis(session.id)}>
                      Quitar escena
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="lint-clean">Todavia no hay escenas cargadas por ingenieria inversa.</p>
          )}
        </div>
      </section>

      <SectionDividerMenu id="toolbox" label="04 Toolbox" title="Toolbox" />

      <section className="editor-toolbar-panel">
        <div className="panel-header compact">
          <div>
            <h2>Toolbox</h2>
            <p>Crea programas completos, bloques sueltos, flechas y edita el codigo de cada pieza.</p>
          </div>
        </div>

        <div className="editor-toolbar-grid">
          <div className="toolbar-group">
            <span className="toolbar-label">Mapa conceptual</span>
            <div className="toolbar-inline">
              <button type="button" className={`tool-button ${mapTool === "select" ? "active" : ""}`} onClick={() => setMapTool("select")}>Mover mapa</button>
              <button type="button" className={`tool-button ${mapTool === "connect" ? "active" : ""}`} onClick={() => setMapTool("connect")}>Conectar</button>
              <button type="button" className={`tool-button ${mapTool === "add-node" ? "active" : ""}`} onClick={() => setMapTool("add-node")}>Crear bloque</button>
            </div>

            <div className="toolbar-inline compact">
              <label className="editor-field small">
                <span>Tipo de flecha</span>
                <select value={edgeType} onChange={(event) => setEdgeType(event.target.value)}>
                  {EDGE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
                </select>
              </label>
            </div>
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Nuevo programa</span>
            <div className="toolbar-inline compact">
              <label className="editor-field small grow">
                <span>Nombre del programa/capa</span>
                <input value={newProgramName} onChange={(event) => setNewProgramName(event.target.value)} placeholder="payments-engine" />
              </label>
              <button type="button" className="tool-button primary" onClick={handleCreateProgram}>Crear programa</button>
            </div>
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Nuevo bloque manual</span>
            <div className="toolbar-inline compact">
              <label className="editor-field small grow">
                <span>Nombre</span>
                <input value={nodeDraft.name} onChange={(event) => setNodeDraft((current) => ({ ...current, name: event.target.value, codeLanguage: detectLanguageFromName(event.target.value) }))} />
              </label>
              <label className="editor-field small">
                <span>Capa</span>
                <input value={nodeDraft.layerLabel} onChange={(event) => setNodeDraft((current) => ({ ...current, layerLabel: event.target.value, layer: slugify(event.target.value) || current.layer }))} />
              </label>
              <label className="editor-field small color-field">
                <span>Color</span>
                <input type="color" value={nodeDraft.color} onChange={(event) => setNodeDraft((current) => ({ ...current, color: event.target.value }))} />
              </label>
            </div>
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Persistencia</span>
            <div className="toolbar-inline">
              <button type="button" className="tool-button primary" onClick={handleSaveGraph} disabled={isSaving}>
                {isSaving ? "Guardando..." : dirty ? "Guardar cambios" : "Guardar estado"}
              </button>
              <span className={`dirty-pill ${dirty ? "is-dirty" : ""}`}>{dirty ? "hay cambios sin guardar" : "todo guardado"}</span>
            </div>
          </div>
        </div>
      </section>

      <AppRuntimeWorkbenches
        focusedProject={effectiveWorkspaceScene}
        editorJumpTarget={editorJumpTarget}
        editorExpanded={editorExpanded}
        onSceneFocus={focusWorkspaceScene}
        onWorkspaceClean={handleWorkspaceClean}
        onCyberlaceBlock={showCyberlaceBlockingAlert}
        onRepairPresenceStart={triggerRepairPresence}
        onToggleEditorExpanded={() => setEditorExpanded((current) => !current)}
      />

      <SectionDividerMenu id="map" label="07 Mapa" title="Mapa conceptual" />

      <main className="workspace-grid">
        <section id="architecture-map-section" className="map-panel">
          <div className="panel-header">
            <div>
              <h2>Mapa conceptual editable</h2>
              <p>Arrastra bloques, crea nodos, conecta programas y arma el ecosistema visual del proyecto.</p>
            </div>
            <div className="legend">
              <span><i className="legend-line reference" /> referencias</span>
              <span><i className="legend-line uses" /> usa/importa</span>
              <span><i className="legend-line socket" /> sincroniza</span>
            </div>
          </div>

          <ArchitectureCanvas
            graph={visibleGraph}
            selectedNodeId={selectedId}
            selectedEdgeId={selectedEdgeId}
            mapTool={mapTool}
            edgeType={edgeType}
            layerOrder={orderedLayers}
            nodeIssuesById={lintIssueMaps.nodeIssuesById}
            onSelectNode={(nodeId) => {
              setSelectedId(nodeId);
              setSelectedEdgeId(null);
            }}
            onSelectEdge={(edgeId) => {
              setSelectedEdgeId(edgeId);
            }}
            onAddNode={handleAddNode}
            onMoveNode={handleMoveNode}
            onAddEdge={handleAddEdge}
            onIssueClick={handleIssueNavigation}
          />
        </section>

        <aside className="inspector">
          <div className="panel-header compact">
            <h2>Inspector y codigo</h2>
          </div>

          {selectedNode ? (
            <div className="inspector-body">
              <span className={`layer-badge ${selectedNode.layer}`}>{selectedNode.layerLabel || selectedNode.layer}</span>
              {isReadOnlyNode ? <span className="meta-pill">Analisis de solo lectura</span> : null}
              <h3>{selectedNode.name}</h3>
              {isReadOnlyNode && selectedNode.sourcePath ? <code className="lint-path">{selectedNode.sourcePath}</code> : null}

              <label className="editor-field">
                <span>Nombre del bloque</span>
                <input value={selectedNode.name} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("name", event.target.value)} />
              </label>

              <label className="editor-field">
                <span>{isReadOnlyNode ? "Ruta fuente real" : "Path / identificador"}</span>
                <input value={isReadOnlyNode ? selectedNode.sourcePath || selectedNode.path : selectedNode.path} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("path", event.target.value)} />
              </label>

              <div className="editor-two-columns">
                <label className="editor-field">
                  <span>Capa</span>
                  <input value={selectedNode.layerLabel || selectedNode.layer} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("layerLabel", event.target.value)} />
                </label>
                <label className="editor-field">
                  <span>Estado</span>
                  <select value={selectedNode.status} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("status", event.target.value)}>
                    <option value="generated">generated</option>
                    <option value="modified">modified</option>
                    <option value="isolated">isolated</option>
                  </select>
                </label>
              </div>

              <div className="editor-two-columns">
                <label className="editor-field color-field">
                  <span>Color</span>
                  <input type="color" value={selectedNode.color || "#60a5fa"} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("color", event.target.value)} />
                </label>
                <label className="editor-field">
                  <span>Lenguaje</span>
                  <input value={selectedNode.codeLanguage} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("codeLanguage", event.target.value)} />
                </label>
              </div>

              <label className="editor-field">
                <span>Descripcion</span>
                <textarea rows={3} value={selectedNode.description} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("description", event.target.value)} />
              </label>

              <label className="editor-field">
                <span>Codigo del bloque / archivo</span>
                <textarea className="code-editor" rows={14} value={selectedNode.code} disabled={isReadOnlyNode} onChange={(event) => updateSelectedNodeField("code", event.target.value)} />
              </label>

              <div className="inspector-action-row">
                <span className="node-stats">{formatStatus(selectedNode.status)} · {selectedNode.lines} lineas · {selectedNode.layerLabel}</span>
                <button type="button" className="tool-button danger" disabled={isReadOnlyNode} onClick={deleteSelectedNode}>Eliminar bloque</button>
              </div>

              {selectedEdge ? (
                <div className="inspector-subpanel">
                  <h4>Flecha seleccionada</h4>
                  <label className="editor-field">
                    <span>Etiqueta de la flecha</span>
                    <input value={selectedEdge.label || ""} disabled={isReadOnlyNode} onChange={(event) => updateSelectedEdgeField("label", event.target.value)} />
                  </label>
                  <label className="editor-field">
                    <span>Tipo</span>
                    <select value={selectedEdge.type} disabled={isReadOnlyNode} onChange={(event) => updateSelectedEdgeField("type", event.target.value)}>
                      {EDGE_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
                    </select>
                  </label>
                  <button type="button" className="tool-button danger" disabled={isReadOnlyNode} onClick={deleteSelectedEdge}>Eliminar flecha</button>
                </div>
              ) : null}

              {selectedStep ? (
                <div className="inspector-subpanel">
                  <h4>Bloque interno del flujo</h4>

                  <label className="editor-field">
                    <span>Etiqueta del paso</span>
                    <textarea rows={3} value={selectedStep.label} disabled={isReadOnlyNode} onChange={(event) => updateSelectedStepField("label", event.target.value)} />
                  </label>

                  <div className="editor-two-columns">
                    <label className="editor-field">
                      <span>Tipo</span>
                      <select value={selectedStep.type} disabled={isReadOnlyNode} onChange={(event) => updateSelectedStepField("type", event.target.value)}>
                        <option value="start">start</option>
                        <option value="process">process</option>
                        <option value="decision">decision</option>
                        <option value="io">io</option>
                        <option value="end">end</option>
                      </select>
                    </label>
                    <label className="editor-field">
                      <span>Lenguaje</span>
                      <input value={selectedStep.codeLanguage || ""} disabled={isReadOnlyNode} onChange={(event) => updateSelectedStepField("codeLanguage", event.target.value)} />
                    </label>
                  </div>

                  <label className="editor-field color-field">
                    <span>Color del paso</span>
                    <input type="color" value={selectedStep.color || "#ccf7cf"} disabled={isReadOnlyNode} onChange={(event) => updateSelectedStepField("color", event.target.value)} />
                  </label>

                  <label className="editor-field">
                    <span>Codigo interno de la clase/funcion/metodo/evento</span>
                    <textarea className="code-editor" rows={12} value={selectedStep.code || ""} disabled={isReadOnlyNode} onChange={(event) => updateSelectedStepField("code", event.target.value)} />
                  </label>

                  <button type="button" className="tool-button danger" disabled={isReadOnlyNode} onClick={deleteSelectedStep}>Eliminar bloque interno</button>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="empty-state">Selecciona un bloque en el mapa para editarlo.</p>
          )}
        </aside>
      </main>

      <SectionDividerMenu id="flow" label="08 Flujo" title="Flujo" />

      <section id="algorithm-flow-section" className="algorithm-panel">
        <div className="panel-header compact">
          <div>
            <h2>Editor del diagrama de flujo</h2>
            <p>Crea mas bloques internos al lado, arrastralos y conectalos como subclases, funciones, eventos o metodos.</p>
          </div>
        </div>

        <div className="sequence-toolbar">
          <div className="sequence-actions">
            <button type="button" className="tool-button primary" onClick={handleStartSequence} disabled={!selectedNode}>
              Iniciar secuencia
            </button>
            <button
              type="button"
              className="tool-button"
              onClick={() => moveSequenceCursor(sequenceCursor - 1)}
              disabled={!isSequenceMode || sequenceCursor === 0}
            >
              Bloque anterior
            </button>
            <button
              type="button"
              className="tool-button"
              onClick={() => moveSequenceCursor(sequenceCursor + 1)}
              disabled={!isSequenceMode || sequenceCursor >= (sequencePlan?.nodeIds?.length || 0) - 1}
            >
              Siguiente bloque
            </button>
            <button
              type="button"
              className="tool-button"
              onClick={() => moveSequenceCursor(0)}
              disabled={!isSequenceMode}
            >
              Reiniciar
            </button>
            <button type="button" className="tool-button" onClick={handleExitSequence} disabled={!isSequenceMode}>
              Salir secuencia
            </button>
          </div>

          <div className="sequence-status">
            {isSequenceMode ? (
              <>
                <strong>{sequencePlan?.label || "Proyecto activo"}</strong>
                <span>{sequenceCursor + 1} de {sequencePlan?.nodeIds?.length || 0} bloques visibles</span>
                <small>Vista encadenada en modo lectura. El inspector sigue el bloque activo.</small>
              </>
            ) : (
              <>
                <strong>Secuencia completa del proyecto</strong>
                <span>Empieza desde el proyecto del bloque seleccionado y une los algoritmos con flechas puente.</span>
              </>
            )}
          </div>
        </div>

        <div className="flow-toolbar">
          {FLOW_BUTTONS.map((item) => (
            <button
              key={item.value}
              type="button"
              className={`tool-button ${flowTool === item.value ? "active" : ""}`}
              disabled={isSequenceMode || isReadOnlyNode}
              onClick={() => setFlowTool(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {selectedNode ? (
          <AlgorithmFlow
            algorithm={selectedNode.algorithm}
            nodeName={selectedNode.name}
            nodeId={selectedNode.id}
            readOnly={isReadOnlyNode}
            selectedStepId={selectedStepId}
            flowTool={flowTool}
            sequenceMode={isSequenceMode}
            sequenceBlocks={sequenceBlocks}
            sequenceTransitions={sequenceTransitions}
            activeSequenceNodeId={activeSequenceNodeId}
            sequenceLabel={sequencePlan?.label || selectedNode.workspaceSceneLabel || selectedNode.name}
            stepIssuesByNodeId={lintIssueMaps.stepIssuesByNodeId}
            nodeIssuesById={lintIssueMaps.nodeIssuesById}
            onSelectStep={setSelectedStepId}
            onMoveStep={handleMoveStep}
            onAddStep={handleAddStep}
            onAddStepEdge={handleAddStepEdge}
            onIssueClick={handleIssueNavigation}
          />
        ) : (
          <p className="empty-state algorithm-fallback">Selecciona un bloque para editar su flujo interno.</p>
        )}

        <div className={`algorithm-sandbox-panel ${embeddedSandboxOpen && embeddedSandboxUrl ? "is-open" : ""}`}>
          <div className="algorithm-sandbox-header">
            <div className="algorithm-sandbox-title">
              <span className="toolbar-label">Sandbox interno</span>
              <strong>{embeddedSandboxReady ? "Aplicacion generada en vivo" : embeddedSandbox.running ? "Sandbox arrancando" : "Sandbox detenido"}</strong>
              <code>{embeddedSandboxUrl || embeddedSandboxLabel}</code>
            </div>
            <div className="toolbar-inline compact">
              <span className={`socket-pill ${embeddedSandboxReady ? "is-online" : "is-offline"}`}>
                {embeddedSandboxReady ? "ready=true" : "ready=false"}
              </span>
              <button
                type="button"
                className="tool-button primary"
                onClick={() => startEmbeddedSandbox()}
                disabled={!effectiveWorkspaceScene || viewAllWorkspaceScenes || embeddedSandboxBusy}
              >
                {embeddedSandboxBusy ? "Procesando..." : embeddedSandbox.running ? "Reiniciar sandbox" : "Arrancar sandbox"}
              </button>
              <button
                type="button"
                className="tool-button"
                onClick={() => setEmbeddedSandboxOpen((current) => !current)}
                disabled={!embeddedSandboxUrl}
              >
                {embeddedSandboxOpen ? "Ocultar visor" : "Ver aqui"}
              </button>
              <button
                type="button"
                className="tool-button"
                onClick={() => setEmbeddedSandboxFrameKey((current) => current + 1)}
                disabled={!embeddedSandboxUrl || !embeddedSandboxOpen}
              >
                Recargar
              </button>
              <button
                type="button"
                className="tool-button danger"
                onClick={() => stopEmbeddedSandbox()}
                disabled={!embeddedSandbox.running || embeddedSandboxBusy}
              >
                Detener
              </button>
            </div>
          </div>

          {embeddedSandboxError ? <p className="agent-error">{embeddedSandboxError}</p> : null}

          {embeddedSandboxOpen && embeddedSandboxUrl ? (
            <div className="algorithm-sandbox-frame-shell">
              <iframe
                key={`${embeddedSandboxUrl}-${embeddedSandboxFrameKey}`}
                title={`Sandbox interno ${embeddedSandboxLabel}`}
                src={embeddedSandboxUrl}
                sandbox="allow-forms allow-modals allow-pointer-lock allow-popups allow-same-origin allow-scripts"
              />
            </div>
          ) : (
            <div className="algorithm-sandbox-empty">
              <span>{effectiveWorkspaceScene && !viewAllWorkspaceScenes ? "Arranca el sandbox para ver la app generada aqui." : "Selecciona un proyecto para abrir su sandbox."}</span>
            </div>
          )}
        </div>
      </section>

      <SectionDividerMenu id="layers" label="09 Capas" title="Capas" />

      <section id="layers-section" className="lanes-panel">
        <div className="panel-header compact">
          <h2>Vista por capas</h2>
          <p>Cada capa representa un programa o una zona del ecosistema.</p>
        </div>

        <div className="lanes-grid">
          {orderedLayers.map((layer) => (
            <article key={layer} className="lane">
              <header>
                <span className={`layer-dot ${layer}`} style={{ background: defaultColorForLayer(layer) }} />
                <strong>{nodesByLayer[layer]?.[0]?.layerLabel || titleizeLayer(layer)}</strong>
                <small>{nodesByLayer[layer]?.length || 0} bloque(s)</small>
              </header>

              {nodesByLayer[layer]?.length ? (
                nodesByLayer[layer].map((node) => (
                  <button
                    type="button"
                    key={node.id}
                    className={`lane-card ${selectedNode?.id === node.id ? "selected" : ""}`}
                    onClick={() => {
                      setSelectedId(node.id);
                      setSelectedEdgeId(null);
                    }}
                  >
                    <span>{node.name}</span>
                    <small>{node.path}</small>
                  </button>
                ))
              ) : (
                <div className="lane-empty">Sin bloques</div>
              )}
            </article>
          ))}
        </div>
      </section>

      <AppStatusbar graph={graph} mapTool={mapTool} flowTool={flowTool} />
      <WelcomeAuthGate apiBaseUrl={SOCKET_URL} logoSrc={HABLA_OBSERVER_LOGO_SRC} />
    </div>
  );
}
