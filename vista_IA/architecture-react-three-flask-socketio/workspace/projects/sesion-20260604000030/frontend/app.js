(function () {
  "use strict";

  const canvas = document.getElementById("world");
  const speedValue = document.getElementById("speed-value");
  const distanceValue = document.getElementById("distance-value");
  const eventValue = document.getElementById("event-value");
  const aiPressure = document.getElementById("ai-pressure");

  const keys = new Set();
  const laneWidth = 2.35;
  const state = {
    speed: 48,
    distance: 0,
    playerLane: 0,
    playerX: 0,
    boost: 0,
    braking: 0,
    event: "piloto neural listo",
    lastEventAt: 0,
    rivals: [
      { lane: -1, targetLane: -1, z: -34, speed: 34, color: [0.95, 0.22, 0.17, 1], seed: 0.2 },
      { lane: 1, targetLane: 1, z: -62, speed: 39, color: [0.12, 0.58, 0.95, 1], seed: 1.8 },
      { lane: 0, targetLane: 0, z: -98, speed: 43, color: [0.98, 0.76, 0.23, 1], seed: 3.1 }
    ]
  };

  const controls = {
    left: document.getElementById("left-control"),
    right: document.getElementById("right-control"),
    boost: document.getElementById("boost-control"),
    brake: document.getElementById("brake-control")
  };

  function setEvent(message) {
    state.event = message;
    state.lastEventAt = performance.now();
    eventValue.textContent = message;
  }

  function updateHud() {
    speedValue.textContent = `${Math.round(state.speed)} m/s`;
    distanceValue.textContent = `${Math.floor(state.distance)} m`;
    eventValue.textContent = state.event;
    const pressure = Math.max(8, Math.min(100, 30 + state.rivals.reduce((score, rival) => score + Math.max(0, 72 + rival.z), 0) / 5));
    aiPressure.value = String(Math.round(pressure));
  }

  function bindInput() {
    const keyMap = { left: "a", right: "d", boost: "w", brake: "s" };

    window.addEventListener("keydown", (event) => {
      keys.add(event.key.toLowerCase());
      if (["arrowleft", "arrowright", "arrowup", "arrowdown", " "].includes(event.key.toLowerCase())) {
        event.preventDefault();
      }
    });
    window.addEventListener("keyup", (event) => keys.delete(event.key.toLowerCase()));

    const press = (name, active) => {
      const button = controls[name];
      if (active) {
        keys.add(keyMap[name]);
        button.classList.add("is-active");
      } else {
        keys.delete(keyMap[name]);
        button.classList.remove("is-active");
      }
    };

    const clearInputState = () => {
      keys.clear();
      Object.values(controls).forEach((button) => button.classList.remove("is-active"));
    };

    Object.entries(controls).forEach(([name, button]) => {
      button.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        if (button.setPointerCapture) {
          button.setPointerCapture(event.pointerId);
        }
        press(name, true);
      });
      button.addEventListener("pointerup", () => press(name, false));
      button.addEventListener("pointerleave", () => press(name, false));
      button.addEventListener("pointercancel", () => press(name, false));
      button.addEventListener("lostpointercapture", () => press(name, false));
    });

    window.addEventListener("blur", clearInputState);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        clearInputState();
      }
    });
  }

  function updateGame(dt) {
    const left = keys.has("a") || keys.has("arrowleft");
    const right = keys.has("d") || keys.has("arrowright");
    state.boost = keys.has("w") || keys.has("arrowup") ? 1 : 0;
    state.braking = keys.has("s") || keys.has("arrowdown") ? 1 : 0;

    if (left && !right) {
      state.playerLane = Math.max(-1, state.playerLane - 2.8 * dt);
    }
    if (right && !left) {
      state.playerLane = Math.min(1, state.playerLane + 2.8 * dt);
    }

    state.speed += (16 + state.boost * 26 - state.braking * 42 - state.speed * 0.18) * dt;
    state.speed = Math.max(18, Math.min(88, state.speed));
    state.distance += state.speed * dt;

    const targetX = state.playerLane * laneWidth;
    state.playerX += (targetX - state.playerX) * Math.min(1, dt * 8);

    state.rivals.forEach((rival, index) => {
      const closeToPlayer = rival.z > -42 && rival.z < -8;
      if (closeToPlayer && Math.abs(rival.lane - state.playerLane) < 0.45) {
        rival.targetLane = rival.lane <= 0 ? 1 : -1;
        setEvent("IA rival esquiva tu linea");
      } else if (Math.sin(state.distance * 0.018 + rival.seed) > 0.96) {
        rival.targetLane = Math.max(-1, Math.min(1, Math.round(Math.sin(state.distance * 0.01 + index) * 1.4)));
      }

      rival.lane += (rival.targetLane - rival.lane) * Math.min(1, dt * 2.6);
      rival.speed += ((42 + index * 4 + Math.sin(state.distance * 0.012 + rival.seed) * 9) - rival.speed) * dt;
      rival.z += (state.speed - rival.speed) * dt;

      const dx = rival.lane * laneWidth - state.playerX;
      if (rival.z > -3.8 && rival.z < 2.4 && Math.abs(dx) < 1.1) {
        state.speed = Math.max(22, state.speed - 28 * dt);
        rival.z -= 7 * dt;
        setEvent("contacto evitado por control neural");
      }

      if (rival.z > 12) {
        rival.z = -92 - Math.random() * 64;
        rival.targetLane = [-1, 0, 1][Math.floor(Math.random() * 3)];
        rival.lane = rival.targetLane;
        rival.speed = 34 + Math.random() * 18;
        setEvent("nuevo rival detectado");
      }
    });

    if (performance.now() - state.lastEventAt > 2600) {
      state.event = state.boost ? "turbo controlado por IA" : "trayectoria estable";
    }
    updateHud();
  }

  function initWebGl() {
    const gl = canvas.getContext("webgl", { antialias: true });
    if (!gl) {
      initFallback2d("fallback-2d");
      return;
    }

    canvas.dataset.renderMode = "webgl";
    const program = createProgram(gl);
    const geometry = createCubeGeometry(gl);
    const locations = {
      position: gl.getAttribLocation(program, "a_position"),
      matrix: gl.getUniformLocation(program, "u_matrix"),
      color: gl.getUniformLocation(program, "u_color")
    };

    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);

    let last = performance.now();

    function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      updateGame(dt);
      resizeCanvas(gl);
      renderWebGl(gl, program, geometry, locations);
      requestAnimationFrame(frame);
    }

    requestAnimationFrame(frame);
  }

  function createProgram(gl) {
    const vertex = `
      attribute vec3 a_position;
      uniform mat4 u_matrix;
      void main() {
        gl_Position = u_matrix * vec4(a_position, 1.0);
      }
    `;
    const fragment = `
      precision mediump float;
      uniform vec4 u_color;
      void main() {
        gl_FragColor = u_color;
      }
    `;
    const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertex);
    const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragment);
    const program = gl.createProgram();
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) || "No se pudo enlazar WebGL");
    }
    return program;
  }

  function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(shader) || "No se pudo compilar shader");
    }
    return shader;
  }

  function createCubeGeometry(gl) {
    const vertices = new Float32Array([
      -0.5, -0.5, 0.5, 0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, 0.5, 0.5,
      -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.5, -0.5, -0.5,
      -0.5, 0.5, -0.5, -0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, -0.5,
      -0.5, -0.5, -0.5, 0.5, -0.5, -0.5, 0.5, -0.5, 0.5, -0.5, -0.5, 0.5,
      0.5, -0.5, -0.5, 0.5, 0.5, -0.5, 0.5, 0.5, 0.5, 0.5, -0.5, 0.5,
      -0.5, -0.5, -0.5, -0.5, -0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.5, -0.5
    ]);
    const indices = new Uint16Array([
      0, 1, 2, 0, 2, 3,
      4, 5, 6, 4, 6, 7,
      8, 9, 10, 8, 10, 11,
      12, 13, 14, 12, 14, 15,
      16, 17, 18, 16, 18, 19,
      20, 21, 22, 20, 22, 23
    ]);
    const vertexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vertexBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    const indexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
    return { vertexBuffer, indexBuffer, indexCount: indices.length };
  }

  function renderWebGl(gl, program, geometry, locations) {
    gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
    gl.clearColor(0.45, 0.72, 0.84, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, geometry.vertexBuffer);
    gl.enableVertexAttribArray(locations.position);
    gl.vertexAttribPointer(locations.position, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, geometry.indexBuffer);

    const aspect = gl.canvas.width / Math.max(1, gl.canvas.height);
    const projection = mat4Perspective(Math.PI / 3.3, aspect, 0.1, 260);
    const view = mat4LookAt([state.playerX * 0.18, 5.4, 12.5], [state.playerX * 0.08, 0.35, -22], [0, 1, 0]);
    const vp = mat4Multiply(projection, view);
    const roadShift = state.distance % 10;

    drawBox(gl, locations, geometry, vp, [0, -0.25, -54], [11.2, 0.12, 150], [0.1, 0.13, 0.16, 1]);
    drawBox(gl, locations, geometry, vp, [-7.2, -0.18, -54], [3.6, 0.09, 150], [0.08, 0.38, 0.2, 1]);
    drawBox(gl, locations, geometry, vp, [7.2, -0.18, -54], [3.6, 0.09, 150], [0.08, 0.38, 0.2, 1]);
    drawBox(gl, locations, geometry, vp, [-5.72, 0.16, -54], [0.2, 0.42, 150], [0.85, 0.18, 0.14, 1]);
    drawBox(gl, locations, geometry, vp, [5.72, 0.16, -54], [0.2, 0.42, 150], [0.85, 0.18, 0.14, 1]);

    for (let z = -124; z < 18; z += 10) {
      const markerZ = z + roadShift;
      drawBox(gl, locations, geometry, vp, [-laneWidth / 2, 0.03, markerZ], [0.12, 0.08, 3.4], [0.95, 0.92, 0.7, 1]);
      drawBox(gl, locations, geometry, vp, [laneWidth / 2, 0.03, markerZ], [0.12, 0.08, 3.4], [0.95, 0.92, 0.7, 1]);
    }

    for (let z = -128; z < 18; z += 18) {
      const scenicZ = z + (state.distance % 18);
      const height = 1.4 + (Math.sin(z) + 1) * 1.1;
      drawBox(gl, locations, geometry, vp, [-9.1, height / 2, scenicZ], [0.9, height, 0.9], [0.14, 0.32, 0.24, 1]);
      drawBox(gl, locations, geometry, vp, [9.4, height / 2, scenicZ - 7], [1.1, height * 0.85, 1.1], [0.15, 0.28, 0.36, 1]);
    }

    drawCar(gl, locations, geometry, vp, state.playerX, 0.15, 2.2, [0.2, 0.92, 0.68, 1], state.playerLane * -0.06);
    state.rivals.forEach((rival) => {
      drawCar(gl, locations, geometry, vp, rival.lane * laneWidth, 0.15, rival.z, rival.color, 0);
    });
  }

  function drawCar(gl, locations, geometry, vp, x, y, z, color, yaw) {
    drawBox(gl, locations, geometry, vp, [x, y + 0.42, z], [1.35, 0.58, 2.05], color, yaw);
    drawBox(gl, locations, geometry, vp, [x, y + 0.86, z - 0.2], [0.78, 0.48, 0.9], [0.07, 0.11, 0.15, 1], yaw);
    drawBox(gl, locations, geometry, vp, [x, y + 0.7, z - 1.08], [1.08, 0.16, 0.18], [1, 0.95, 0.55, 1], yaw);
    drawBox(gl, locations, geometry, vp, [x - 0.78, y + 0.16, z - 0.68], [0.22, 0.32, 0.5], [0.02, 0.025, 0.03, 1], yaw);
    drawBox(gl, locations, geometry, vp, [x + 0.78, y + 0.16, z - 0.68], [0.22, 0.32, 0.5], [0.02, 0.025, 0.03, 1], yaw);
    drawBox(gl, locations, geometry, vp, [x - 0.78, y + 0.16, z + 0.68], [0.22, 0.32, 0.5], [0.02, 0.025, 0.03, 1], yaw);
    drawBox(gl, locations, geometry, vp, [x + 0.78, y + 0.16, z + 0.68], [0.22, 0.32, 0.5], [0.02, 0.025, 0.03, 1], yaw);
  }

  function drawBox(gl, locations, geometry, vp, translation, scale, color, yaw = 0) {
    const model = mat4Multiply(mat4Translate(translation), mat4Multiply(mat4RotateY(yaw), mat4Scale(scale)));
    const matrix = mat4Multiply(vp, model);
    gl.uniformMatrix4fv(locations.matrix, false, matrix);
    gl.uniform4fv(locations.color, color);
    gl.drawElements(gl.TRIANGLES, geometry.indexCount, gl.UNSIGNED_SHORT, 0);
  }

  function resizeCanvas(gl) {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.floor(canvas.clientWidth * dpr));
    const height = Math.max(1, Math.floor(canvas.clientHeight * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      gl.viewport(0, 0, width, height);
    }
  }

  function initFallback2d(reason) {
    const ctx = canvas.getContext("2d");
    canvas.dataset.renderMode = "fallback-2d";
    setEvent(reason === "error webgl" ? "error webgl: fallback 2d activo" : "fallback 2d activo");
    let last = performance.now();

    function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      updateGame(dt);
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.max(1, Math.floor(canvas.clientWidth * dpr));
      canvas.height = Math.max(1, Math.floor(canvas.clientHeight * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      renderFallback2d(ctx, canvas.clientWidth, canvas.clientHeight);
      requestAnimationFrame(frame);
    }

    requestAnimationFrame(frame);
  }

  function renderFallback2d(ctx, width, height) {
    ctx.fillStyle = "#76bed8";
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = "#214f35";
    ctx.fillRect(0, height * 0.48, width, height * 0.52);
    ctx.fillStyle = "#222830";
    ctx.beginPath();
    ctx.moveTo(width * 0.42, height * 0.42);
    ctx.lineTo(width * 0.58, height * 0.42);
    ctx.lineTo(width * 0.86, height);
    ctx.lineTo(width * 0.14, height);
    ctx.closePath();
    ctx.fill();

    for (let i = 0; i < 16; i += 1) {
      const y = height * 0.46 + ((i * 42 + state.distance * 1.4) % (height * 0.58));
      const widthScale = (y / height) * 22;
      ctx.fillStyle = "#f3dc8a";
      ctx.fillRect(width / 2 - widthScale - 5, y, 7, 24);
      ctx.fillRect(width / 2 + widthScale, y, 7, 24);
    }

    drawFallbackCar(ctx, width / 2 + state.playerX * 38, height * 0.78, 1.15, "#47d6a3");
    state.rivals.forEach((rival) => {
      const depth = Math.max(0.22, Math.min(0.9, 1 + rival.z / 110));
      drawFallbackCar(ctx, width / 2 + rival.lane * laneWidth * 34 * depth, height * (0.48 + depth * 0.42), depth, "#f16b58");
    });
  }

  function drawFallbackCar(ctx, x, y, scale, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x - 28 * scale, y - 30 * scale, 56 * scale, 46 * scale);
    ctx.fillStyle = "#101820";
    ctx.fillRect(x - 16 * scale, y - 46 * scale, 32 * scale, 24 * scale);
    ctx.fillStyle = "#05070a";
    ctx.fillRect(x - 34 * scale, y - 21 * scale, 10 * scale, 18 * scale);
    ctx.fillRect(x + 24 * scale, y - 21 * scale, 10 * scale, 18 * scale);
  }

  function mat4Perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2);
    const nf = 1 / (near - far);
    return new Float32Array([
      f / aspect, 0, 0, 0,
      0, f, 0, 0,
      0, 0, (far + near) * nf, -1,
      0, 0, 2 * far * near * nf, 0
    ]);
  }

  function mat4LookAt(eye, target, up) {
    const z = normalize([eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]]);
    const x = normalize(cross(up, z));
    const y = cross(z, x);
    return new Float32Array([
      x[0], y[0], z[0], 0,
      x[1], y[1], z[1], 0,
      x[2], y[2], z[2], 0,
      -dot(x, eye), -dot(y, eye), -dot(z, eye), 1
    ]);
  }

  function mat4Translate(v) {
    return new Float32Array([
      1, 0, 0, 0,
      0, 1, 0, 0,
      0, 0, 1, 0,
      v[0], v[1], v[2], 1
    ]);
  }

  function mat4Scale(v) {
    return new Float32Array([
      v[0], 0, 0, 0,
      0, v[1], 0, 0,
      0, 0, v[2], 0,
      0, 0, 0, 1
    ]);
  }

  function mat4RotateY(angle) {
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    return new Float32Array([
      c, 0, -s, 0,
      0, 1, 0, 0,
      s, 0, c, 0,
      0, 0, 0, 1
    ]);
  }

  function mat4Multiply(a, b) {
    const out = new Float32Array(16);
    for (let row = 0; row < 4; row += 1) {
      for (let col = 0; col < 4; col += 1) {
        out[row + col * 4] =
          a[row] * b[col * 4] +
          a[row + 4] * b[col * 4 + 1] +
          a[row + 8] * b[col * 4 + 2] +
          a[row + 12] * b[col * 4 + 3];
      }
    }
    return out;
  }

  function normalize(v) {
    const length = Math.hypot(v[0], v[1], v[2]) || 1;
    return [v[0] / length, v[1] / length, v[2] / length];
  }

  function cross(a, b) {
    return [
      a[1] * b[2] - a[2] * b[1],
      a[2] * b[0] - a[0] * b[2],
      a[0] * b[1] - a[1] * b[0]
    ];
  }

  function dot(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  }

  bindInput();
  updateHud();

  try {
    initWebGl();
  } catch (error) {
    console.warn(error);
    initFallback2d("error webgl");
  }
})();
