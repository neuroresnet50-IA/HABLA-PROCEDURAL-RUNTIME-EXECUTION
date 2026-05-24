import { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";
import ArchitectureCanvas from "./components/ArchitectureCanvas.jsx";
import AlgorithmFlow from "./components/AlgorithmFlow.jsx";
import AppAgentPresenceLayer from "./components/AppAgentPresenceLayer.jsx";
import AppLintPanel from "./components/AppLintPanel.jsx";
import AppObserverPanel from "./components/AppObserverPanel.jsx";
import AppRuntimeWorkbenches from "./components/AppRuntimeWorkbenches.jsx";
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

export default function App() {
  const socketRef = useRef(null);
  const autonomousModeRef = useRef(false);
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

      <SectionDividerMenu id="runtime" label="01 Runtime" title="Runtime" />

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
