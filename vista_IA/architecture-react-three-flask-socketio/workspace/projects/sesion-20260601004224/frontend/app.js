(function () {
  "use strict";

  const canvas = document.getElementById("world");
  const hud = {
    score: document.getElementById("score-value"),
    distance: document.getElementById("distance-value"),
    speed: document.getElementById("speed-value"),
    reward: document.getElementById("reward-value"),
    camera: document.getElementById("camera-value"),
    stage: document.getElementById("stage-value"),
    policy: document.getElementById("policy-value"),
    event: document.getElementById("event-value"),
    episode: document.getElementById("episode-value"),
    epsilon: document.getElementById("epsilon-bar"),
    q: document.getElementById("q-bar"),
    energy: document.getElementById("energy-bar"),
    coins: document.getElementById("coins-value"),
    combo: document.getElementById("combo-value"),
    castle: document.getElementById("castle-value"),
    threat: document.getElementById("threat-value"),
    pressure: document.getElementById("pressure-value"),
    progress: document.getElementById("progress-marker"),
    leaderboard: document.getElementById("leaderboard")
  };

  const ACTIONS = ["run", "jump", "duck", "dash"];
  const FEATURE_COUNT = 9;
  // The hero face is modeled toward +Z, while the runner route advances on +X.
  const HERO_CORRIDOR_YAW = Math.PI * 0.5;
  const params = new URLSearchParams(window.location.search);
  const lightMode = params.get("light") || "day";

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function makeWeights(actionIndex) {
    const presets = [
      [0.12, -0.28, -0.16, 0.08, -0.04, 0.01, 0.08, 0.05, 0.06],
      [-0.02, 0.62, 0.34, -0.06, -0.32, 0.08, -0.02, 0.02, 0.03],
      [-0.04, 0.22, -0.14, -0.03, 0.16, -0.05, -0.02, 0.04, 0.01],
      [0.06, -0.12, -0.04, 0.22, -0.08, 0.02, 0.18, 0.08, 0.04]
    ];
    return presets[actionIndex].slice();
  }

  class DQNAgent {
    constructor() {
      this.epsilon = 0.32;
      this.gamma = 0.86;
      this.learningRate = 0.045;
      this.weights = ACTIONS.map((_, index) => makeWeights(index));
      this.lastQ = 0;
      this.decisions = 0;
    }

    qValue(features, actionIndex) {
      return this.weights[actionIndex].reduce((sum, weight, index) => sum + weight * features[index], 0);
    }

    choose(features) {
      this.decisions += 1;
      if (Math.random() < this.epsilon) {
        return Math.floor(Math.random() * ACTIONS.length);
      }
      const scores = ACTIONS.map((_, index) => this.qValue(features, index));
      this.lastQ = Math.max(...scores);
      return scores.indexOf(this.lastQ);
    }

    learn(previousFeatures, actionIndex, reward, nextFeatures, done) {
      const current = this.qValue(previousFeatures, actionIndex);
      const nextBest = Math.max(...ACTIONS.map((_, index) => this.qValue(nextFeatures, index)));
      const target = reward + (done ? 0 : this.gamma * nextBest);
      const error = target - current;
      const weights = this.weights[actionIndex];
      for (let index = 0; index < FEATURE_COUNT; index += 1) {
        weights[index] += this.learningRate * error * previousFeatures[index];
      }
      this.lastQ = lerp(this.lastQ, nextBest, 0.12);
      this.epsilon = Math.max(0.06, this.epsilon * 0.9992);
    }
  }

  class Game {
    constructor() {
      this.agent = new DQNAgent();
      this.bestRuns = this.loadScores();
      this.episode = 0;
      this.messageTimer = 0;
      this.reset("start");
    }

    loadScores() {
      try {
        const stored = JSON.parse(localStorage.getItem("castle-runner-scores") || "[]");
        if (Array.isArray(stored) && stored.length > 0) {
          return stored.slice(0, 5);
        }
      } catch (_error) {
        return [];
      }
      return [
        { score: 4200, meters: 720, label: "Ruta Alfa" },
        { score: 3150, meters: 610, label: "Ruta Beta" },
        { score: 2080, meters: 470, label: "Ruta Gamma" }
      ];
    }

    saveScores() {
      try {
        localStorage.setItem("castle-runner-scores", JSON.stringify(this.bestRuns.slice(0, 5)));
      } catch (_error) {
        return;
      }
    }

    reset(reason) {
      this.episode += 1;
      this.distance = 0;
      this.speed = 4.8;
      this.score = 0;
      this.rewardTotal = 0;
      this.energy = 100;
      this.coins = 0;
      this.combo = 1;
      this.time = 0;
      this.castleX = 900;
      this.biomeIndex = 0;
      this.biomeName = "Valle";
      this.threatLevel = 0;
      this.difficultyPressure = 0;
      this.difficultyLabel = "estable";
      this.policyLabel = "run";
      this.routeTier = 1;
      this.player = {
        y: 0,
        vy: 0,
        duck: 0,
        shield: 0,
        invulnerable: 0,
        onGround: true
      };
      this.objects = [];
      this.nextSpawn = 45;
      this.spawnAhead();
      this.currentFeatures = this.observe();
      this.lastAction = 0;
      this.lastReward = 0;
      this.event = reason === "castle" ? "castillo conquistado, nueva ruta" : "agente entrenando ruta autonoma";
      this.updateHud();
    }

    spawnAhead() {
      while (this.nextSpawn < this.distance + 820 && this.nextSpawn < this.castleX - 45) {
        const lane = Math.floor(this.nextSpawn / 55) % 8;
        const routeBand = Math.floor(this.nextSpawn / 210) % 4;
        const laneZ = (routeBand - 1.5) * 1.25;
        const base = this.nextSpawn;
        if (lane === 0) {
          this.objects.push({ type: "coin", x: base + 12, y: 36, w: 6, h: 6, laneZ, active: true });
          this.objects.push({ type: "coin", x: base + 23, y: 52, w: 6, h: 6, laneZ, active: true });
          this.objects.push({ type: "crystal", x: base + 38, y: 68, w: 8, h: 10, laneZ, active: true });
        } else if (lane === 1) {
          this.objects.push({ type: "turtle", x: base, y: 0, w: 13, h: 16, laneZ, active: true });
        } else if (lane === 2) {
          this.objects.push({ type: "gate", x: base + 4, y: 0, w: 12, h: 32, laneZ, active: true });
          this.objects.push({ type: "coin", x: base + 28, y: 62, w: 6, h: 6, laneZ, active: true });
        } else if (lane === 3) {
          this.objects.push({ type: "spring", x: base + 8, y: 0, w: 12, h: 8, laneZ, active: true });
          this.objects.push({ type: "winged", x: base + 34, y: 38, w: 15, h: 13, laneZ, phase: base * 0.03, active: true });
        } else if (lane === 4) {
          this.objects.push({ type: "mushroom", x: base + 6, y: 0, w: 13, h: 17, laneZ, active: true });
          this.objects.push({ type: "coin", x: base + 30, y: 42, w: 6, h: 6, laneZ, active: true });
        } else if (lane === 5) {
          this.objects.push({ type: "battery", x: base + 16, y: 28, w: 7, h: 9, laneZ, active: true });
          this.objects.push({ type: "goomba", x: base + 38, y: 0, w: 12, h: 14, laneZ, active: true });
        } else if (lane === 6) {
          this.objects.push({ type: "firebar", x: base + 18, y: 10, w: 18, h: 28, laneZ, phase: base * 0.04, active: true });
        } else {
          this.objects.push({ type: "portal", x: base + 20, y: 24, w: 13, h: 26, laneZ, active: true });
          this.objects.push({ type: "coin", x: base + 44, y: 58, w: 6, h: 6, laneZ, active: true });
        }
        this.nextSpawn += 38 + (lane % 4) * 10 + Math.floor(this.routeTier * 1.5);
      }
    }

    updateWorldState() {
      const previousBiome = this.biomeName;
      const progress = this.distance / this.castleX;
      const biomes = ["Valle", "Bosque", "Nubes", "Volcan", "Castillo"];
      this.biomeIndex = clamp(Math.floor(progress * biomes.length), 0, biomes.length - 1);
      this.biomeName = biomes[this.biomeIndex];
      this.routeTier = 1 + this.biomeIndex;
      const nextHazards = this.objects.filter((object) => object.active && !["coin", "battery", "crystal", "portal"].includes(object.type) && object.x >= this.playerWorldX() - 6 && object.x < this.playerWorldX() + 120);
      this.threatLevel = clamp(nextHazards.length * 18 + this.biomeIndex * 10 + Math.max(0, this.speed - 6) * 5, 0, 100);
      if (previousBiome !== this.biomeName && this.distance > 20) {
        this.event = `nuevo bioma: ${this.biomeName}`;
        this.messageTimer = 0.75;
      }
    }

    playerWorldX() {
      return this.distance + 28;
    }

    observe() {
      const playerX = this.playerWorldX();
      const hazards = this.objects.filter((object) => object.active && object.type !== "coin" && object.type !== "battery" && object.x >= playerX - 4);
      const coins = this.objects.filter((object) => object.active && (object.type === "coin" || object.type === "battery") && object.x >= playerX - 4);
      const nearestHazard = hazards.sort((a, b) => a.x - b.x)[0];
      const nearestCoin = coins.sort((a, b) => a.x - b.x)[0];
      const hazardDistance = nearestHazard ? clamp((nearestHazard.x - playerX) / 110, 0, 1) : 1;
      const hazardHeight = nearestHazard ? clamp(nearestHazard.h / 36, 0, 1) : 0;
      const coinDistance = nearestCoin ? clamp((nearestCoin.x - playerX) / 120, 0, 1) : 1;
      return [
        1,
        1 - hazardDistance,
        hazardHeight,
        1 - coinDistance,
        clamp(this.player.y / 90, 0, 1),
        clamp((this.player.vy + 70) / 140, 0, 1),
        clamp(this.speed / 10, 0, 1),
        clamp(this.energy / 100, 0, 1),
        clamp(this.distance / this.castleX, 0, 1)
      ];
    }

    act(actionIndex, dt) {
      const action = ACTIONS[actionIndex];
      if (action === "jump" && this.player.onGround) {
        this.player.vy = 64 + this.speed * 1.4;
        this.player.onGround = false;
        this.event = "salto predictivo ante riesgo";
      }
      if (action === "duck") {
        this.player.duck = Math.max(this.player.duck, 0.24);
      }
      if (action === "dash" && this.energy > 8) {
        this.speed += 4.2 * dt;
        this.energy -= 9 * dt;
        this.event = "dash hacia recompensa";
      }
      if (action === "run") {
        this.speed += 1.6 * dt;
      }
    }

    tick(dt) {
      const step = clamp(dt, 0.001, 0.05);
      this.time += step;
      this.messageTimer = Math.max(0, this.messageTimer - step);
      this.spawnAhead();

      const previousFeatures = this.currentFeatures || this.observe();
      const actionIndex = this.agent.choose(previousFeatures);
      this.lastAction = actionIndex;
      this.policyLabel = ACTIONS[actionIndex];
      this.act(actionIndex, step);

      const reward = this.simulate(step);
      const done = this.energy <= 0 || this.distance >= this.castleX;
      const nextFeatures = this.observe();
      this.agent.learn(previousFeatures, actionIndex, reward, nextFeatures, done);
      this.currentFeatures = nextFeatures;
      this.lastReward = reward;
      this.rewardTotal += reward;
      this.updateHud();

      if (this.energy <= 0) {
        this.finishRun("energia agotada");
      }
      if (this.distance >= this.castleX) {
        this.score += 850 + Math.floor(this.energy * 4);
        this.finishRun("castle");
      }
    }

    simulate(dt) {
      const before = this.distance;
      this.player.duck = Math.max(0, this.player.duck - dt);
      this.player.invulnerable = Math.max(0, this.player.invulnerable - dt);
      this.player.shield = Math.max(0, this.player.shield - dt);
      this.speed = clamp(this.speed + 0.22 * dt, 2.4, 9.6);
      this.distance += this.speed * dt * 8.2;
      this.energy = clamp(this.energy + 3.5 * dt, 0, 100);
      this.updateObjectDynamics(dt);
      this.updateWorldState();
      this.updateDifficultyDirector(dt);

      this.player.vy -= 92 * dt;
      this.player.y += this.player.vy * dt;
      if (this.player.y <= 0) {
        this.player.y = 0;
        this.player.vy = 0;
        this.player.onGround = true;
      }

      let reward = (this.distance - before) * 0.12;
      reward += this.speed > 6.2 ? 0.012 : -0.004;
      reward += this.combo > 1 ? 0.006 * this.combo : 0;
      reward += this.handleCollisions();

      this.objects = this.objects.filter((object) => object.active || object.x > this.distance - 80);
      this.score = Math.max(0, this.score + Math.floor(reward * 9));
      return reward;
    }

    updateDifficultyDirector(dt) {
      const previousLabel = this.difficultyLabel;
      const progress = clamp(this.distance / this.castleX, 0, 1);
      const risk = clamp(
        this.threatLevel / 100 * 0.58 + progress * 0.28 + Math.max(0, this.combo - 1) * 0.015 - (this.energy < 35 ? 0.14 : 0),
        0,
        1
      );
      this.difficultyPressure = lerp(this.difficultyPressure, risk, 0.08);

      if (this.difficultyPressure > 0.72) {
        this.difficultyLabel = "asistencia";
        this.speed = clamp(this.speed - 0.38 * dt, 2.4, 9.1);
        this.energy = clamp(this.energy + 2.4 * dt, 0, 100);
      } else if (this.difficultyPressure < 0.24 && this.energy > 68 && progress > 0.08) {
        this.difficultyLabel = "reto";
        this.speed = clamp(this.speed + 0.18 * dt, 2.4, 9.8);
      } else {
        this.difficultyLabel = "estable";
      }

      if (previousLabel !== this.difficultyLabel && this.messageTimer <= 0) {
        this.event = `director ${this.difficultyLabel}`;
        this.messageTimer = 0.7;
      }
    }

    updateObjectDynamics(dt) {
      for (const object of this.objects) {
        if (!object.active) {
          continue;
        }
        if (object.type === "winged") {
          object.y = 36 + Math.sin(this.time * 3.2 + (object.phase || 0)) * 14;
          object.x -= dt * (2.2 + this.biomeIndex * 0.7);
        }
        if (object.type === "firebar") {
          object.phase = (object.phase || 0) + dt * (2.4 + this.biomeIndex * 0.35);
          object.y = 14 + Math.sin(object.phase) * 9;
          object.h = 26 + Math.abs(Math.cos(object.phase)) * 12;
        }
        if (object.type === "portal") {
          object.y = 24 + Math.sin(this.time * 2.4 + object.x * 0.01) * 5;
        }
      }
    }

    handleCollisions() {
      const playerX = this.playerWorldX();
      const playerHeight = this.player.duck > 0 ? 13 : 25;
      const playerWidth = this.player.duck > 0 ? 14 : 11;
      let reward = 0;

      for (const object of this.objects) {
        if (!object.active) {
          continue;
        }
        const overlapX = Math.abs(object.x - playerX) < (object.w + playerWidth);
        const overlapY = this.player.y < object.y + object.h && this.player.y + playerHeight > object.y;
        if (!overlapX || !overlapY) {
          continue;
        }

        if (object.type === "coin") {
          object.active = false;
          this.coins += 1;
          this.combo = Math.min(9, this.combo + 1);
          reward += 4.5 * this.combo;
          this.score += 120 * this.combo;
          this.event = "moneda tomada con combo";
          this.messageTimer = 0.5;
        } else if (object.type === "battery") {
          object.active = false;
          this.energy = clamp(this.energy + 25, 0, 100);
          this.player.shield = 1.8;
          reward += 6.5;
          this.score += 180;
          this.event = "escudo cargado";
          this.messageTimer = 0.5;
        } else if (object.type === "crystal") {
          object.active = false;
          this.combo = Math.min(12, this.combo + 2);
          reward += 9.5 * this.combo;
          this.score += 320 * this.combo;
          this.event = "cristal raro activa ruta LACE";
          this.messageTimer = 0.7;
        } else if (object.type === "portal") {
          object.active = false;
          this.distance += 42;
          this.energy = clamp(this.energy + 12, 0, 100);
          reward += 11;
          this.score += 450;
          this.event = "portal acelera hacia el castillo";
          this.messageTimer = 0.7;
        } else if (object.type === "spring") {
          object.active = false;
          this.player.vy = 82;
          this.player.onGround = false;
          reward += 3.5;
          this.event = "resorte usado para ruta alta";
          this.messageTimer = 0.5;
        } else {
          const stomped = this.player.vy < 0 && this.player.y > object.h * 0.55;
          const enemyName = object.type === "turtle" ? "tortuga" : object.type === "mushroom" ? "hongo enemigo" : object.type === "goomba" ? "goomba" : object.type === "winged" ? "tortuga alada" : object.type === "firebar" ? "barra de fuego" : "amenaza";
          if (stomped) {
            object.active = false;
            this.player.vy = 48;
            this.combo = Math.min(9, this.combo + 1);
            reward += 7.5 * this.combo;
            this.score += 220 * this.combo;
            this.event = `${enemyName} neutralizado`;
            this.messageTimer = 0.5;
          } else if (this.player.invulnerable <= 0) {
            const blocked = this.player.shield > 0;
            this.energy -= blocked ? 5 : 18;
            this.speed = Math.max(2.6, this.speed - (blocked ? 0.35 : 1.2));
            this.combo = 1;
            this.player.invulnerable = 0.55;
            reward -= blocked ? 2.5 : 10.5;
            this.event = blocked ? `escudo bloquea ${enemyName}` : `impacto con ${enemyName}`;
            this.messageTimer = 0.6;
          }
        }
      }
      return reward;
    }

    finishRun(reason) {
      const label = reason === "castle" ? "Castillo" : "Recovery";
      this.bestRuns.unshift({
        score: Math.round(this.score),
        meters: Math.round(this.distance),
        label: `${label} E${this.episode}`
      });
      this.bestRuns = this.bestRuns.sort((a, b) => b.score - a.score).slice(0, 5);
      this.saveScores();
      this.reset(reason);
    }

    updateHud() {
      hud.score.textContent = String(Math.round(this.score));
      hud.distance.textContent = `${Math.floor(this.distance)} m`;
      hud.speed.textContent = `${this.speed.toFixed(1)} m/s`;
      hud.reward.textContent = this.rewardTotal.toFixed(2);
      hud.event.textContent = this.event;
      hud.episode.textContent = `Episodio ${this.episode}`;
      hud.coins.textContent = String(this.coins);
      hud.combo.textContent = `x${this.combo}`;
      hud.castle.textContent = `${Math.max(0, Math.ceil(this.castleX - this.distance))} m`;
      if (hud.stage) {
        hud.stage.textContent = this.biomeName;
      }
      if (hud.policy) {
        hud.policy.textContent = this.policyLabel;
      }
      if (hud.threat) {
        hud.threat.textContent = `${Math.round(this.threatLevel)}%`;
      }
      if (hud.pressure) {
        hud.pressure.textContent = `${this.difficultyLabel} ${Math.round(this.difficultyPressure * 100)}%`;
      }
      hud.progress.style.left = `${clamp((this.distance / this.castleX) * 100, 0, 97)}%`;
      hud.epsilon.style.width = `${clamp(this.agent.epsilon * 100, 6, 100)}%`;
      hud.q.style.width = `${clamp((this.agent.lastQ + 2) * 18, 4, 100)}%`;
      hud.energy.style.width = `${clamp(this.energy, 0, 100)}%`;
      hud.leaderboard.innerHTML = this.bestRuns
        .slice(0, 5)
        .map((run) => `<li><b>${run.score}</b> ${run.meters} m ${run.label}</li>`)
        .join("");
    }
  }

  class CanvasRenderer {
    constructor(targetCanvas) {
      this.canvas = targetCanvas;
      this.ctx = targetCanvas.getContext("2d");
      this.dpr = 1;
      this.canvas.dataset.renderMode = "fallback-2d";
      window.addEventListener("resize", () => this.resize(), { passive: true });
      this.resize();
    }

    resize() {
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.floor(this.canvas.clientWidth * this.dpr));
      const height = Math.max(1, Math.floor(this.canvas.clientHeight * this.dpr));
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
      }
    }

    screenX(gameX, game) {
      const scale = this.canvas.width / 310;
      return this.canvas.width * 0.27 + (gameX - game.playerWorldX()) * scale;
    }

    groundY() {
      return this.canvas.height * 0.72;
    }

    render(game) {
      this.resize();
      const ctx = this.ctx;
      const width = this.canvas.width;
      const height = this.canvas.height;
      const groundY = this.groundY();
      const day = lightMode !== "night";
      if (hud.camera) {
        hud.camera.textContent = "2D";
      }

      const sky = ctx.createLinearGradient(0, 0, 0, height);
      const biomeSky = {
        Valle: ["#64caff", "#d5f4ff", "#61ba65", "#215c33"],
        Bosque: ["#5ab7da", "#bce8d5", "#4b9c5a", "#214a2e"],
        Nubes: ["#8edbff", "#f4fbff", "#a7d6ea", "#507c9a"],
        Volcan: ["#312044", "#9b5444", "#6e3a2c", "#241412"],
        Castillo: ["#435070", "#d5d8e7", "#7b8a8f", "#2f3439"]
      }[game.biomeName] || ["#64caff", "#d5f4ff", "#61ba65", "#215c33"];
      sky.addColorStop(0, day ? biomeSky[0] : "#14284f");
      sky.addColorStop(0.55, day ? biomeSky[1] : "#364f85");
      sky.addColorStop(0.56, day ? biomeSky[2] : "#396a50");
      sky.addColorStop(1, day ? biomeSky[3] : "#17291f");
      ctx.fillStyle = sky;
      ctx.fillRect(0, 0, width, height);

      this.drawSun(ctx, width, height, day);
      this.drawClouds(ctx, width, height, game);
      this.drawHills(ctx, width, height, game);
      this.drawRoad(ctx, width, groundY, game);
      this.drawCastle(ctx, width, groundY, game);
      this.drawObjects(ctx, game, groundY);
      this.drawPlayer(ctx, game, groundY);
    }

    drawSun(ctx, width, height, day) {
      ctx.save();
      ctx.globalAlpha = day ? 0.92 : 0.42;
      ctx.fillStyle = day ? "#ffd45a" : "#d8e6ff";
      ctx.beginPath();
      ctx.arc(width * 0.18, height * 0.18, Math.min(width, height) * 0.055, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    drawClouds(ctx, width, height, game) {
      const offset = (game.distance * 0.45) % (width * 0.7);
      ctx.save();
      ctx.fillStyle = "rgba(255, 255, 255, 0.88)";
      for (let index = 0; index < 5; index += 1) {
        const x = ((index * width * 0.32 - offset) % (width + 180)) - 90;
        const y = height * (0.14 + (index % 3) * 0.07);
        const scale = 0.72 + (index % 2) * 0.28;
        ctx.beginPath();
        ctx.ellipse(x, y, 42 * scale, 17 * scale, 0, 0, Math.PI * 2);
        ctx.ellipse(x + 28 * scale, y - 8 * scale, 32 * scale, 22 * scale, 0, 0, Math.PI * 2);
        ctx.ellipse(x + 62 * scale, y, 44 * scale, 18 * scale, 0, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    drawHills(ctx, width, height, game) {
      const offset = (game.distance * 1.3) % 220;
      ctx.save();
      for (let layer = 0; layer < 2; layer += 1) {
        ctx.fillStyle = layer === 0 ? "rgba(47, 116, 80, 0.72)" : "rgba(39, 91, 67, 0.88)";
        const base = height * (0.58 + layer * 0.08);
        ctx.beginPath();
        ctx.moveTo(-240 - offset * (layer + 1), base);
        for (let x = -240; x < width + 420; x += 220) {
          ctx.quadraticCurveTo(x + 90 - offset * (layer + 1), base - 95 + layer * 28, x + 220 - offset * (layer + 1), base);
        }
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
    }

    drawRoad(ctx, width, groundY, game) {
      ctx.save();
      ctx.fillStyle = "#6a3d2b";
      ctx.fillRect(0, groundY, width, this.canvas.height - groundY);
      ctx.fillStyle = "#3d241b";
      const tileWidth = width / 12;
      const start = -((game.distance * 18) % tileWidth);
      for (let x = start; x < width + tileWidth; x += tileWidth) {
        ctx.fillRect(x, groundY, tileWidth - 3, 18);
        ctx.fillRect(x + tileWidth * 0.5, groundY + 21, tileWidth - 3, 18);
      }
      ctx.fillStyle = "#48b85d";
      ctx.fillRect(0, groundY - 16, width, 18);
      ctx.fillStyle = "#92de67";
      for (let x = start; x < width + 24; x += 36) {
        ctx.fillRect(x, groundY - 20, 18, 5);
      }
      ctx.restore();
    }

    drawCastle(ctx, width, groundY, game) {
      const scale = width / 310;
      const x = this.screenX(game.castleX, game);
      if (x < -120 || x > width + 180) {
        return;
      }
      ctx.save();
      ctx.translate(x, groundY);
      ctx.scale(scale, scale);
      ctx.fillStyle = "#dad6c6";
      ctx.fillRect(-34, -76, 68, 76);
      ctx.fillStyle = "#b74234";
      ctx.fillRect(-42, -92, 22, 24);
      ctx.fillRect(-11, -104, 22, 36);
      ctx.fillRect(20, -92, 22, 24);
      ctx.fillStyle = "#f7f0da";
      ctx.fillRect(-28, -56, 14, 20);
      ctx.fillRect(14, -56, 14, 20);
      ctx.fillStyle = "#5d392b";
      ctx.beginPath();
      ctx.roundRect(-12, -30, 24, 30, 7);
      ctx.fill();
      ctx.restore();
    }

    drawObjects(ctx, game, groundY) {
      const scale = this.canvas.width / 310;
      for (const object of game.objects) {
        if (!object.active) {
          continue;
        }
        const x = this.screenX(object.x, game);
        if (x < -60 || x > this.canvas.width + 80) {
          continue;
        }
        const y = groundY - object.y * scale;
        ctx.save();
        ctx.translate(x, y);
        ctx.scale(scale, scale);
        if (object.type === "coin") {
          ctx.fillStyle = "#ffd45a";
          ctx.beginPath();
          ctx.ellipse(0, -8, 5, 8, 0, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = "#8d6220";
          ctx.stroke();
        } else if (object.type === "battery") {
          ctx.fillStyle = "#48d97b";
          ctx.fillRect(-5, -18, 10, 14);
          ctx.fillStyle = "#eaff9a";
          ctx.fillRect(-2, -22, 4, 4);
        } else if (object.type === "crystal") {
          ctx.fillStyle = "#78f1ff";
          ctx.beginPath();
          ctx.moveTo(0, -30);
          ctx.lineTo(9, -18);
          ctx.lineTo(4, -4);
          ctx.lineTo(-6, -4);
          ctx.lineTo(-10, -18);
          ctx.closePath();
          ctx.fill();
          ctx.strokeStyle = "#d9fdff";
          ctx.stroke();
        } else if (object.type === "portal") {
          ctx.strokeStyle = "#ba79ff";
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.ellipse(0, -22, 11, 22, 0, 0, Math.PI * 2);
          ctx.stroke();
          ctx.strokeStyle = "#6df0ff";
          ctx.beginPath();
          ctx.ellipse(0, -22, 6, 16, 0.5, 0, Math.PI * 2);
          ctx.stroke();
        } else if (object.type === "spring") {
          ctx.strokeStyle = "#68e0ff";
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(-9, -4);
          ctx.lineTo(9, -8);
          ctx.lineTo(-9, -12);
          ctx.lineTo(9, -16);
          ctx.stroke();
        } else if (object.type === "firebar") {
          ctx.strokeStyle = "#ffcf5a";
          ctx.lineWidth = 5;
          ctx.beginPath();
          ctx.moveTo(-12, -8);
          ctx.lineTo(12, -32);
          ctx.stroke();
          ctx.fillStyle = "#ff6546";
          ctx.beginPath();
          ctx.arc(13, -33, 8, 0, Math.PI * 2);
          ctx.fill();
        } else if (object.type === "winged") {
          ctx.fillStyle = "#235b38";
          ctx.beginPath();
          ctx.ellipse(0, -16, 12, 8, 0, Math.PI, 0);
          ctx.fill();
          ctx.fillStyle = "#f4f7ff";
          ctx.beginPath();
          ctx.ellipse(-11, -21, 9, 5, -0.4, 0, Math.PI * 2);
          ctx.ellipse(11, -21, 9, 5, 0.4, 0, Math.PI * 2);
          ctx.fill();
        } else if (object.type === "gate") {
          ctx.fillStyle = "#7f3b2f";
          ctx.fillRect(-8, -34, 16, 34);
          ctx.fillStyle = "#f4cc58";
          ctx.fillRect(-11, -38, 22, 7);
        } else if (object.type === "turtle") {
          ctx.fillStyle = "#235b38";
          ctx.beginPath();
          ctx.ellipse(0, -14, 13, 10, 0, Math.PI, 0);
          ctx.fill();
          ctx.fillStyle = "#f1d28f";
          ctx.fillRect(-10, -13, 20, 10);
          ctx.fillStyle = "#214b31";
          ctx.fillRect(-12, -5, 5, 5);
          ctx.fillRect(7, -5, 5, 5);
          ctx.fillStyle = "#ffe0a7";
          ctx.beginPath();
          ctx.arc(13, -13, 5, 0, Math.PI * 2);
          ctx.fill();
        } else if (object.type === "mushroom") {
          ctx.fillStyle = "#d94c3d";
          ctx.beginPath();
          ctx.ellipse(0, -15, 13, 10, 0, Math.PI, 0);
          ctx.fill();
          ctx.fillStyle = "#fff2d7";
          ctx.fillRect(-8, -15, 16, 15);
          ctx.fillStyle = "#4d2b22";
          ctx.fillRect(-4, -9, 2, 3);
          ctx.fillRect(3, -9, 2, 3);
          ctx.fillStyle = "#fff7e8";
          ctx.beginPath();
          ctx.arc(-6, -18, 3, 0, Math.PI * 2);
          ctx.arc(5, -20, 3, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillStyle = "#8f4f2d";
          ctx.beginPath();
          ctx.roundRect(-9, -15, 18, 15, 5);
          ctx.fill();
          ctx.fillStyle = "#fff2d7";
          ctx.fillRect(-5, -11, 2, 3);
          ctx.fillRect(4, -11, 2, 3);
          ctx.fillStyle = "#4d2b22";
          ctx.fillRect(-10, -2, 6, 4);
          ctx.fillRect(4, -2, 6, 4);
        }
        ctx.restore();
      }
    }

    drawPlayer(ctx, game, groundY) {
      const scale = this.canvas.width / 310;
      const x = this.canvas.width * 0.27;
      const y = groundY - game.player.y * scale;
      const duck = game.player.duck > 0;
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(scale, scale);
      ctx.fillStyle = "rgba(0, 0, 0, 0.25)";
      ctx.beginPath();
      ctx.ellipse(0, 5, 17, 5, 0, 0, Math.PI * 2);
      ctx.fill();
      const torsoTop = duck ? -18 : -26;
      const headY = duck ? -27 : -40;
      ctx.fillStyle = "#d94736";
      ctx.fillRect(-14, torsoTop - 2, 28, 13);
      ctx.fillStyle = game.player.shield > 0 ? "#69e6ff" : "#2459b7";
      ctx.fillRect(-10, torsoTop + 6, 20, duck ? 16 : 24);
      ctx.fillStyle = "#ffd45a";
      ctx.fillRect(-6, torsoTop + 11, 4, 4);
      ctx.fillRect(3, torsoTop + 11, 4, 4);
      ctx.fillStyle = "#ffd2a2";
      ctx.beginPath();
      ctx.roundRect(-13, headY - 8, 26, 20, 8);
      ctx.fill();
      ctx.fillStyle = "#d94736";
      ctx.beginPath();
      ctx.roundRect(-15, headY - 18, 30, 11, 5);
      ctx.fill();
      ctx.fillRect(-19, headY - 10, 17, 4);
      ctx.fillStyle = "#fff7dc";
      ctx.fillRect(-3, headY - 16, 7, 5);
      ctx.fillStyle = "#1f2b36";
      ctx.fillRect(2, headY - 2, 3, 3);
      ctx.fillRect(8, headY - 2, 3, 3);
      ctx.fillStyle = "#7a3729";
      ctx.beginPath();
      ctx.ellipse(3, headY + 7, 6, 3, 0, 0, Math.PI * 2);
      ctx.ellipse(10, headY + 7, 6, 3, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#ffd2a2";
      ctx.fillRect(-19, torsoTop + 6, 7, 12);
      ctx.fillRect(12, torsoTop + 6, 7, 12);
      ctx.fillStyle = "#2b211d";
      ctx.fillRect(-11, 0, 9, 5);
      ctx.fillRect(2, 0, 11, 5);
      ctx.restore();
    }
  }

  class OrbitControlsLite {
    constructor(targetCanvas) {
      this.canvas = targetCanvas;
      this.yaw = -0.34;
      this.pitch = 0.34;
      this.distance = 16;
      this.dragging = false;
      this.lastX = 0;
      this.lastY = 0;
      targetCanvas.addEventListener("pointerdown", (event) => this.pointerDown(event));
      targetCanvas.addEventListener("pointermove", (event) => this.pointerMove(event));
      targetCanvas.addEventListener("pointerup", (event) => this.pointerUp(event));
      targetCanvas.addEventListener("pointercancel", (event) => this.pointerUp(event));
      targetCanvas.addEventListener("wheel", (event) => this.zoom(event), { passive: false });
    }

    pointerDown(event) {
      this.dragging = true;
      this.lastX = event.clientX;
      this.lastY = event.clientY;
      if (this.canvas.setPointerCapture) {
        this.canvas.setPointerCapture(event.pointerId);
      }
    }

    pointerMove(event) {
      if (!this.dragging) {
        return;
      }
      const dx = event.clientX - this.lastX;
      const dy = event.clientY - this.lastY;
      this.lastX = event.clientX;
      this.lastY = event.clientY;
      this.yaw -= dx * 0.008;
      this.pitch = clamp(this.pitch + dy * 0.006, -0.12, 0.86);
    }

    pointerUp(event) {
      this.dragging = false;
      if (this.canvas.releasePointerCapture) {
        try {
          this.canvas.releasePointerCapture(event.pointerId);
        } catch (_error) {
          return;
        }
      }
    }

    zoom(event) {
      event.preventDefault();
      this.distance = clamp(this.distance + event.deltaY * 0.01, 10, 24);
    }

    update(camera, THREE, target, time) {
      const orbitYaw = this.dragging ? this.yaw : this.yaw + Math.sin(time * 0.18) * 0.2;
      const horizontal = Math.cos(this.pitch) * this.distance;
      camera.position.set(
        target.x + Math.sin(orbitYaw) * horizontal,
        target.y + Math.sin(this.pitch) * this.distance,
        target.z + Math.cos(orbitYaw) * horizontal
      );
      camera.lookAt(new THREE.Vector3(target.x, target.y, target.z));
    }

    label() {
      const degrees = Math.round((((this.yaw % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2)) * 180 / Math.PI);
      return `${degrees}°`;
    }
  }

  class ThreeRenderer {
    constructor(targetCanvas, THREE) {
      this.THREE = THREE;
      this.canvas = targetCanvas;
      this.canvas.dataset.renderMode = "webgl";
      this.renderer = new THREE.WebGLRenderer({ canvas: targetCanvas, antialias: true });
      this.renderer.setClearColor(lightMode === "night" ? 0x102340 : 0x70cfff, 1);
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(58, 1, 0.1, 500);
      this.camera.position.set(0, 7.5, 15);
      this.controls = new OrbitControlsLite(targetCanvas);
      this.materials = this.createMaterials();
      this.objectMeshes = [];
      this.clouds = [];
      this.hills = [];
      this.buildStaticScene();
      window.addEventListener("resize", () => this.resize(), { passive: true });
      this.resize();
    }

    createMaterials() {
      const THREE = this.THREE;
      return {
        grass: new THREE.MeshStandardMaterial({ color: 0x4fc35f, roughness: 0.8 }),
        dirt: new THREE.MeshStandardMaterial({ color: 0x764631, roughness: 0.92 }),
        red: new THREE.MeshStandardMaterial({ color: 0xd84b3a, roughness: 0.55 }),
        blue: new THREE.MeshStandardMaterial({ color: 0x315bbd, roughness: 0.5 }),
        skin: new THREE.MeshStandardMaterial({ color: 0xffca9c, roughness: 0.5 }),
        gold: new THREE.MeshStandardMaterial({ color: 0xffd45a, metalness: 0.35, roughness: 0.28 }),
        stone: new THREE.MeshStandardMaterial({ color: 0xd8d4c5, roughness: 0.78 }),
        hazard: new THREE.MeshStandardMaterial({ color: 0x9a4535, roughness: 0.8 }),
        spike: new THREE.MeshStandardMaterial({ color: 0xe4edf5, metalness: 0.2, roughness: 0.35 }),
        energy: new THREE.MeshStandardMaterial({ color: 0x4de27f, emissive: 0x143c20, roughness: 0.3 }),
        dark: new THREE.MeshStandardMaterial({ color: 0x2b1f1a, roughness: 0.62 }),
        white: new THREE.MeshStandardMaterial({ color: 0xfff6e2, roughness: 0.42 }),
        brown: new THREE.MeshStandardMaterial({ color: 0x8f4f2d, roughness: 0.78 }),
        shell: new THREE.MeshStandardMaterial({ color: 0x235b38, roughness: 0.65 }),
        mushroomRed: new THREE.MeshStandardMaterial({ color: 0xd94c3d, roughness: 0.54 }),
        crystal: new THREE.MeshStandardMaterial({ color: 0x74f1ff, emissive: 0x145e68, metalness: 0.18, roughness: 0.18 }),
        portal: new THREE.MeshStandardMaterial({ color: 0x9b65ff, emissive: 0x37206c, roughness: 0.22 }),
        fire: new THREE.MeshStandardMaterial({ color: 0xff7144, emissive: 0x7a1d08, roughness: 0.34 }),
        wing: new THREE.MeshStandardMaterial({ color: 0xf4f7ff, roughness: 0.42 }),
        cloud: new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.35 }),
        hill: new THREE.MeshStandardMaterial({ color: 0x3f935c, roughness: 0.9 }),
        hillDark: new THREE.MeshStandardMaterial({ color: 0x2c6f4b, roughness: 0.94 })
      };
    }

    buildStaticScene() {
      const THREE = this.THREE;
      const hemi = new THREE.HemisphereLight(0xffffff, 0x3d5839, 2.3);
      this.scene.add(hemi);
      const sun = new THREE.DirectionalLight(0xfff4c0, 2.2);
      sun.position.set(-6, 12, 8);
      this.scene.add(sun);

      this.groundGroup = new THREE.Group();
      this.scene.add(this.groundGroup);
      for (let index = 0; index < 28; index += 1) {
        const block = new THREE.Mesh(new THREE.BoxGeometry(8, 0.8, 8), this.materials.dirt);
        block.position.z = -0.4;
        this.groundGroup.add(block);
        const grass = new THREE.Mesh(new THREE.BoxGeometry(8, 0.22, 8), this.materials.grass);
        grass.position.y = 0.52;
        grass.position.z = -0.4;
        this.groundGroup.add(grass);
      }

      this.cloudGroup = new THREE.Group();
      this.scene.add(this.cloudGroup);
      for (let index = 0; index < 8; index += 1) {
        const cloud = this.createCloud();
        cloud.position.set(index * 8 - 18, 9 + (index % 3) * 1.2, -8 - (index % 2) * 5);
        cloud.scale.setScalar(0.7 + (index % 4) * 0.12);
        this.cloudGroup.add(cloud);
        this.clouds.push(cloud);
      }

      this.hillGroup = new THREE.Group();
      this.scene.add(this.hillGroup);
      for (let index = 0; index < 9; index += 1) {
        const hill = new THREE.Mesh(
          new THREE.ConeGeometry(4 + (index % 3), 3.8 + (index % 2), 18),
          index % 2 ? this.materials.hill : this.materials.hillDark
        );
        hill.position.set(index * 9 - 28, 1.1, -12 - (index % 3) * 2);
        hill.rotation.y = Math.PI * 0.25;
        this.hillGroup.add(hill);
        this.hills.push(hill);
      }

      this.player = this.createHero();
      this.scene.add(this.player);

      this.objectGroup = new THREE.Group();
      this.scene.add(this.objectGroup);
      this.castle = this.createCastle();
      this.scene.add(this.castle);
    }

    createCloud() {
      const THREE = this.THREE;
      const cloud = new THREE.Group();
      const blobs = [
        [-0.8, 0, 0.95],
        [0, 0.22, 1.18],
        [0.9, 0, 1.0],
        [1.65, -0.08, 0.72]
      ];
      for (const [x, y, scale] of blobs) {
        const blob = new THREE.Mesh(new THREE.SphereGeometry(scale, 16, 10), this.materials.cloud);
        blob.position.set(x, y, 0);
        blob.scale.y = 0.58;
        cloud.add(blob);
      }
      return cloud;
    }

    createHero() {
      const THREE = this.THREE;
      const hero = new THREE.Group();

      const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.66, 1.05, 18), this.materials.red);
      torso.position.y = 1.12;
      hero.add(torso);
      const overalls = new THREE.Mesh(new THREE.BoxGeometry(1.02, 0.82, 0.62), this.materials.blue);
      overalls.position.y = 0.95;
      hero.add(overalls);

      const head = new THREE.Mesh(new THREE.SphereGeometry(0.48, 24, 18), this.materials.skin);
      head.position.y = 1.95;
      head.scale.z = 0.9;
      hero.add(head);
      const nose = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 10), this.materials.skin);
      nose.position.set(0, 1.93, 0.47);
      hero.add(nose);
      for (const x of [-0.16, 0.16]) {
        const eye = new THREE.Mesh(new THREE.SphereGeometry(0.055, 10, 8), this.materials.dark);
        eye.position.set(x, 2.05, 0.43);
        hero.add(eye);
      }
      for (const x of [-0.17, 0.17]) {
        const mustache = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.08, 0.08), this.materials.dark);
        mustache.position.set(x, 1.78, 0.48);
        mustache.rotation.z = x < 0 ? -0.18 : 0.18;
        hero.add(mustache);
      }

      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.52, 0.46, 0.25, 24), this.materials.red);
      cap.position.y = 2.38;
      hero.add(cap);
      const capBrim = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.1, 0.36), this.materials.red);
      capBrim.position.set(0, 2.28, 0.34);
      hero.add(capBrim);
      const badge = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.035, 16), this.materials.white);
      badge.position.set(0, 2.42, 0.47);
      badge.rotation.x = Math.PI * 0.5;
      hero.add(badge);

      for (const x of [-0.67, 0.67]) {
        const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.13, 0.74, 14), this.materials.red);
        arm.position.set(x, 1.13, 0);
        arm.rotation.z = x < 0 ? -0.28 : 0.28;
        hero.add(arm);
        const glove = new THREE.Mesh(new THREE.SphereGeometry(0.15, 14, 10), this.materials.white);
        glove.position.set(x * 1.08, 0.72, 0.03);
        hero.add(glove);
      }
      for (const x of [-0.28, 0.28]) {
        const leg = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.58, 0.35), this.materials.blue);
        leg.position.set(x, 0.34, 0);
        hero.add(leg);
        const boot = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.18, 0.58), this.materials.dark);
        boot.position.set(x, 0.06, 0.08);
        hero.add(boot);
      }

      hero.scale.setScalar(1.12);
      return hero;
    }

    createCastle() {
      const THREE = this.THREE;
      const castle = new THREE.Group();
      const keep = new THREE.Mesh(new THREE.BoxGeometry(5.5, 6, 3), this.materials.stone);
      keep.position.y = 3;
      castle.add(keep);
      for (const x of [-2.6, 0, 2.6]) {
        const tower = new THREE.Mesh(new THREE.BoxGeometry(1.2, 7.2, 3.4), this.materials.stone);
        tower.position.set(x, 3.6, 0);
        castle.add(tower);
        const roof = new THREE.Mesh(new THREE.ConeGeometry(1.05, 1.5, 4), this.materials.red);
        roof.position.set(x, 7.95, 0);
        roof.rotation.y = Math.PI * 0.25;
        castle.add(roof);
      }
      return castle;
    }

    resize() {
      const width = Math.max(1, this.canvas.clientWidth);
      const height = Math.max(1, this.canvas.clientHeight);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.setSize(width, height, false);
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
    }

    meshFor(index, type) {
      const THREE = this.THREE;
      if (!this.objectMeshes[index]) {
        this.objectMeshes[index] = new THREE.Group();
        this.objectGroup.add(this.objectMeshes[index]);
      }
      const group = this.objectMeshes[index];
      group.visible = true;
      if (group.userData.type !== type) {
        group.clear();
        group.userData.type = type;
        if (type === "coin") {
          group.add(new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.12, 10, 20), this.materials.gold));
        } else if (type === "battery") {
          const battery = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.8, 0.45), this.materials.energy);
          const cap = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.14, 0.24), this.materials.white);
          cap.position.y = 0.48;
          group.add(battery, cap);
        } else if (type === "crystal") {
          const crystal = new THREE.Mesh(new THREE.OctahedronGeometry(0.48, 0), this.materials.crystal);
          crystal.position.y = 0.42;
          group.add(crystal);
        } else if (type === "portal") {
          const ring = new THREE.Mesh(new THREE.TorusGeometry(0.58, 0.08, 12, 28), this.materials.portal);
          ring.rotation.y = Math.PI * 0.5;
          ring.position.y = 0.74;
          const core = new THREE.Mesh(new THREE.SphereGeometry(0.25, 16, 10), this.materials.crystal);
          core.position.y = 0.74;
          group.add(ring, core);
        } else if (type === "spike") {
          group.add(new THREE.Mesh(new THREE.ConeGeometry(0.55, 1.1, 4), this.materials.spike));
        } else if (type === "spring") {
          const spring = new THREE.Mesh(new THREE.TorusGeometry(0.48, 0.08, 8, 16), this.materials.energy);
          spring.rotation.x = Math.PI * 0.5;
          group.add(spring);
        } else if (type === "firebar") {
          const bar = new THREE.Mesh(new THREE.BoxGeometry(0.22, 1.8, 0.22), this.materials.fire);
          bar.position.y = 0.65;
          bar.rotation.z = 0.75;
          const flame = new THREE.Mesh(new THREE.SphereGeometry(0.32, 16, 10), this.materials.fire);
          flame.position.set(0.55, 1.22, 0);
          group.add(bar, flame);
        } else if (type === "winged") {
          const shell = new THREE.Mesh(new THREE.SphereGeometry(0.5, 18, 12), this.materials.shell);
          shell.scale.set(1.15, 0.7, 0.9);
          shell.position.y = 0.42;
          const wingA = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.12, 0.34), this.materials.wing);
          wingA.position.set(-0.55, 0.62, 0);
          wingA.rotation.z = -0.35;
          const wingB = wingA.clone();
          wingB.position.x = 0.55;
          wingB.rotation.z = 0.35;
          group.add(shell, wingA, wingB);
        } else if (type === "turtle") {
          const shell = new THREE.Mesh(new THREE.SphereGeometry(0.55, 18, 12), this.materials.shell);
          shell.scale.set(1.18, 0.72, 0.9);
          shell.position.y = 0.38;
          const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 10), this.materials.white);
          head.position.set(0.52, 0.34, 0);
          const footA = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.14, 0.22), this.materials.dark);
          footA.position.set(-0.28, -0.12, 0.28);
          const footB = footA.clone();
          footB.position.z = -0.28;
          group.add(shell, head, footA, footB);
        } else if (type === "mushroom") {
          const cap = new THREE.Mesh(new THREE.SphereGeometry(0.56, 20, 12), this.materials.mushroomRed);
          cap.scale.y = 0.55;
          cap.position.y = 0.56;
          const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.34, 0.55, 14), this.materials.white);
          stem.position.y = 0.12;
          const spotA = new THREE.Mesh(new THREE.SphereGeometry(0.11, 10, 8), this.materials.white);
          spotA.position.set(-0.2, 0.66, 0.32);
          const spotB = new THREE.Mesh(new THREE.SphereGeometry(0.09, 10, 8), this.materials.white);
          spotB.position.set(0.18, 0.7, 0.34);
          group.add(cap, stem, spotA, spotB);
        } else if (type === "goomba") {
          const body = new THREE.Mesh(new THREE.SphereGeometry(0.48, 18, 12), this.materials.brown);
          body.scale.y = 0.78;
          body.position.y = 0.28;
          const brow = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.08, 0.1), this.materials.dark);
          brow.position.set(0, 0.45, 0.38);
          brow.rotation.z = -0.08;
          const footA = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.16, 0.3), this.materials.dark);
          footA.position.set(-0.28, -0.12, 0.05);
          const footB = footA.clone();
          footB.position.x = 0.28;
          group.add(body, brow, footA, footB);
        } else {
          const gate = new THREE.Mesh(new THREE.BoxGeometry(0.9, type === "gate" ? 2.2 : 1.1, 0.9), this.materials.hazard);
          gate.position.y = type === "gate" ? 0.45 : 0;
          group.add(gate);
        }
      }
      return group;
    }

    render(game) {
      this.resize();
      const THREE = this.THREE;
      const centerX = game.playerWorldX();
      this.controls.update(this.camera, THREE, new THREE.Vector3(6.5, 1.55, 0), game.time);
      if (hud.camera) {
        hud.camera.textContent = this.controls.label();
      }

      this.groundGroup.children.forEach((mesh, index) => {
        const tile = Math.floor(index / 2);
        mesh.position.x = tile * 8 - ((game.distance * 0.75) % 8) - 24;
        mesh.position.y = index % 2 === 0 ? -0.42 : 0.08;
      });

      this.clouds.forEach((cloud, index) => {
        cloud.position.x = index * 8 - ((game.distance * 0.08) % 8) - 18;
        cloud.rotation.y = Math.sin(game.time * 0.16 + index) * 0.08;
      });
      this.hills.forEach((hill, index) => {
        hill.position.x = index * 9 - ((game.distance * 0.18) % 9) - 28;
      });

      this.player.position.set(0, game.player.y / 11, 0);
      this.player.rotation.y = HERO_CORRIDOR_YAW + Math.sin(game.time * game.speed) * 0.05;
      this.player.rotation.z = Math.sin(game.time * game.speed) * 0.04;
      this.player.scale.set(1.12, game.player.duck > 0 ? 0.76 : 1.12, 1.12);

      let meshIndex = 0;
      for (const object of game.objects) {
        if (!object.active) {
          continue;
        }
        const x = (object.x - centerX) * 0.32;
        if (x < -11 || x > 34) {
          continue;
        }
        const group = this.meshFor(meshIndex, object.type);
        group.position.set(x, object.y / 12 + 0.65, object.laneZ || 0);
        group.rotation.y += object.type === "coin" || object.type === "crystal" || object.type === "portal" ? 0.08 : 0;
        if (object.type === "turtle" || object.type === "goomba" || object.type === "mushroom" || object.type === "winged") {
          group.rotation.y = Math.sin(game.time * 2.2 + meshIndex) * 0.18;
        }
        meshIndex += 1;
      }
      for (let index = meshIndex; index < this.objectMeshes.length; index += 1) {
        this.objectMeshes[index].visible = false;
      }

      this.castle.position.set((game.castleX - centerX) * 0.32, 0, -0.8);
      this.castle.visible = this.castle.position.x > -12 && this.castle.position.x < 42;
      const biomeColors = {
        Valle: 0x70cfff,
        Bosque: 0x67c4b6,
        Nubes: 0xaee8ff,
        Volcan: 0x4b3048,
        Castillo: 0x788396
      };
      this.scene.background = new THREE.Color(lightMode === "night" ? 0x12284a : (biomeColors[game.biomeName] || 0x70cfff));
      this.renderer.render(this.scene, this.camera);
    }
  }

  function start(renderer) {
    const game = new Game();
    if (renderer instanceof CanvasRenderer) {
      game.event = "fallback local activo";
    } else {
      game.event = "three.js webgl activo";
    }
    game.updateHud();
    let last = performance.now();
    function frame(now) {
      const dt = (now - last) / 1000;
      last = now;
      game.tick(dt);
      renderer.render(game);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function startFallback() {
    if (window.__castleRunnerStarted) {
      return;
    }
    window.__castleRunnerStarted = true;
    start(new CanvasRenderer(canvas));
  }

  function boot() {
    if (!canvas) {
      return;
    }
    hud.speed.textContent = "4.8 m/s";
    hud.distance.textContent = "0 m";
    canvas.dataset.renderMode = "fallback-2d";

    const fallbackTimer = window.setTimeout(startFallback, 700);
    import("https://unpkg.com/three@0.160.0/build/three.module.js")
      .then((THREE) => {
        if (window.__castleRunnerStarted) {
          return;
        }
        window.clearTimeout(fallbackTimer);
        try {
          const renderer = new ThreeRenderer(canvas, THREE);
          window.__castleRunnerStarted = true;
          start(renderer);
        } catch (_error) {
          startFallback();
        }
      })
      .catch(() => {
        startFallback();
      });
  }

  boot();
})();
