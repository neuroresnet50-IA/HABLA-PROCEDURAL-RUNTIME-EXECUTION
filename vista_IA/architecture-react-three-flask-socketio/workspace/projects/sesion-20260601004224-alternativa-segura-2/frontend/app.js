"use strict";

const state = {
  role: "auditor",
  filter: "all",
  mode: "build",
  redactions: 0,
  generatedAt: new Date("2026-06-01T22:26:48Z").toISOString(),
};

const tasks = [
  {
    id: "S01",
    title: "Planner",
    detail: "Alcance delimitado a frontend estatico y evidencia segura.",
    status: "ready",
  },
  {
    id: "S02",
    title: "Frontend",
    detail: "Interfaz runnable con mapa visual, controles y ledger sintetico.",
    status: "ready",
  },
  {
    id: "S03",
    title: "Backend",
    detail: "Sin cambios de runtime por propiedad del control-plane.",
    status: "ready",
  },
  {
    id: "S04",
    title: "QA Browser",
    detail: "Smoke visual esperado sobre HTML, CSS y JavaScript locales.",
    status: "ready",
  },
  {
    id: "S05",
    title: "Observer",
    detail: "Findings sin hallazgos activos; integrity pendiente de retry.",
    status: "blocked",
  },
  {
    id: "S06",
    title: "LACE Docs",
    detail: "Registro acotado a la tarea y evidencia verificable.",
    status: "ready",
  },
];

const policies = [
  {
    title: "Datos sinteticos",
    detail: "La pantalla no procesa informacion sensible local ni credenciales.",
    severity: "ok",
  },
  {
    title: "Acceso por rol",
    detail: "Viewer solo consulta; Auditor y Planner pueden generar informes.",
    severity: "ok",
  },
  {
    title: "Runtime protegido",
    detail: "Los archivos internos del control-plane quedan fuera del alcance del worker.",
    severity: "warning",
  },
  {
    title: "Evidencia real",
    detail: "La validacion se basa en archivos existentes y smoke browser.",
    severity: "ok",
  },
];

const ledger = [
  {
    time: "22:26",
    actor: "S01 Planner",
    event: "Se separo la alternativa segura del prompt bloqueado.",
    evidence: "scope-redacted-001",
    status: "ready",
  },
  {
    time: "22:28",
    actor: "S02 Frontend",
    event: "Se preparo UI estatica con datos sinteticos.",
    evidence: "frontend-build-002",
    status: "ready",
  },
  {
    time: "22:29",
    actor: "S05 Observer",
    event: "Findings activos en cero; integrity requiere retry.",
    evidence: "observer-compact-003",
    status: "blocked",
  },
  {
    time: "22:31",
    actor: "S06 LACE Docs",
    event: "Se registro ciclo acotado para la tarea actual.",
    evidence: "lace-log-004",
    status: "ready",
  },
];

const nodes = [
  { id: "index", label: "index.html", x: 0.17, y: 0.24, status: "ready" },
  { id: "styles", label: "styles.css", x: 0.48, y: 0.18, status: "ready" },
  { id: "app", label: "app.js", x: 0.76, y: 0.27, status: "ready" },
  { id: "findings", label: "findings", x: 0.28, y: 0.69, status: "ready" },
  { id: "integrity", label: "integrity", x: 0.64, y: 0.72, status: "blocked" },
];

const links = [
  ["index", "styles"],
  ["index", "app"],
  ["app", "findings"],
  ["app", "integrity"],
];

const permissions = {
  auditor: { label: "Auditor", canExport: true, canRedact: true },
  planner: { label: "Planner", canExport: true, canRedact: true },
  viewer: { label: "Viewer", canExport: false, canRedact: false },
};

