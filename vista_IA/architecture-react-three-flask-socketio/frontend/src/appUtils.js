export const DEV_FRONTEND_PORTS = new Set(["4173", "5173"]);
export const DEFAULT_BACKEND_PORT = String(import.meta.env.VITE_BACKEND_PORT || "5001");

export function resolveSocketUrl() {
  if (import.meta.env.VITE_SOCKET_URL) {
    return import.meta.env.VITE_SOCKET_URL;
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    const hostname = window.location.hostname || "127.0.0.1";
    const origin = window.location.origin || `${protocol}//${hostname}`;
    const port = String(window.location.port || "");
    if (DEV_FRONTEND_PORTS.has(port)) {
      return `${protocol}//${hostname}:${DEFAULT_BACKEND_PORT}`;
    }
    return origin;
  }

  return `http://127.0.0.1:${DEFAULT_BACKEND_PORT}`;
}

export const SOCKET_URL = resolveSocketUrl();
export const HABLA_OBSERVER_LOGO_SRC = "/assets/img/HABLA_Observer_IA_ojo_random_giro_guino_parpadeo.gif";
export const BASE_LAYER_ORDER = ["frontend", "backend", "data", "microservice", "shared", "docs", "style", "config", "script"];
export const EDGE_TYPES = ["uses", "socket", "reference", "import"];
export const FLOW_BUTTONS = [
  { value: "select", label: "Mover flujo" },
  { value: "connect", label: "Conectar flujo" },
  { value: "add-start", label: "Inicio" },
  { value: "add-process", label: "Proceso" },
  { value: "add-decision", label: "Decision" },
  { value: "add-io", label: "Entrada/Salida" },
  { value: "add-end", label: "Fin" },
];

export const AGENT_PRESENCE_ACTION_DELAYS_MS = [1200, 2200, 5000, 2600, 7400, 1800];
export const CLOSED_AGENT_VISUAL_OPS = new Set([
  "session_complete",
  "session_completed",
  "session_completed_with_warnings",
  "session_blocked",
  "session_failed",
  "session_stopped",
]);
export const EMPTY_EMBEDDED_SANDBOX = {
  status: "idle",
  running: false,
  ready: false,
  embedUrl: "",
  url: "",
  project: "",
  technology: "",
  logs: [],
};
export const AGENT_PRESENCE_STEPS = [
  {
    kind: "code-scan",
    area: "codigo",
    phase: "Observando codigo",
    detail: "barriendo lineas y rutas generadas",
    targetId: "code-workbench",
    mapScale: 1,
    flowScale: 1,
  },
  {
    kind: "map-zoom",
    area: "mapa",
    phase: "Zoom autonomo en mapa",
    detail: "acercando dependencias y nodos desconectados",
    targetId: "architecture-map-section",
    mapScale: 1.12,
    mapPanX: -18,
    mapPanY: 12,
    flowScale: 1,
  },
  {
    kind: "map-click",
    area: "mapa",
    phase: "Marcando nodo sospechoso",
    detail: "simulando foco/click visual sobre una conexion",
    targetId: "architecture-map-section",
    mapScale: 0.92,
    mapPanX: 22,
    mapPanY: -14,
    flowScale: 1,
  },
  {
    kind: "flow-zoom",
    area: "flujo",
    phase: "Zoom en diagrama de flujo",
    detail: "acercando decisiones y saltos de control",
    targetId: "algorithm-flow-section",
    mapScale: 1,
    flowScale: 1.14,
    flowPanX: -16,
    flowPanY: 18,
  },
  {
    kind: "flow-pan",
    area: "flujo",
    phase: "Moviendo algoritmo",
    detail: "recorriendo bloques internos y retornos",
    targetId: "algorithm-flow-section",
    mapScale: 1,
    flowScale: 0.94,
    flowPanX: 26,
    flowPanY: -12,
  },
  {
    kind: "page-scroll",
    area: "capas",
    phase: "Scroll de arquitectura",
    detail: "subiendo y bajando para comparar zonas",
    targetId: "layers-section",
    mapScale: 1,
    flowScale: 1,
  },
  {
    kind: "micro-modal",
    area: "capas",
    phase: "Consulta interna rapida",
    detail: "verificando contrato visual con el runtime",
    targetId: "layers-section",
    mapScale: 1,
    flowScale: 1,
    microMessage: "agente visual cruzando evidencia",
  },
];

