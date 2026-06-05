(function () {
  "use strict";

  const canvas = document.getElementById("world");
  const ctx = canvas.getContext("2d");
  const hud = {
    time: document.getElementById("time"),
    energy: document.getElementById("energy"),
    speed: document.getElementById("speed-value"),
    distance: document.getElementById("distance-value"),
    checkpoints: document.getElementById("checkpoints"),
    status: document.getElementById("status"),
    eventLog: document.getElementById("event-value"),
    restart: document.getElementById("restart"),
  };

  const world = {
    width: 2200,
    height: 1500,
    checkpoints: [
      { x: 390, y: 1180, active: false },
      { x: 1030, y: 820, active: false },
      { x: 1660, y: 430, active: false },
    ],
    goal: { x: 2030, y: 210, r: 72 },
    energyCells: [
      { x: 720, y: 1160, active: true },
      { x: 1360, y: 710, active: true },
      { x: 1820, y: 290, active: true },
    ],
    walls: [
      { x: 0, y: 0, w: 2200, h: 38 },
      { x: 0, y: 1462, w: 2200, h: 38 },
      { x: 0, y: 0, w: 38, h: 1500 },
      { x: 2162, y: 0, w: 38, h: 1500 },
      { x: 210, y: 220, w: 1150, h: 44 },
      { x: 360, y: 390, w: 44, h: 740 },
      { x: 520, y: 1080, w: 890, h: 44 },
      { x: 700, y: 470, w: 44, h: 470 },
      { x: 700, y: 470, w: 610, h: 44 },
      { x: 1010, y: 650, w: 44, h: 430 },
      { x: 1210, y: 650, w: 660, h: 44 },
      { x: 1510, y: 260, w: 44, h: 430 },
      { x: 1380, y: 900, w: 560, h: 44 },
      { x: 1900, y: 430, w: 44, h: 520 },
      { x: 1180, y: 1240, w: 740, h: 44 },
    ],
    hazards: [
      { x: 560, y: 650, r: 34, phase: 0 },
      { x: 1180, y: 915, r: 42, phase: 2.1 },
      { x: 1710, y: 760, r: 38, phase: 4.2 },
    ],
    stars: [],
  };

  const state = {
    player: { x: 130, y: 1340, r: 22, vx: 0, vy: 0 },
    camera: { x: 0, y: 0 },
    keys: new Set(),
    energy: 100,
    startTime: performance.now(),
    elapsed: 0,
    status: "Explorando",
    event: "Inicio",
    won: false,
    lastHit: 0,
  };

  function resetGame() {
    state.player.x = 130;
    state.player.y = 1340;
    state.player.vx = 0;
    state.player.vy = 0;
    state.energy = 100;
    state.startTime = performance.now();
    state.elapsed = 0;
    state.status = "Explorando";
    state.event = "Inicio";
    state.won = false;
    state.lastHit = 0;
    world.checkpoints.forEach((checkpoint) => {
      checkpoint.active = false;
    });
    world.energyCells.forEach((cell) => {
      cell.active = true;
    });
  }

  function resize() {
    const ratio = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    const width = Math.floor(canvas.clientWidth * ratio);
    const height = Math.floor(canvas.clientHeight * ratio);
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function rectCircleCollides(rect, circle) {
    const nearestX = Math.max(rect.x, Math.min(circle.x, rect.x + rect.w));
    const nearestY = Math.max(rect.y, Math.min(circle.y, rect.y + rect.h));
    const dx = circle.x - nearestX;
    const dy = circle.y - nearestY;
    return dx * dx + dy * dy < circle.r * circle.r;
  }

  function moveAxis(axis, amount) {
    const player = state.player;
    const previous = axis === "x" ? player.x : player.y;
    player[axis] += amount;
    const blocked = world.walls.some((wall) => rectCircleCollides(wall, player));
    if (blocked) {
      player[axis] = previous;
      if (performance.now() - state.lastHit > 450) {
        state.energy = Math.max(0, state.energy - 4);
        state.event = "Colision con muro";
        state.lastHit = performance.now();
      }
    }
  }

  function distance(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function update(dt, now) {
    const player = state.player;
    let inputX = 0;
    let inputY = 0;
    if (state.keys.has("arrowleft") || state.keys.has("a")) inputX -= 1;
    if (state.keys.has("arrowright") || state.keys.has("d")) inputX += 1;
    if (state.keys.has("arrowup") || state.keys.has("w")) inputY -= 1;
    if (state.keys.has("arrowdown") || state.keys.has("s")) inputY += 1;

    const length = Math.hypot(inputX, inputY) || 1;
    const speed = state.energy > 0 && !state.won ? 245 : 0;
    player.vx += ((inputX / length) * speed - player.vx) * Math.min(1, dt * 10);
    player.vy += ((inputY / length) * speed - player.vy) * Math.min(1, dt * 10);
    moveAxis("x", player.vx * dt);
    moveAxis("y", player.vy * dt);

    if (!state.won) {
      state.energy = Math.max(0, state.energy - dt * 1.2);
    }

    world.hazards.forEach((hazard) => {
      const pulse = Math.sin(now / 420 + hazard.phase) * 12;
      if (distance(player, hazard) < player.r + hazard.r + pulse * 0.2 && now - state.lastHit > 450) {
        state.energy = Math.max(0, state.energy - 12);
        state.event = "Zona inestable";
        state.lastHit = now;
      }
    });

    world.energyCells.forEach((cell) => {
      if (cell.active && distance(player, cell) < player.r + 30) {
        cell.active = false;
        state.energy = Math.min(100, state.energy + 24);
        state.event = "Energia recuperada";
      }
    });

    world.checkpoints.forEach((checkpoint) => {
      if (!checkpoint.active && distance(player, checkpoint) < player.r + 38) {
        checkpoint.active = true;
        state.status = "Checkpoint activo";
        state.event = "Checkpoint activo";
      }
    });

    const activeCheckpoints = world.checkpoints.filter((checkpoint) => checkpoint.active).length;
    if (distance(player, world.goal) < player.r + world.goal.r && activeCheckpoints === world.checkpoints.length) {
      state.won = true;
      state.status = "Victoria";
      state.event = "Meta alcanzada";
    } else if (state.energy <= 0) {
      state.status = "Sin energia";
      state.event = "Sin energia";
    } else if (!state.won && state.status !== "Checkpoint activo") {
      state.status = "Explorando";
    }

    state.elapsed = Math.floor((now - state.startTime) / 1000);
    const viewWidth = canvas.clientWidth;
    const viewHeight = canvas.clientHeight;
    const targetX = Math.max(0, Math.min(world.width - viewWidth, player.x - viewWidth * 0.5));
    const targetY = Math.max(0, Math.min(world.height - viewHeight, player.y - viewHeight * 0.55));
    state.camera.x += (targetX - state.camera.x) * Math.min(1, dt * 4.5);
    state.camera.y += (targetY - state.camera.y) * Math.min(1, dt * 4.5);
  }

  function project(point, height) {
    const depth = 0.22;
    return {
      x: point.x - state.camera.x,
      y: point.y - state.camera.y - height * depth,
    };
  }

  function drawWall(wall) {
    const x = wall.x - state.camera.x;
    const y = wall.y - state.camera.y;
    const top = 18;
    const gradient = ctx.createLinearGradient(x, y - top, x, y + wall.h);
    gradient.addColorStop(0, "#4cd7ef");
    gradient.addColorStop(0.2, "#1f7f9d");
    gradient.addColorStop(1, "#14243c");
    ctx.fillStyle = gradient;
    ctx.fillRect(x, y - top, wall.w, wall.h + top);
    ctx.strokeStyle = "rgba(158, 238, 255, 0.38)";
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y - top, wall.w, wall.h + top);
  }

  function drawDisc(item, radius, fill, stroke) {
    const p = project(item, 14);
    ctx.beginPath();
    ctx.ellipse(p.x, p.y + radius * 0.52, radius * 1.1, radius * 0.34, 0, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 3;
    ctx.stroke();
  }

  function drawPlayer() {
    const player = state.player;
    const p = project(player, 24);
    const glow = ctx.createRadialGradient(p.x - 7, p.y - 9, 4, p.x, p.y, player.r + 14);
    glow.addColorStop(0, "#ffffff");
    glow.addColorStop(0.24, "#8af7ff");
    glow.addColorStop(1, "#1766ff");
    ctx.beginPath();
    ctx.ellipse(p.x, p.y + 24, player.r * 1.2, player.r * 0.36, 0, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(p.x, p.y, player.r, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();
    ctx.strokeStyle = "rgba(255, 255, 255, 0.84)";
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  function drawBackground(now) {
    const viewWidth = canvas.clientWidth;
    const viewHeight = canvas.clientHeight;
    const gradient = ctx.createLinearGradient(0, 0, viewWidth, viewHeight);
    gradient.addColorStop(0, "#080b17");
    gradient.addColorStop(0.45, "#111b2d");
    gradient.addColorStop(1, "#070912");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, viewWidth, viewHeight);

    ctx.save();
    ctx.globalAlpha = 0.72;
    world.stars.forEach((star) => {
      const x = (star.x - state.camera.x * star.depth) % viewWidth;
      const y = (star.y - state.camera.y * star.depth + Math.sin(now / 900 + star.x) * 2) % viewHeight;
      ctx.fillStyle = star.color;
      ctx.fillRect((x + viewWidth) % viewWidth, (y + viewHeight) % viewHeight, star.size, star.size);
    });
    ctx.restore();
  }

  function drawGrid() {
    ctx.save();
    ctx.translate(-state.camera.x % 80, -state.camera.y % 80);
    ctx.strokeStyle = "rgba(99, 233, 255, 0.08)";
    ctx.lineWidth = 1;
    for (let x = -80; x < canvas.clientWidth + 80; x += 80) {
      ctx.beginPath();
      ctx.moveTo(x, -80);
      ctx.lineTo(x, canvas.clientHeight + 80);
      ctx.stroke();
    }
    for (let y = -80; y < canvas.clientHeight + 80; y += 80) {
      ctx.beginPath();
      ctx.moveTo(-80, y);
      ctx.lineTo(canvas.clientWidth + 80, y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function render(now) {
    drawBackground(now);
    drawGrid();

    drawDisc(world.goal, world.goal.r, "rgba(114, 242, 168, 0.18)", "#72f2a8");
    world.checkpoints.forEach((checkpoint) => {
      drawDisc(
        checkpoint,
        checkpoint.active ? 30 : 24,
        checkpoint.active ? "rgba(114, 242, 168, 0.72)" : "rgba(255, 209, 102, 0.45)",
        checkpoint.active ? "#72f2a8" : "#ffd166"
      );
    });
    world.energyCells.forEach((cell) => {
      if (cell.active) drawDisc(cell, 22, "rgba(99, 233, 255, 0.72)", "#63e9ff");
    });
    world.hazards.forEach((hazard) => {
      const pulse = Math.sin(now / 420 + hazard.phase) * 8;
      drawDisc(hazard, hazard.r + pulse, "rgba(255, 107, 138, 0.56)", "#ff6b8a");
    });
    world.walls.forEach(drawWall);
    drawPlayer();
  }

  function updateHud() {
    const minutes = String(Math.floor(state.elapsed / 60)).padStart(2, "0");
    const seconds = String(state.elapsed % 60).padStart(2, "0");
    const activeCheckpoints = world.checkpoints.filter((checkpoint) => checkpoint.active).length;
    const speed = Math.round(Math.hypot(state.player.vx, state.player.vy));
    const distanceToGoal = Math.max(0, Math.round(distance(state.player, world.goal) - world.goal.r));
    hud.time.textContent = `${minutes}:${seconds}`;
    hud.energy.textContent = String(Math.round(state.energy));
    hud.speed.textContent = `${speed} u/s`;
    hud.distance.textContent = `${distanceToGoal} m`;
    hud.checkpoints.textContent = `${activeCheckpoints}/${world.checkpoints.length}`;
    hud.status.textContent = state.status;
    hud.eventLog.textContent = state.event;
  }

  function seedStars() {
    world.stars = Array.from({ length: 190 }, (_, index) => ({
      x: (index * 137.5) % 1700,
      y: (index * 73.3) % 920,
      depth: 0.12 + (index % 7) * 0.045,
      size: 1 + (index % 3) * 0.55,
      color: index % 5 === 0 ? "rgba(255, 209, 102, 0.9)" : "rgba(220, 247, 255, 0.82)",
    }));
  }

  let lastFrame = performance.now();
  function loop(now) {
    resize();
    const dt = Math.min(0.04, (now - lastFrame) / 1000);
    lastFrame = now;
    update(dt, now);
    render(now);
    updateHud();
    requestAnimationFrame(loop);
  }

  window.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    if (["arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d"].includes(key)) {
      event.preventDefault();
      state.keys.add(key);
    }
  });

  window.addEventListener("keyup", (event) => {
    state.keys.delete(event.key.toLowerCase());
  });

  hud.restart.addEventListener("click", resetGame);
  seedStars();
  resetGame();
  requestAnimationFrame(loop);
})();
