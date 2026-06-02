const pipeline = [
  {
    title: "Entrada redactada",
    detail: "El flujo recibe solo campos sinteticos y textos saneados.",
    status: "aislado",
    color: "#2e6f8f"
  },
  {
    title: "Normalizacion",
    detail: "Los identificadores sensibles se reemplazan por tokens publicos.",
    status: "limpio",
    color: "#b56b16"
  },
  {
    title: "Validacion",
    detail: "La evidencia se valida por archivos y render real de navegador.",
    status: "activo",
    color: "#2f7d58"
  },
  {
    title: "Cierre bloqueable",
    detail: "El cierre depende de pruebas y no de memoria implicita.",
    status: "verificado",
    color: "#b6423c"
  }
];

const records = [
  ["frontend/index.html", "pantalla", "presente"],
  ["frontend/styles.css", "estilos", "presente"],
  ["frontend/app.js", "logica", "presente"],
  ["secrets", "datos reales", "no usados"]
];

const state = {
  distance: 128,
  speed: 14,
  frame: 0,
  light: "day"
};

function qs(name) {
  return new URLSearchParams(window.location.search).get(name);
}

function setHud() {
  const mode = qs("mode") || "smoke";
  document.getElementById("distance-value").textContent = `${state.distance} m`;
  document.getElementById("speed-value").textContent = `${state.speed} m/s`;
  document.getElementById("mode-value").textContent = mode;
  document.getElementById("event-value").textContent = "fallback-2d listo";
}

function renderPipeline() {
  const list = document.getElementById("pipeline-list");
  list.innerHTML = "";
  pipeline.forEach((item) => {
    const row = document.createElement("article");
    row.className = "pipeline-item";

    const marker = document.createElement("span");
    marker.className = "pipeline-marker";
    marker.style.background = item.color;

    const copy = document.createElement("div");
    const title = document.createElement("h3");
    const detail = document.createElement("p");
    title.textContent = item.title;
    detail.textContent = item.detail;
    copy.append(title, detail);

    const badge = document.createElement("span");
    badge.className = "pipeline-badge";
    badge.textContent = item.status;

    row.append(marker, copy, badge);
    list.append(row);
  });
}

function renderRecords() {
  const table = document.getElementById("records-table");
  table.innerHTML = "";
  records.forEach(([artifact, type, status]) => {
    const row = document.createElement("tr");
    [artifact, type, status].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    table.append(row);
  });
}

function fitCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(640, Math.floor(rect.width * ratio));
  canvas.height = Math.max(420, Math.floor(rect.height * ratio));
  return ratio;
}

function drawWorld() {
  const canvas = document.getElementById("world");
  canvas.dataset.renderMode = "fallback-2d";
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    document.getElementById("event-value").textContent = "canvas no disponible";
    return;
  }

  const ratio = fitCanvas(canvas);
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.scale(ratio, ratio);

  const logicalWidth = width / ratio;
  const logicalHeight = height / ratio;
  ctx.fillStyle = state.light === "day" ? "#e8ede4" : "#d9e0d5";
  ctx.fillRect(0, 0, logicalWidth, logicalHeight);

  ctx.strokeStyle = "rgba(23, 32, 27, 0.12)";
  ctx.lineWidth = 1;
  for (let x = 40; x < logicalWidth; x += 80) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, logicalHeight);
    ctx.stroke();
  }
  for (let y = 40; y < logicalHeight; y += 80) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(logicalWidth, y);
    ctx.stroke();
  }

  const nodes = pipeline.map((item, index) => ({
    ...item,
    x: 120 + index * ((logicalWidth - 240) / Math.max(1, pipeline.length - 1)),
    y: logicalHeight * 0.42 + Math.sin((state.frame + index * 18) / 24) * 18
  }));

  ctx.lineWidth = 5;
  ctx.strokeStyle = "#2e6f8f";
  ctx.beginPath();
  nodes.forEach((node, index) => {
    if (index === 0) ctx.moveTo(node.x, node.y);
    else ctx.lineTo(node.x, node.y);
  });
  ctx.stroke();

  nodes.forEach((node, index) => {
    ctx.fillStyle = node.color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, 30, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.font = "700 18px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(index + 1), node.x, node.y);

    ctx.fillStyle = "#17201b";
    ctx.font = "700 14px system-ui, sans-serif";
    ctx.fillText(node.title, node.x, node.y + 52);
  });

  ctx.fillStyle = "rgba(255, 255, 255, 0.86)";
  ctx.fillRect(28, 28, 300, 92);
  ctx.fillStyle = "#17201b";
  ctx.font = "800 20px system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("Arquitectura segura", 48, 64);
  ctx.font = "500 14px system-ui, sans-serif";
  ctx.fillStyle = "#667067";
  ctx.fillText("Sin credenciales, sin bypasses, sin datos reales", 48, 92);
}

function tick() {
  state.frame += 1;
  state.distance += 3;
  state.speed = 14 + (state.frame % 5);
  setHud();
  drawWorld();
  window.requestAnimationFrame(tick);
}

function bindControls() {
  document.querySelector("[data-action='rerun']").addEventListener("click", () => {
    state.distance += 17;
    state.speed = 18;
    setHud();
    drawWorld();
  });

  document.querySelector("[data-action='toggle']").addEventListener("click", () => {
    state.light = state.light === "day" ? "night" : "day";
    document.body.classList.toggle("theme-night", state.light === "night");
    drawWorld();
  });

  window.addEventListener("resize", drawWorld);
}

function init() {
  renderPipeline();
  renderRecords();
  setHud();
  bindControls();
  drawWorld();
  window.requestAnimationFrame(tick);
}

document.addEventListener("DOMContentLoaded", init);