export const EMPTY_GRAPH = {
  metadata: {
    projectName: "Architecture View",
    generatedCount: 0,
    connectionCount: 0,
    isolatedCount: 0,
    updatedAt: null,
  },
  nodes: [],
  edges: [],
};

export function buildLocalClearedGraph(projectName) {
  return {
    metadata: {
      ...EMPTY_GRAPH.metadata,
      projectName: projectName || EMPTY_GRAPH.metadata.projectName,
      note: "Vista limpiada localmente. El mapa global del backend no fue modificado.",
      updatedAt: new Date().toISOString(),
    },
    nodes: [],
    edges: [],
  };
}

export const EMPTY_LINT_REPORT = {
  generatedAt: null,
  scope: {
    scene: "",
    label: "Mapa completo",
  },
  summary: {
    error: 0,
    warning: 0,
    info: 0,
    total: 0,
  },
  findings: [],
};

export const SEQUENCE_EDGE_PRIORITY = {
  import: 0,
  uses: 1,
  socket: 2,
  reference: 3,
};

export const SEQUENCE_LAYER_PRIORITY = {
  frontend: 0,
  shared: 1,
  backend: 2,
  microservice: 3,
  data: 4,
  style: 5,
  config: 6,
  script: 7,
  docs: 8,
};

export function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function titleizeLayer(layer) {
  return String(layer || "script")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function defaultColorForLayer(layer) {
  return {
    frontend: "#a855f7",
    backend: "#f97316",
    data: "#fb7185",
    microservice: "#14b8a6",
    shared: "#38bdf8",
    docs: "#eab308",
    style: "#d946ef",
    config: "#f59e0b",
    script: "#ec4899",
  }[layer] || "#60a5fa";
}

export function detectLanguageFromName(name) {
  const extension = String(name || "").split(".").pop()?.toLowerCase();
  return {
    py: "python",
    js: "javascript",
    jsx: "jsx",
    ts: "typescript",
    tsx: "tsx",
    html: "html",
    css: "css",
    json: "json",
    cpp: "cpp",
    cc: "cpp",
    cxx: "cpp",
    h: "cpp",
    hpp: "cpp",
  }[extension] || "text";
}

export function formatStatus(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "validated" || normalized === "validado") return "Validado";
  if (normalized === "completed" || normalized === "completado") return "Completado";
  if (normalized === "failed" || normalized === "fallido") return "Fallido";
  if (normalized === "improving" || normalized === "mejorando") return "Mejorando";
  if (normalized === "analyzing" || normalized === "analizando") return "Analizando";
  if (normalized === "pending" || normalized === "pendiente") return "Pendiente";
  if (normalized === "modified" || normalized === "modificado") return "Modificado";
  if (normalized === "isolated" || normalized === "aislado") return "Aislado";
  return "Generado";
}

