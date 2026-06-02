(function () {
  "use strict";

  var canvas = document.getElementById("world");
  var distanceNode = document.getElementById("distance-value");
  var speedNode = document.getElementById("speed-value");
  var eventNode = document.getElementById("event-value");
  var root = document.documentElement;
  var params = new URLSearchParams(window.location.search);
  var lightMode = params.get("light") || "day";
  var runMode = params.get("mode") || "build";
  var startTime = performance.now();
  var frameCount = 0;
  var fallbackTimer = 0;

  root.dataset.light = lightMode;
  root.dataset.jsErrors = "0";

  function recordRuntimeError() {
    var current = Number(root.dataset.jsErrors || "0");
    root.dataset.jsErrors = String(current + 1);
  }

  window.addEventListener("error", recordRuntimeError);
  window.addEventListener("unhandledrejection", recordRuntimeError);

  function setTelemetry(now, renderMode) {
    var seconds = Math.max(0.1, (now - startTime) / 1000);
    var speed = 13.8 + Math.sin(seconds * 0.9) * 1.8 + (runMode === "smoke" ? 0.7 : 0);
    var distance = 2.4 + seconds * speed;

    distanceNode.textContent = distance.toFixed(1) + " m";
    speedNode.textContent = speed.toFixed(1) + " m/s";
    eventNode.textContent = renderMode + " activo";
  }

  function resizeCanvas() {
    var rect = canvas.getBoundingClientRect();
    var ratio = Math.min(window.devicePixelRatio || 1, 2);
    var width = Math.max(640, Math.floor(rect.width * ratio));
    var height = Math.max(420, Math.floor(rect.height * ratio));

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }

    return { width: width, height: height };
  }

  function createShader(gl, type, source) {
    var shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(shader) || "shader compile failed");
    }

    return shader;
  }

  function createProgram(gl) {
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
      "float line(float value, float width) {",
      "  return 1.0 - smoothstep(0.0, width, abs(value));",
      "}",
      "void main() {",
      "  vec2 uv = gl_FragCoord.xy / u_resolution.xy;",
      "  float horizon = smoothstep(0.1, 0.92, uv.y);",
      "  vec3 sky = mix(vec3(0.83, 0.94, 0.91), vec3(0.98, 0.99, 0.93), horizon);",
      "  float road = smoothstep(0.2, 0.92, 1.0 - uv.y);",
      "  vec3 base = mix(sky, vec3(0.78, 0.84, 0.80), road * 0.42);",
      "  float gridX = line(fract((uv.x + u_time * 0.04) * 12.0) - 0.5, 0.035);",
      "  float gridY = line(fract((uv.y + u_time * 0.08) * 9.0) - 0.5, 0.028);",
      "  float curve = line(uv.y - (0.33 + 0.18 * sin((uv.x * 6.2) + u_time)), 0.018);",
      "  float pulse = smoothstep(0.09, 0.0, distance(uv, vec2(fract(0.18 + u_time * 0.11), 0.55)));",
      "  vec3 gridColor = vec3(0.08, 0.49, 0.55);",
      "  vec3 curveColor = vec3(0.94, 0.57, 0.16);",
      "  base = mix(base, gridColor, (gridX + gridY) * 0.11);",
      "  base = mix(base, curveColor, curve * 0.82);",
      "  base += vec3(0.08, 0.29, 0.31) * pulse;",
      "  gl_FragColor = vec4(base, 1.0);",
      "}"
    ].join("\n");

    var program = gl.createProgram();
    gl.attachShader(program, createShader(gl, gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, createShader(gl, gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) || "program link failed");
    }

    return program;
  }

  function startWebgl() {
    var gl = canvas.getContext("webgl", { antialias: true }) || canvas.getContext("experimental-webgl");
    if (!gl) {
      throw new Error("webgl unavailable");
    }

    var program = createProgram(gl);
    var buffer = gl.createBuffer();
    var positionLocation = gl.getAttribLocation(program, "a_position");
    var resolutionLocation = gl.getUniformLocation(program, "u_resolution");
    var timeLocation = gl.getUniformLocation(program, "u_time");

    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW
    );

    canvas.dataset.renderMode = "webgl";

    function draw(now) {
      var size = resizeCanvas();
      var seconds = (now - startTime) / 1000;
      frameCount += 1;

      gl.viewport(0, 0, size.width, size.height);
      gl.clearColor(0.86, 0.94, 0.91, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.useProgram(program);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(positionLocation);
      gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
      gl.uniform2f(resolutionLocation, size.width, size.height);
      gl.uniform1f(timeLocation, seconds);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      setTelemetry(now, "webgl");
      window.requestAnimationFrame(draw);
    }

    window.requestAnimationFrame(draw);
  }

  function drawFallbackFrame(context, now) {
    var size = resizeCanvas();
    var width = size.width;
    var height = size.height;
    var seconds = (now - startTime) / 1000;
    var gradient = context.createLinearGradient(0, 0, 0, height);

    gradient.addColorStop(0, "#eef8f2");
    gradient.addColorStop(0.58, "#d7ece8");
    gradient.addColorStop(1, "#c7d5ce");
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);

    context.strokeStyle = "rgba(8, 126, 139, 0.22)";
    context.lineWidth = Math.max(1, width / 900);
    for (var x = -80; x < width + 80; x += 80) {
      context.beginPath();
      context.moveTo(x + Math.sin(seconds) * 30, height * 0.2);
      context.lineTo(x - width * 0.18, height);
      context.stroke();
    }
    for (var y = height * 0.32; y < height; y += 54) {
      context.beginPath();
      context.moveTo(0, y + Math.sin(seconds + y) * 4);
      context.lineTo(width, y + Math.cos(seconds + y) * 4);
      context.stroke();
    }

    context.strokeStyle = "#d7791c";
    context.lineWidth = Math.max(5, width / 180);
    context.beginPath();
    for (var i = 0; i <= 120; i += 1) {
      var t = i / 120;
      var px = t * width;
      var py = height * (0.55 + Math.sin(t * 6.2 + seconds) * 0.12);
      if (i === 0) {
        context.moveTo(px, py);
      } else {
        context.lineTo(px, py);
      }
    }
    context.stroke();

    context.fillStyle = "#0b5961";
    context.beginPath();
    context.arc((0.18 + seconds * 0.11) % 1 * width, height * 0.44, 32, 0, Math.PI * 2);
    context.fill();
    setTelemetry(now, "fallback-2d");
  }

  function startFallback() {
    var context = canvas.getContext("2d");
    canvas.dataset.renderMode = "fallback-2d";

    function draw(now) {
      drawFallbackFrame(context, now);
      fallbackTimer = window.requestAnimationFrame(draw);
    }

    window.requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resizeCanvas);

  try {
    startWebgl();
  } catch (error) {
    if (fallbackTimer) {
      window.cancelAnimationFrame(fallbackTimer);
    }
    startFallback();
  }

  setTelemetry(performance.now() + 100, canvas.dataset.renderMode || "fallback-2d");
})();