const dom = {
  roleSelect: document.getElementById("roleSelect"),
  modePill: document.getElementById("modePill"),
  filesMetric: document.getElementById("filesMetric"),
  riskMetric: document.getElementById("riskMetric"),
  redactionMetric: document.getElementById("redactionMetric"),
  accessMetric: document.getElementById("accessMetric"),
  queueCount: document.getElementById("queueCount"),
  taskList: document.getElementById("taskList"),
  mapSummary: document.getElementById("mapSummary"),
  canvas: document.getElementById("world"),
  policySummary: document.getElementById("policySummary"),
  policyList: document.getElementById("policyList"),
  ledgerSummary: document.getElementById("ledgerSummary"),
  ledgerBody: document.getElementById("ledgerBody"),
  speedValue: document.getElementById("speed-value"),
  distanceValue: document.getElementById("distance-value"),
  eventValue: document.getElementById("event-value"),
  redactButton: document.getElementById("redactButton"),
  exportButton: document.getElementById("exportButton"),
  reportModal: document.getElementById("reportModal"),
  reportOutput: document.getElementById("reportOutput"),
  closeReport: document.getElementById("closeReport"),
};

function createEl(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== undefined) {
    element.textContent = text;
  }
  return element;
}

function getFilteredItems(items) {
  if (state.filter === "all") {
    return items;
  }
  return items.filter((item) => item.status === state.filter);
}

function renderMetrics() {
  const blockedCount = tasks.filter((task) => task.status === "blocked").length;
  const readyFiles = ["frontend/index.html", "frontend/styles.css", "frontend/app.js"];
  dom.filesMetric.textContent = `${readyFiles.length}/3`;
  dom.riskMetric.textContent = blockedCount > 0 ? "Medio" : "Bajo";
  dom.redactionMetric.textContent = String(state.redactions);
  dom.accessMetric.textContent = permissions[state.role].label;
  dom.modePill.textContent = `Mode: ${state.mode}`;
}

function renderTasks() {
  const filteredTasks = getFilteredItems(tasks);
  dom.queueCount.textContent = `${filteredTasks.length} tareas`;
  dom.taskList.replaceChildren();

  filteredTasks.forEach((task) => {
    const item = createEl("article", "task-item");
    const topline = createEl("div", "task-topline");
    topline.append(
      createEl("span", "task-title", `${task.id} ${task.title}`),
      createEl("span", `task-status ${task.status}`, task.status),
    );
    item.append(topline, createEl("p", "", task.detail));
    dom.taskList.append(item);
  });
}

function renderPolicies() {
  dom.policyList.replaceChildren();
  policies.forEach((policy) => {
    const item = createEl("li", policy.severity === "warning" ? "policy-item warning" : "policy-item");
    item.append(createEl("strong", "", policy.title), createEl("span", "", policy.detail));
    dom.policyList.append(item);
  });
  dom.policySummary.textContent = permissions[state.role].canExport ? "Exportable" : "Lectura";
}

function renderLedger() {
  const filteredLedger = getFilteredItems(ledger);
  dom.ledgerBody.replaceChildren();
  filteredLedger.forEach((entry) => {
    const row = document.createElement("tr");
    [entry.time, entry.actor, entry.event, entry.evidence].forEach((value) => {
      row.append(createEl("td", "", value));
    });
    const statusCell = createEl("td");
    statusCell.append(createEl("span", `state-dot ${entry.status}`, entry.status));
    row.append(statusCell);
    dom.ledgerBody.append(row);
  });
  dom.ledgerSummary.textContent = `${filteredLedger.length} eventos visibles para ${permissions[state.role].label}.`;
}

function renderControls() {
  const permission = permissions[state.role];
  dom.redactButton.disabled = !permission.canRedact;
  dom.exportButton.disabled = !permission.canExport;
  dom.redactButton.title = permission.canRedact ? "" : "Rol sin permiso de redaccion";
  dom.exportButton.title = permission.canExport ? "" : "Rol sin permiso de informe";
}