export function formatUpdatedAt(value) {
  if (!value) return "sin actualizacion";
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

export function formatLintSeverity(value) {
  return {
    error: "Error",
    warning: "Advertencia",
    info: "Info",
  }[String(value || "").toLowerCase()] || "Aviso";
}

export const STRUCTURAL_VISUAL_ISSUE_CODES = new Set([
  "algorithm_dead_end",
  "algorithm_unreachable_step",
  "incomplete_control_flow",
  "missing_dependency",
  "parse_failure",
  "type_resolution_failure",
  "unreachable_code",
  "unresolved_import",
]);

export function severityWeight(value) {
  return {
    error: 3,
    warning: 2,
    info: 1,
  }[String(value || "").toLowerCase()] || 0;
}

export function getFindingVisualSeverity(finding) {
  const rawSeverity = String(finding?.severity || "").toLowerCase();
  const rawCode = String(finding?.code || finding?.issueType || "").toLowerCase();
  if (rawSeverity === "error") return "error";
  if (STRUCTURAL_VISUAL_ISSUE_CODES.has(rawCode)) return "error";
  if (rawSeverity === "warning") return "warning";
  return "info";
}

export function emitWithAck(socket, event, payload, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    if (!socket?.connected) {
      reject(new Error("reverse_socket_disconnected"));
      return;
    }

    const timer = window.setTimeout(() => {
      reject(new Error("reverse_ack_timeout"));
    }, timeoutMs);

    socket.emit(event, payload, (response) => {
      window.clearTimeout(timer);
      if (response?.ok === false) {
        reject(new Error(response.message || response.error || "request_failed"));
        return;
      }
      resolve(response || { ok: true });
    });
  });
}

export function humanizeReverseError(error) {
  const message = String(error?.message || error || "request_failed");
  if (message === "reverse_socket_disconnected") return "el socket de ingenieria inversa esta desconectado";
  if (message === "reverse_ack_timeout") return "el analizador no respondio a tiempo";
  if (message === "missing_target_path") return "falta la ruta local a analizar";
  if (message === "missing_analysis_id") return "falta la escena a quitar";
  if (message === "target_not_found") return "la ruta indicada no existe";
  if (message === "analysis_failed") return "no fue posible construir la escena de analisis";
  if (message === "analysis_io_error") return "hubo un error de lectura al analizar la ruta";
  return message;
}

export function chooseRandom(values, fallback) {
  if (!values?.length) return fallback;
  return values[Math.floor(Math.random() * values.length)];
}

export function findAgentPresenceStepIndex(actionType, targetId) {
  const normalizedAction = String(actionType || "").trim();
  const normalizedTarget = String(targetId || "").trim();
  const directIndex = AGENT_PRESENCE_STEPS.findIndex((step) => step.kind === normalizedAction);
  if (directIndex >= 0) return directIndex;
  const targetIndex = AGENT_PRESENCE_STEPS.findIndex((step) => step.targetId === normalizedTarget);
  return targetIndex >= 0 ? targetIndex : 0;
}

