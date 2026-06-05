(function () {
  "use strict";

  var canvas = document.getElementById("world");
  var distanceValue = document.getElementById("distance-value");
  var speedValue = document.getElementById("speed-value");
  var eventValue = document.getElementById("event-value");
  var startTime = performance.now();
  var state = {
    distance: 0,
    speed: 31,
    renderMode: "booting",
    lastFrame: startTime
  };

  function setHud(message) {
    distanceValue.textContent = Math.max(1, Math.floor(state.distance)).toLocaleString("en-US") + " m";
    speedValue.textContent = Math.round(state.speed).toString() + " m/s";
    eventValue.textContent = message;
  }

  function resizeCanvas() {
    var rect = canvas.getBoundingClientRect();
    var pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    var width = Math.max(640, Math.floor(rect.width * pixelRatio));
    var height = Math.max(360, Math.floor(rect.height * pixelRatio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
  }

  function compileShader(gl, type, source) {
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      var error = gl.getShaderInfoLog(shader) || "shader compile failed";
      gl.deleteShader(shader);
      throw new Error(error);
    }
    return shader;
  }

  function createWebglRenderer() {
    var gl = canvas.getContext("webgl", { antialias: true, alpha: false }) ||
      canvas.getContext("experimental-webgl", { antialias: true, alpha: false });
    if (!gl) {
      throw new Error("webgl unavailable");
    }

    var vertexSource = [
      "attribute vec2 a_position;",
      "void main() {",
      "  gl_Position = vec4(a_position, 0.0, 1.0);",
      "}"
    ].join("\n");
    var fragmentSource = [
      "precision mediump float;",
      "uniform vec2 u_resolution;",
      "uniform float u_time;",
      "float band(float value, float center, float width) {",
      "  return smoothstep(width, 0.0, abs(value - center));",
      "}",
      "void main() {",
      "  vec2 uv = gl_FragCoord.xy / u_resolution.xy;",
      "  float pulse = 0.5 + 0.5 * sin(u_time * 1.7);",
      "  vec3 sky = mix(vec3(0.49, 0.66, 0.68), vec3(0.15, 0.24, 0.24), uv.y);",
      "  vec3 ground = mix(vec3(0.20, 0.26, 0.16), vec3(0.49, 0.38, 0.21), uv.y);",
      "  vec3 color = mix(ground, sky, smoothstep(0.36, 0.40, uv.y));",
      "  float horizon = band(uv.y, 0.40 + 0.02 * sin(uv.x * 14.0 + u_time), 0.018);",
      "  color = mix(color, vec3(0.92, 0.73, 0.38), horizon * 0.55);",
      "  float roadWidth = mix(0.10, 0.58, smoothstep(0.38, 0.02, uv.y));",
      "  float road = smoothstep(roadWidth, roadWidth - 0.018, abs(uv.x - 0.5));",
      "  color = mix(color, vec3(0.16, 0.17, 0.15), road);",
      "  float laneOffset = fract((1.0 - uv.y) * 9.0 + u_time * 1.4);",
      "  float lane = band(abs(uv.x - 0.5), 0.035, 0.010) * smoothstep(0.65, 1.0, laneOffset) * step(uv.y, 0.55);",
      "  color = mix(color, vec3(0.95, 0.88, 0.57), lane);",
      "  vec2 shipUv = (uv - vec2(0.5, 0.31)) * vec2(2.8, 6.0);",
      "  float ship = smoothstep(0.42, 0.37, length(shipUv));",
      "  float cockpit = smoothstep(0.18, 0.12, length(shipUv - vec2(0.0, 0.10)));",
      "  color = mix(color, vec3(0.86, 0.20, 0.16), ship);",
      "  color = mix(color, vec3(0.96, 0.90, 0.65), cockpit);",
      "  float beacon = smoothstep(0.09, 0.02, length(uv - vec2(0.5, 0.46))) * (0.45 + pulse * 0.35);",
      "  color += vec3(0.50, 0.28, 0.06) * beacon;",
      "  gl_FragColor = vec4(color, 1.0);",
      "}"
    ].join("\n");

    var program = gl.createProgram();
    gl.attachShader(program, compileShader(gl, gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) || "program link failed");
    }

    var buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1,
      3, -1,
      -1, 3
    ]), gl.STATIC_DRAW);

    var positionLocation = gl.getAttribLocation(program, "a_position");
    var resolutionLocation = gl.getUniformLocation(program, "u_resolution");
    var timeLocation = gl.getUniformLocation(program, "u_time");

    return function renderWebgl(timeSeconds) {
      resizeCanvas();
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.useProgram(program);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(positionLocation);
      gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
      gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
      gl.uniform1f(timeLocation, timeSeconds);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
  }

  function createFallbackRenderer() {
    var context = canvas.getContext("2d", { alpha: false });
    if (!context) {
      throw new Error("2d canvas unavailable");
    }
    return function renderFallback(timeSeconds) {
      resizeCanvas();
      var width = canvas.width;
      var height = canvas.height;
      var gradient = context.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, "#8fb6b3");
      gradient.addColorStop(0.42, "#314542");
      gradient.addColorStop(0.43, "#6c5b32");
      gradient.addColorStop(1, "#24271c");
      context.fillStyle = gradient;
      context.fillRect(0, 0, width, height);

      context.fillStyle = "#252721";
      context.beginPath();
      context.moveTo(width * 0.46, height * 0.43);
      context.lineTo(width * 0.54, height * 0.43);
      context.lineTo(width * 0.82, height);
      context.lineTo(width * 0.18, height);
      context.closePath();
      context.fill();

      context.strokeStyle = "#f2dd79";
      context.lineWidth = Math.max(3, width * 0.006);
      context.setLineDash([height * 0.08, height * 0.08]);
      context.lineDashOffset = -timeSeconds * height * 0.18;
      context.beginPath();
      context.moveTo(width * 0.5, height * 0.46);
      context.lineTo(width * 0.5, height);
      context.stroke();
      context.setLineDash([]);

      context.fillStyle = "#d93a2c";
      context.beginPath();
      context.ellipse(width * 0.5, height * 0.68, width * 0.09, height * 0.065, 0, 0, Math.PI * 2);
      context.fill();
      context.fillStyle = "#fff0a0";
      context.beginPath();
      context.ellipse(width * 0.5, height * 0.64, width * 0.035, height * 0.025, 0, 0, Math.PI * 2);
      context.fill();
    };
  }

  function boot() {
    resizeCanvas();
    var render;
    try {
      render = createWebglRenderer();
      state.renderMode = "webgl";
      canvas.setAttribute("data-render-mode", "webgl");
    } catch (error) {
      render = createFallbackRenderer();
      state.renderMode = "fallback-2d";
      canvas.setAttribute("data-render-mode", "fallback-2d");
    }

    function frame(now) {
      var delta = Math.min(0.08, Math.max(0.001, (now - state.lastFrame) / 1000));
      var elapsed = (now - startTime) / 1000;
      state.lastFrame = now;
      state.speed = 34 + Math.sin(elapsed * 1.4) * 4;
      state.distance += state.speed * delta;
      render(elapsed);
      setHud(state.renderMode === "webgl" ? "webgl activo" : "fallback 2d activo");
      window.requestAnimationFrame(frame);
    }

    setHud("preparado");
    window.requestAnimationFrame(frame);
  }

  window.addEventListener("resize", resizeCanvas);
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
}());