function renderHud() {
  const visibleNodes = getFilteredItems(nodes).length;
  const visibleLedger = getFilteredItems(ledger).length;
  const speed = Math.max(12, visibleLedger * 6);
  dom.speedValue.textContent = `${speed} m/s`;
  dom.distanceValue.textContent = `${visibleNodes} nodos / 3 archivos`;
  dom.eventValue.textContent = state.filter === "blocked" ? "fallback-2d blocked view" : "fallback-2d ready";
}

function drawCanvas() {
  const canvas = dom.canvas;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(320, Math.floor(rect.width));
  const height = Math.max(300, Math.floor(rect.height));
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const activeNodes = getFilteredItems(nodes);
  const byId = new Map(activeNodes.map((node) => [node.id, node]));

  ctx.fillStyle = "#f8fbfa";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#d9e2dd";
  ctx.lineWidth = 1;
  for (let i = 0; i < width; i += 38) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, height);
    ctx.stroke();
  }
  for (let i = 0; i < height; i += 38) {
    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(width, i);
    ctx.stroke();
  }

  links.forEach(([fromId, toId]) => {
    const from = byId.get(fromId);
    const to = byId.get(toId);
    if (!from || !to) {
      return;
    }
    ctx.beginPath();
    ctx.moveTo(from.x * width, from.y * height);
    ctx.lineTo(to.x * width, to.y * height);
    ctx.strokeStyle = "#8ea19a";
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  activeNodes.forEach((node) => {
    const x = node.x * width;
    const y = node.y * height;
    const radius = 30;
    const fill = node.status === "blocked" ? "#f8dedd" : "#dff5ec";
    const stroke = node.status === "blocked" ? "#ad3535" : "#176f53";

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.fillStyle = "#17201d";
    ctx.font = "700 13px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(node.label, x, y + radius + 22);
  });

  dom.mapSummary.textContent = `${activeNodes.length} nodos`;
}

function buildReport() {
  return {
    projectSlug: "sesion-20260601004224-alternativa-segura-2",
    generatedAt: new Date().toISOString(),
    mode: state.mode,
    role: state.role,
    dataSource: "synthetic",
    sensitiveLocalProcessing: false,
    expectedFiles: ["frontend/index.html", "frontend/styles.css", "frontend/app.js"],
    visibleTasks: getFilteredItems(tasks).map((task) => ({
      id: task.id,
      title: task.title,
      status: task.status,
    })),
    visibleLedger: getFilteredItems(ledger).map((entry) => ({
      time: entry.time,
      actor: entry.actor,
      event: entry.event,
      evidence: `[redacted:${entry.evidence.slice(-3)}]`,
      status: entry.status,
    })),
  };
}

function openReport() {
  if (!permissions[state.role].canExport) {
    return;
  }
  dom.reportOutput.textContent = JSON.stringify(buildReport(), null, 2);
  if (typeof dom.reportModal.showModal === "function") {
    dom.reportModal.showModal();
  } else {
    dom.reportModal.setAttribute("open", "open");
  }
}

function closeReport() {
  if (typeof dom.reportModal.close === "function") {
    dom.reportModal.close();
  } else {
    dom.reportModal.removeAttribute("open");
  }
}

function redactVisibleEvidence() {
  if (!permissions[state.role].canRedact) {
    return;
  }
  state.redactions += getFilteredItems(ledger).length;
  render();
}

function render() {
  renderMetrics();
  renderTasks();
  renderPolicies();
  renderLedger();
  renderControls();
  renderHud();
  drawCanvas();
}

function bindEvents() {
  dom.roleSelect.addEventListener("change", (event) => {
    state.role = event.target.value;
    render();
  });

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      state.filter = button.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach((item) => {
        item.classList.toggle("active", item === button);
      });
      render();
    });
  });

  dom.redactButton.addEventListener("click", redactVisibleEvidence);
  dom.exportButton.addEventListener("click", openReport);
  dom.closeReport.addEventListener("click", closeReport);
  window.addEventListener("resize", drawCanvas);
}

bindEvents();
render();