export function parseWorkspaceEditorTarget(rawPath, fallbackProject = "") {
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

export function buildEmptyAlgorithm(name, language) {
  return {
    title: `Algoritmo editable de ${name}`,
    source: "editor",
    steps: [
      { id: "start", type: "start", label: "Inicio", x: 300, y: 70, code: "", codeLanguage: language, color: null },
      { id: "process-1", type: "process", label: "Bloque principal", x: 300, y: 220, code: "", codeLanguage: language, color: null },
      { id: "end", type: "end", label: "Fin", x: 300, y: 380, code: "", codeLanguage: language, color: null },
    ],
    edges: [
      { from: "start", to: "process-1", label: "" },
      { from: "process-1", to: "end", label: "" },
    ],
  };
}

export function ensureNode(node) {
  const layer = slugify(node.layer || "script") || "script";
  const codeLanguage = node.codeLanguage || detectLanguageFromName(node.name);
  const algorithm = node.algorithm?.steps?.length ? node.algorithm : buildEmptyAlgorithm(node.name, codeLanguage);
  return {
    ...node,
    layer,
    layerLabel: node.layerLabel || titleizeLayer(layer),
    color: node.color || defaultColorForLayer(layer),
    code: node.code || "",
    codeLanguage,
    algorithm: {
      ...algorithm,
      source: algorithm.source || "editor",
      title: algorithm.title || `Algoritmo editable de ${node.name}`,
      steps: algorithm.steps.map((step, index) => ({
        ...step,
        id: step.id || `step-${index + 1}`,
        code: step.code || "",
        codeLanguage: step.codeLanguage || codeLanguage,
        color: step.color || null,
      })),
      edges: (algorithm.edges || []).map((edge, index) => ({
        id: edge.id || `flow-edge-${index + 1}`,
        from: edge.from,
        to: edge.to,
        label: edge.label || "",
      })),
    },
  };
}

export function applyDefaultLayout(graph) {
  const uniqueLayers = [...new Set(graph.nodes.map((node) => ensureNode(node).layer))];
  const knownLayers = BASE_LAYER_ORDER.filter((layer) => uniqueLayers.includes(layer));
  const customLayers = uniqueLayers.filter((layer) => !knownLayers.includes(layer)).sort();
  const orderedLayers = [...knownLayers, ...customLayers];
  const layerX = new Map(orderedLayers.map((layer, index) => [layer, 220 + index * 320]));
  const layerCount = new Map();

  return {
    ...graph,
    nodes: graph.nodes.map((rawNode) => {
      const node = ensureNode(rawNode);
      if (node.position?.x != null && node.position?.y != null) return node;

      const layerIndex = layerCount.get(node.layer) || 0;
      layerCount.set(node.layer, layerIndex + 1);
      return {
        ...node,
        position: {
          x: layerX.get(node.layer) || 220,
          y: 180 + layerIndex * 180,
        },
      };
    }),
  };
}

export function computeGraphMetadata(graph) {
  const connectedIds = new Set();
  for (const edge of graph.edges) {
    connectedIds.add(edge.from);
    connectedIds.add(edge.to);
  }

  return {
    ...graph.metadata,
    generatedCount: graph.nodes.length,
    connectionCount: graph.edges.length,
    isolatedCount: graph.nodes.filter((node) => !connectedIds.has(node.id)).length,
    updatedAt: new Date().toISOString(),
  };
}

export function workspaceProjectFromPath(path) {
  const parts = String(path || "").replace(/\\/g, "/").split("/");
  if (parts.length >= 3 && parts[0] === "workspace" && parts[1] === "projects") {
    return parts[2];
  }
  return "";
}

export function isWorkspaceRuntimeInternalPath(path) {
  const parts = String(path || "").replace(/\\/g, "/").split("/");
  return parts.length >= 4
    && parts[0] === "workspace"
    && parts[1] === "projects"
    && (parts[3] === "runtime" || parts[3] === ".vista");
}

export function workspaceProjectKeyForNode(node) {
  const explicitProject = String(node?.workspaceProject || "").trim();
  if (explicitProject) return explicitProject;
  const sceneKey = String(node?.workspaceScene || "").trim();
  if (sceneKey) return sceneKey.split("/")[0];
  return workspaceProjectFromPath(node?.path);
}

export function sanitizeGraphForVisualScope(graph) {
  const nodes = (graph.nodes || []).filter((node) => !isWorkspaceRuntimeInternalPath(node.path));
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = (graph.edges || []).filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));
  const scenes = Array.isArray(graph.scenes)
    ? graph.scenes.filter((scene) => {
      const key = String(scene.key || scene.id || "");
      return !key.includes("/runtime") && !key.includes("/.vista");
    })
    : [];

  return {
    ...graph,
    nodes,
    edges,
    scenes,
  };
}

export function collectWorkspaceProjectScenes(graph) {
  const sceneMap = new Map();
  const scopedGraph = sanitizeGraphForVisualScope(graph);

  for (const node of scopedGraph.nodes) {
    const key = workspaceProjectKeyForNode(node);
    if (!key) continue;
    const current = sceneMap.get(key) || {
      key,
      label: titleizeLayer(key),
      count: 0,
    };
    current.count += 1;
    if (node.workspaceScene === key && node.workspaceSceneLabel) {
      current.label = node.workspaceSceneLabel;
    }
    sceneMap.set(key, current);
  }

  return [...sceneMap.values()].sort((left, right) => right.key.localeCompare(left.key));
}

export function filterGraphByScene(graph, sceneKey) {
  const scopedGraph = sanitizeGraphForVisualScope(graph);
  if (!sceneKey) return scopedGraph;

  const nodes = scopedGraph.nodes.filter((node) => node.workspaceScene === sceneKey);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = scopedGraph.edges.filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));
  const scenes = Array.isArray(scopedGraph.scenes) ? scopedGraph.scenes.filter((scene) => scene.key === sceneKey || scene.id === `scene:${sceneKey}`) : [];
  const filtered = {
    ...scopedGraph,
    nodes,
    edges,
    scenes,
    metadata: {
      ...graph.metadata,
      projectName: nodes[0]?.workspaceSceneLabel || graph.metadata?.projectName || sceneKey,
      note: `Vista filtrada a la escena ${nodes[0]?.workspaceSceneLabel || sceneKey}.`,
      updatedAt: graph.metadata?.updatedAt || new Date().toISOString(),
    },
  };
  return {
    ...filtered,
    metadata: computeGraphMetadata(filtered),
  };
}

export function createNodeFromDraft(draft, position) {
  const layer = slugify(draft.layer || draft.layerLabel || "programa") || "programa";
  const name = draft.name || "nuevo-bloque.js";
  const language = draft.codeLanguage || detectLanguageFromName(name);
  const path = draft.path || `virtual/${layer}/${name}`;
  const code = draft.code || "";

  return {
    id: `${slugify(name) || "bloque"}-${Date.now()}`,
    name,
    path,
    layer,
    layerLabel: draft.layerLabel || titleizeLayer(layer),
    status: "generated",
    size: "editor",
    lines: Math.max(1, code.split("\n").length),
    description: draft.description || "Bloque creado manualmente dentro del editor visual.",
    imports: [],
    dependents: [],
    position,
    color: draft.color || defaultColorForLayer(layer),
    code,
    codeLanguage: language,
    algorithm: buildEmptyAlgorithm(name, language),
  };
}

export function createProgramBundle(name, graph, selectedNode) {
  const label = name.trim() || `programa-${graph.nodes.length + 1}`;
  const layer = slugify(label) || `programa-${graph.nodes.length + 1}`;
  const color = defaultColorForLayer(layer);
  const maxX = graph.nodes.length ? Math.max(...graph.nodes.map((node) => Number(node.position?.x) || 0)) : 0;
  const baseX = maxX + 360;
  const baseY = 220;

  const programNodes = [
    {
      id: `${layer}-package`,
      name: "package.json",
      path: `${layer}/package.json`,
      layer,
      layerLabel: label,
      status: "generated",
      size: "editor",
      lines: 10,
      description: "Configuracion base del programa creado desde el editor.",
      imports: [],
      dependents: [],
      position: { x: baseX, y: baseY - 120 },
      color,
      codeLanguage: "json",
      code: `{\n  "name": "${layer}",\n  "version": "1.0.0"\n}`,
      algorithm: buildEmptyAlgorithm("package.json", "json"),
    },
    {
      id: `${layer}-main`,
      name: "main.js",
      path: `${layer}/src/main.js`,
      layer,
      layerLabel: label,
      status: "generated",
      size: "editor",
      lines: 8,
      description: "Entrada principal del programa lateral.",
      imports: [],
      dependents: [],
      position: { x: baseX - 140, y: baseY + 60 },
      color,
      codeLanguage: "javascript",
      code: `import { runService } from "./service.js";\n\nrunService();\n`,
      algorithm: buildEmptyAlgorithm("main.js", "javascript"),
    },
    {
      id: `${layer}-service`,
      name: "service.js",
      path: `${layer}/src/service.js`,
      layer,
      layerLabel: label,
      status: "generated",
      size: "editor",
      lines: 12,
      description: "Servicio central del programa creado manualmente.",
      imports: [],
      dependents: [],
      position: { x: baseX + 140, y: baseY + 60 },
      color,
      codeLanguage: "javascript",
      code: `export function runService() {\n  return "service-ready";\n}\n`,
      algorithm: buildEmptyAlgorithm("service.js", "javascript"),
    },
    {
      id: `${layer}-bridge`,
      name: "bridge.js",
      path: `${layer}/src/bridge.js`,
      layer,
      layerLabel: label,
      status: "generated",
      size: "editor",
      lines: 10,
      description: "Adaptador para conectar este programa con el ecosistema actual.",
      imports: [],
      dependents: [],
      position: { x: baseX, y: baseY + 240 },
      color,
      codeLanguage: "javascript",
      code: `export async function publishBridge() {\n  return fetch("/api/architecture");\n}\n`,
      algorithm: buildEmptyAlgorithm("bridge.js", "javascript"),
    },
  ];

  const edges = [
    { id: `edge-${layer}-package-main`, from: `${layer}-package`, to: `${layer}-main`, type: "import", label: "configura runtime", dashed: false },
    { id: `edge-${layer}-main-service`, from: `${layer}-main`, to: `${layer}-service`, type: "uses", label: "ejecuta servicio", dashed: false },
    { id: `edge-${layer}-service-bridge`, from: `${layer}-service`, to: `${layer}-bridge`, type: "reference", label: "prepara bridge", dashed: false },
  ];

  const targetNode =
    selectedNode
    || graph.nodes.find((node) => node.path === "backend/app.py")
    || graph.nodes.find((node) => node.layer === "backend")
    || graph.nodes[0];

  if (targetNode) {
    edges.push({
      id: `edge-${layer}-bridge-target`,
      from: `${layer}-bridge`,
      to: targetNode.id,
      type: "socket",
      label: "sincroniza ecosistema",
      dashed: false,
    });
  }

  return { nodes: programNodes, edges };
}

export function dedupeReferences(values) {
  return [...new Set((values || []).filter(Boolean))];
}

export function compareCanvasPosition(a, b) {
  const ay = Number(a?.position?.y) || 0;
  const by = Number(b?.position?.y) || 0;
  if (ay !== by) return ay - by;

  const ax = Number(a?.position?.x) || 0;
  const bx = Number(b?.position?.x) || 0;
  if (ax !== bx) return ax - bx;

  return String(a?.name || a?.id || "").localeCompare(String(b?.name || b?.id || ""), "es", { sensitivity: "base" });
}

export function isSequenceCandidate(node) {
  return Boolean(node?.algorithm?.steps?.length) && node.layer !== "docs";
}

export function scoreSequenceEntry(node, incomingCount, outgoingCount) {
  const path = String(node?.path || node?.name || "").toLowerCase();
  let score = 100;

  if (/index\.html$/.test(path)) score -= 70;
  if (/(^|\/)(main|app|server)\.(js|jsx|ts|tsx|py|cpp|cc|cxx)$/.test(path)) score -= 48;
  if (/(^|\/)app\.py$/.test(path)) score -= 36;
  if (node?.layer === "frontend") score -= 24;
  if (node?.layer === "backend") score -= 18;
  if (node?.layer === "microservice") score -= 14;
  if (node?.layer === "shared") score -= 8;
  if (node?.layer === "data") score += 14;
  if (node?.layer === "style") score += 10;
  if (node?.layer === "docs") score += 40;

  score += Math.min(incomingCount, 6) * 12;
  score -= Math.min(outgoingCount, 6) * 3;
  score += (Number(node?.position?.y) || 0) / 1000;
  score += (Number(node?.position?.x) || 0) / 10000;

  return score;
}

export function compareSequenceNodes(a, b, incomingCounts, outgoingCounts) {
  const scoreDiff = scoreSequenceEntry(
    a,
    incomingCounts.get(a.id) || 0,
    outgoingCounts.get(a.id) || 0
  ) - scoreSequenceEntry(
    b,
    incomingCounts.get(b.id) || 0,
    outgoingCounts.get(b.id) || 0
  );

  if (scoreDiff) return scoreDiff;

  const layerDiff = (SEQUENCE_LAYER_PRIORITY[a.layer] ?? 50) - (SEQUENCE_LAYER_PRIORITY[b.layer] ?? 50);
  if (layerDiff) return layerDiff;

  return compareCanvasPosition(a, b);
}

export function buildSequencePlan(graph, anchorNodeId) {
  const anchorNode = graph.nodes.find((node) => node.id === anchorNodeId);
  if (!anchorNode) return null;

  const scopeNodes = anchorNode.workspaceScene
    ? graph.nodes.filter((node) => node.workspaceScene === anchorNode.workspaceScene)
    : graph.nodes;

  const candidates = scopeNodes.filter(isSequenceCandidate);
  if (!candidates.length) return null;

  const nodeMap = new Map(candidates.map((node) => [node.id, node]));
  const scopeEdges = graph.edges.filter((edge) => nodeMap.has(edge.from) && nodeMap.has(edge.to));
  const incomingCounts = new Map(candidates.map((node) => [node.id, 0]));
  const outgoingCounts = new Map(candidates.map((node) => [node.id, 0]));
  const outgoingMap = new Map(candidates.map((node) => [node.id, []]));

  for (const edge of scopeEdges) {
    incomingCounts.set(edge.to, (incomingCounts.get(edge.to) || 0) + 1);
    outgoingCounts.set(edge.from, (outgoingCounts.get(edge.from) || 0) + 1);
    outgoingMap.get(edge.from)?.push(edge);
  }

  const orderedCandidates = [...candidates].sort((a, b) => compareSequenceNodes(a, b, incomingCounts, outgoingCounts));
  const rootNode = orderedCandidates[0];
  const visited = new Set();
  const orderedNodes = [];

  const visit = (node) => {
    if (!node || visited.has(node.id)) return;

    visited.add(node.id);
    orderedNodes.push(node);

    const outgoingEdges = [...(outgoingMap.get(node.id) || [])].sort((left, right) => {
      const priorityDiff = (SEQUENCE_EDGE_PRIORITY[left.type] ?? 10) - (SEQUENCE_EDGE_PRIORITY[right.type] ?? 10);
      if (priorityDiff) return priorityDiff;

      const leftNode = nodeMap.get(left.to);
      const rightNode = nodeMap.get(right.to);
      if (!leftNode || !rightNode) return 0;
      return compareSequenceNodes(leftNode, rightNode, incomingCounts, outgoingCounts);
    });

    for (const edge of outgoingEdges) {
      visit(nodeMap.get(edge.to));
    }
  };

  visit(rootNode);
  for (const node of orderedCandidates) {
    visit(node);
  }

  const nodeIds = orderedNodes.map((node) => node.id);
  const links = nodeIds.slice(0, -1).map((nodeId, index) => {
    const nextId = nodeIds[index + 1];
    const matchedEdge =
      scopeEdges.find((edge) => edge.from === nodeId && edge.to === nextId)
      || scopeEdges.find((edge) => edge.from === nextId && edge.to === nodeId)
      || null;

    return {
      fromNodeId: nodeId,
      toNodeId: nextId,
      label: matchedEdge?.label
        || (matchedEdge?.type === "socket"
          ? "sincroniza"
          : matchedEdge?.type === "import"
            ? "importa"
            : matchedEdge?.type === "reference"
              ? "referencia"
              : "continua"),
      type: matchedEdge?.type || "sequence",
    };
  });

  return {
    scene: anchorNode.workspaceScene || "",
    label: anchorNode.workspaceSceneLabel || anchorNode.workspaceScene || anchorNode.name || "proyecto",
    nodeIds,
    links,
  };
}

export function isEditableShortcutTarget(target) {
  const tagName = String(target?.tagName || "").toLowerCase();
  if (["input", "textarea", "select"].includes(tagName)) return true;
  if (target?.isContentEditable) return true;
  return Boolean(target?.closest?.('[contenteditable="true"], [role="textbox"], .code-workbench-editor'));
}
