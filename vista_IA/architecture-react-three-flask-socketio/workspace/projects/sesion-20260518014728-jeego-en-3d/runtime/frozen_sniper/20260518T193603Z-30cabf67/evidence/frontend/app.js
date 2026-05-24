import * as THREE from "three";
import { OrbitControls } from "https://cdn.jsdelivr.net/npm/three@0.164.1/examples/jsm/controls/OrbitControls.js";

const MODE_QUERY_KEY = "mode";
const LIGHT_QUERY_KEY = "light";

const MODES = Object.freeze({
  smoke: {
    seed: 3101,
    chunkLength: 34,
    forwardChunks: 8,
    backwardChunks: 2,
    buildingDensity: 4,
    treeDensity: 5,
    obstacleChance: 0.34,
    sensorRange: 54,
    baseSpeed: 15,
    speedLimit: 24,
    trainSteps: 1,
    batchSize: 16,
    replaySize: 500,
    epsilonStart: 0.18,
    epsilonMin: 0.08,
    epsilonDecay: 0.9992,
    targetSync: 160 // prueba externa visual studio code

  },
  build: {
    seed: 7307,
    chunkLength: 34,
    forwardChunks: 13,
    backwardChunks: 3,
    buildingdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddDensity: 6,
    treeDensity: 8,
    obstacleChance: 0.56,
    sensorRange: 68,
    baseSpeed: 18,
    speedLimit: 30,
    trainSteps: 2,
    batchSize: 24,
    replaySize: 1200,
    epsilonStart: 0.24,
    epsilonMin: 0.06,
    epsilonDecay: 0.9991,
    targetSync: 180
  },
  medium: {
    seed: 9113,
    chunkLength: 34,
    forwardChunks: 16,
    backwardChunks: 3,
    buildingDensity: 8,
    treeDensity: 11,
    obstacleChance: 0.72,
    sensorRange: 76,
    baseSpeed: 20,
    speedLimit: 34,
    trainSteps: 3,
    batchSize: 28,
    replaySize: 2200,
    epsilonStart: 0.3,
    epsilonMin: 0.045,
    epsilonDecay: 0.999,
    targetSync: 210
  },
  "long-run": {
    seed: 15331,
    chunkLength: 34,
    forwardChunks: 22,
    backwardChunks: 5,
    buildingDensity: 10,
    treeDensity: 13,
    obstacleChance: 0.86,
    sensorRange: 86,
    baseSpeed: 22,
    speedLimit: 38,
    trainSteps: 5,
    batchSize: 36,
    replaySize: 5000,
    epsilonStart: 0.34,
    epsilonMin: 0.025,
    epsilonDecay: 0.9988,
    targetSync: 240
  }
});

const ACTIONS = Object.freeze([
  { id: "izq", steer: -1, lift: 0, throttle: 0.02 },
  { id: "der", steer: 1, lift: 0, throttle: 0.02 },
  { id: "subir", steer: 0, lift: 1, throttle: 0 },
  { id: "bajar", steer: 0, lift: -1, throttle: 0 },
  { id: "rapido", steer: 0, lift: 0, throttle: 1 },
  { id: "freno", steer: 0, lift: 0, throttle: -1 },
  { id: "recto", steer: 0, lift: 0, throttle: 0.05 }
]);

const INPUT_SIZE = 18;
const DRONE_RADIUS = 1.15;
const DAY_NIGHT_CYCLE_SECONDS = 38;
const FLIGHT_ALERT_MS = 3200;
const EVIDENCE_SCAN_RANGE = 132;
const SCAN_LOCK_SECONDS = 2.6;
const TRAFFIC_LANES = Object.freeze([-9.5, -3.2, 3.2, 9.5]);

const hud = {
  distance: document.querySelector("#distance-value"),
  altitude: document.querySelector("#altitude-value"),
  speed: document.querySelector("#speed-value"),
  episode: document.querySelector("#episode-value"),
  reward: document.querySelector("#reward-value"),
  penalty: document.querySelector("#penalty-value"),
  mode: document.querySelector("#mode-value"),
  policy: document.querySelector("#policy-value"),
  clearance: document.querySelector("#clearance-value"),
  event: document.querySelector("#event-value"),
  alert: document.querySelector("#flight-alert"),
  qBars: document.querySelector("#q-bars"),
  rewardChart: document.querySelector("#reward-chart"),
  modeButtons: [...document.querySelectorAll("[data-mode]")],
  targetKind: document.querySelector("#target-kind-value"),
  targetId: document.querySelector("#target-id-value"),
  targetDetail: document.querySelector("#target-detail-value"),
  targetZoom: document.querySelector("#target-zoom-value"),
  targetConfidence: document.querySelector("#target-confidence-value"),
  targetLock: document.querySelector("#target-lock-value"),
  reticle: document.querySelector("#scanner-reticle")
};

function start() {
  boot();
}

function boot() {
  const modeName = readExplicitMode();
  hud.mode.textContent = modeName;
  try {
    new DroneGame(modeName);
  } catch (error) {
    hud.event.textContent = `error webgl: ${error.message}`;
    console.error(error);
  }
}

function readExplicitMode() {
  const requested = new URLSearchParams(window.location.search).get(MODE_QUERY_KEY);
  return Object.prototype.hasOwnProperty.call(MODES, requested) ? requested : "build";
}

function readExplicitLightMode() {
  const requested = new URLSearchParams(window.location.search).get(LIGHT_QUERY_KEY);
  return requested === "day" || requested === "night" ? requested : "auto";
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function randRange(rand, min, max) {
  return lerp(min, max, rand());
}

function mulberry32(seed) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makeLabelTexture(text, options = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = options.width || 256;
  canvas.height = options.height || 96;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = options.background || "#f1f4e8";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = options.border || "#101614";
  ctx.lineWidth = 8;
  ctx.strokeRect(4, 4, canvas.width - 8, canvas.height - 8);
  ctx.fillStyle = options.color || "#101614";
  ctx.font = `800 ${options.fontSize || 38}px ui-sans-serif, system-ui, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width * 0.5, canvas.height * 0.54);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

function makeBounds(center, size) {
  return {
    min: new THREE.Vector3(
      center.x - size.x * 0.5,
      center.y - size.y * 0.5,
      center.z - size.z * 0.5
    ),
    max: new THREE.Vector3(
      center.x + size.x * 0.5,
      center.y + size.y * 0.5,
      center.z + size.z * 0.5
    )
  };
}

function sphereIntersectsAabb(center, radius, bounds) {
  const x = clamp(center.x, bounds.min.x, bounds.max.x);
  const y = clamp(center.y, bounds.min.y, bounds.max.y);
  const z = clamp(center.z, bounds.min.z, bounds.max.z);
  const dx = center.x - x;
  const dy = center.y - y;
  const dz = center.z - z;
  return dx * dx + dy * dy + dz * dz <= radius * radius;
}

class DenseNetwork {
  constructor(inputSize, hiddenSize, outputSize, rand) {
    this.inputSize = inputSize;
    this.hiddenSize = hiddenSize;
    this.outputSize = outputSize;
    this.w1 = Array.from({ length: hiddenSize }, () =>
      Array.from({ length: inputSize }, () => randRange(rand, -0.24, 0.24))
    );
    this.b1 = Array.from({ length: hiddenSize }, () => randRange(rand, -0.04, 0.04));
    this.w2 = Array.from({ length: outputSize }, () =>
      Array.from({ length: hiddenSize }, () => randRange(rand, -0.18, 0.18))
    );
    this.b2 = Array.from({ length: outputSize }, () => randRange(rand, -0.02, 0.02));
  }

  copyFrom(other) {
    for (let h = 0; h < this.hiddenSize; h += 1) {
      this.b1[h] = other.b1[h];
      for (let i = 0; i < this.inputSize; i += 1) {
        this.w1[h][i] = other.w1[h][i];
      }
    }
    for (let a = 0; a < this.outputSize; a += 1) {
      this.b2[a] = other.b2[a];
      for (let h = 0; h < this.hiddenSize; h += 1) {
        this.w2[a][h] = other.w2[a][h];
      }
    }
  }

  predict(input) {
    const hidden = new Array(this.hiddenSize);
    for (let h = 0; h < this.hiddenSize; h += 1) {
      let sum = this.b1[h];
      for (let i = 0; i < this.inputSize; i += 1) {
        sum += this.w1[h][i] * input[i];
      }
      hidden[h] = Math.max(0, sum);
    }

    const q = new Array(this.outputSize);
    for (let a = 0; a < this.outputSize; a += 1) {
      let sum = this.b2[a];
      for (let h = 0; h < this.hiddenSize; h += 1) {
        sum += this.w2[a][h] * hidden[h];
      }
      q[a] = clamp(sum, -30, 30);
    }
    return { hidden, q };
  }

  train(input, actionIndex, target, learningRate) {
    const { hidden, q } = this.predict(input);
    const error = clamp(q[actionIndex] - target, -5, 5);
    const oldOutputWeights = this.w2[actionIndex].slice();

    for (let h = 0; h < this.hiddenSize; h += 1) {
      this.w2[actionIndex][h] -= learningRate * error * hidden[h];
    }
    this.b2[actionIndex] -= learningRate * error;

    for (let h = 0; h < this.hiddenSize; h += 1) {
      if (hidden[h] <= 0) continue;
      const hiddenError = error * oldOutputWeights[h];
      for (let i = 0; i < this.inputSize; i += 1) {
        this.w1[h][i] -= learningRate * hiddenError * input[i];
      }
      this.b1[h] -= learningRate * hiddenError;
    }
  }
}

class ReplayBuffer {
  constructor(limit) {
    this.limit = limit;
    this.samples = [];
    this.index = 0;
  }

  push(sample) {
    if (this.samples.length < this.limit) {
      this.samples.push(sample);
      return;
    }
    this.samples[this.index] = sample;
    this.index = (this.index + 1) % this.limit;
  }

  sample(count) {
    const batch = [];
    for (let i = 0; i < count; i += 1) {
      batch.push(this.samples[Math.floor(Math.random() * this.samples.length)]);
    }
    return batch;
  }
}

class DqnAgent {
  constructor(config) {
    const rand = mulberry32(config.seed + 404);
    this.online = new DenseNetwork(INPUT_SIZE, 32, ACTIONS.length, rand);
    this.target = new DenseNetwork(INPUT_SIZE, 32, ACTIONS.length, rand);
    this.target.copyFrom(this.online);
    this.replay = new ReplayBuffer(config.replaySize);
    this.gamma = 0.92;
    this.learningRate = 0.0028;
    this.epsilon = config.epsilonStart;
    this.epsilonMin = config.epsilonMin;
    this.epsilonDecay = config.epsilonDecay;
    this.batchSize = config.batchSize;
    this.trainSteps = config.trainSteps;
    this.targetSync = config.targetSync;
    this.steps = 0;
    this.lastQ = new Array(ACTIONS.length).fill(0);
    this.lastAction = ACTIONS.length - 1;
    this.exploring = true;
  }

  act(state, safetyBias) {
    const q = this.online.predict(state).q;
    const adjusted = q.map((value, index) => value + safetyBias[index]);
    const useExplore = Math.random() < this.epsilon;
    let actionIndex;
    if (useExplore) {
      actionIndex = this.pickExploration(adjusted);
    } else {
      actionIndex = argmax(adjusted);
    }
    this.lastQ = adjusted;
    this.lastAction = actionIndex;
    this.exploring = useExplore;
    return actionIndex;
  }

  pickExploration(adjusted) {
    const ranked = adjusted
      .map((value, index) => ({ value, index }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 3);
    return ranked[Math.floor(Math.random() * ranked.length)].index;
  }

  remember(sample) {
    this.replay.push(sample);
  }

  learn() {
    if (this.replay.samples.length < this.batchSize) return;

    for (let i = 0; i < this.trainSteps; i += 1) {
      const batch = this.replay.sample(this.batchSize);
      for (const item of batch) {
        const nextQ = this.target.predict(item.nextState).q;
        const targetValue = item.done ? item.reward : item.reward + this.gamma * Math.max(...nextQ);
        this.online.train(item.state, item.action, targetValue, this.learningRate);
      }
    }

    this.steps += 1;
    this.epsilon = Math.max(this.epsilonMin, this.epsilon * this.epsilonDecay);
    if (this.steps % this.targetSync === 0) {
      this.target.copyFrom(this.online);
    }
  }
}

function argmax(values) {
  let bestIndex = 0;
  let bestValue = values[0];
  for (let i = 1; i < values.length; i += 1) {
    if (values[i] > bestValue) {
      bestIndex = i;
      bestValue = values[i];
    }
  }
  return bestIndex;
}

class ProceduralCity {
  constructor(scene, config) {
    this.scene = scene;
    this.config = config;
    this.rand = mulberry32(config.seed);
    this.chunks = [];
    this.obstacles = [];
    this.trafficActors = [];
    this.pedestrianActors = [];
    this.scanTargets = [];
    this.nextZ = -config.chunkLength * config.backwardChunks;
    this.materials = {
      road: new THREE.MeshStandardMaterial({ color: 0x1f2421, roughness: 0.92 }),
      lane: new THREE.MeshBasicMaterial({ color: 0x9ba69d, transparent: true, opacity: 0.45 }),
      buildingA: new THREE.MeshStandardMaterial({ color: 0x2f3d3b, roughness: 0.65, metalness: 0.08 }),
      buildingB: new THREE.MeshStandardMaterial({ color: 0x3f342e, roughness: 0.72, metalness: 0.04 }),
      glass: new THREE.MeshStandardMaterial({ color: 0x204650, roughness: 0.35, metalness: 0.2 }),
      windowLit: new THREE.MeshStandardMaterial({
        color: 0xf5e7b0,
        emissive: 0xf5bb4c,
        emissiveIntensity: 0.65,
        roughness: 0.28,
        metalness: 0.08,
        side: THREE.DoubleSide
      }),
      windowDim: new THREE.MeshStandardMaterial({
        color: 0x1c3b45,
        emissive: 0x071217,
        emissiveIntensity: 0.25,
        roughness: 0.42,
        metalness: 0.16,
        side: THREE.DoubleSide
      }),
      trunk: new THREE.MeshStandardMaterial({ color: 0x4b3326, roughness: 0.85 }),
      leaves: new THREE.MeshStandardMaterial({ color: 0x2f7f4f, roughness: 0.82 }),
      hazard: new THREE.MeshStandardMaterial({ color: 0xf6b94b, roughness: 0.6, metalness: 0.2 }),
      asphaltCurb: new THREE.MeshStandardMaterial({ color: 0x2d332f, roughness: 0.96 }),
      trafficRed: new THREE.MeshStandardMaterial({
        color: 0xff3030,
        emissive: 0xff1010,
        emissiveIntensity: 1.25
      }),
      trafficGreen: new THREE.MeshStandardMaterial({
        color: 0x54ff5d,
        emissive: 0x20c820,
        emissiveIntensity: 1.1
      }),
      carBlue: new THREE.MeshStandardMaterial({ color: 0x1b5a96, roughness: 0.48, metalness: 0.28 }),
      carYellow: new THREE.MeshStandardMaterial({ color: 0xd6a224, roughness: 0.45, metalness: 0.2 }),
      carRed: new THREE.MeshStandardMaterial({ color: 0x982d2d, roughness: 0.5, metalness: 0.25 }),
      carBlack: new THREE.MeshStandardMaterial({ color: 0x111514, roughness: 0.38, metalness: 0.5 }),
      windshield: new THREE.MeshStandardMaterial({
        color: 0x83d8f7,
        transparent: true,
        opacity: 0.52,
        roughness: 0.18,
        metalness: 0.22
      }),
      tire: new THREE.MeshStandardMaterial({ color: 0x080909, roughness: 0.9 }),
      skin: new THREE.MeshStandardMaterial({ color: 0xd7a078, roughness: 0.55 }),
      personA: new THREE.MeshStandardMaterial({ color: 0x2e7bbd, roughness: 0.72 }),
      personB: new THREE.MeshStandardMaterial({ color: 0x8d3b6b, roughness: 0.72 }),
      personC: new THREE.MeshStandardMaterial({ color: 0x4d7a3a, roughness: 0.72 })
    };

    this.geometries = {
      road: new THREE.PlaneGeometry(34, config.chunkLength),
      lane: new THREE.PlaneGeometry(0.16, config.chunkLength * 0.82),
      cube: new THREE.BoxGeometry(1, 1, 1),
      window: new THREE.PlaneGeometry(0.72, 1.08),
      sidewalk: new THREE.BoxGeometry(1, 0.16, 1),
      carBody: new THREE.BoxGeometry(2.3, 0.72, 4.3),
      carCabin: new THREE.BoxGeometry(1.55, 0.78, 1.85),
      wheel: new THREE.CylinderGeometry(0.28, 0.28, 0.22, 16),
      plate: new THREE.PlaneGeometry(1.14, 0.38),
      pedestrianBody: new THREE.CylinderGeometry(0.22, 0.28, 1.15, 10),
      pedestrianHead: new THREE.SphereGeometry(0.28, 16, 12),
      pedestrianLeg: new THREE.BoxGeometry(0.12, 0.62, 0.14),
      trunk: new THREE.CylinderGeometry(0.28, 0.34, 1, 8),
      leaves: new THREE.ConeGeometry(1.2, 2.7, 9),
      pole: new THREE.CylinderGeometry(0.38, 0.38, 1, 12)
    };

    this.ground = new THREE.Mesh(
      new THREE.PlaneGeometry(900, 900),
      new THREE.MeshStandardMaterial({ color: 0x182019, roughness: 1 })
    );
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.position.y = -0.04;
    this.ground.receiveShadow = true;
    scene.add(this.ground);
  }

  reset(modeConfig) {
    this.config = modeConfig;
    this.rand = mulberry32(modeConfig.seed);
    for (const chunk of this.chunks) {
      this.scene.remove(chunk.group);
    }
    this.chunks = [];
    this.obstacles = [];
    this.trafficActors = [];
    this.pedestrianActors = [];
    this.scanTargets = [];
    this.nextZ = -modeConfig.chunkLength * modeConfig.backwardChunks;
    this.ensureAhead(0);
  }

  ensureAhead(droneZ) {
    const ahead = droneZ + this.config.forwardChunks * this.config.chunkLength;
    while (this.nextZ < ahead) {
      this.createChunk(this.nextZ);
      this.nextZ += this.config.chunkLength;
    }

    const behind = droneZ - this.config.backwardChunks * this.config.chunkLength;
    while (this.chunks.length && this.chunks[0].z + this.config.chunkLength < behind) {
      const old = this.chunks.shift();
      this.scene.remove(old.group);
      this.obstacles = this.obstacles.filter((obstacle) => obstacle.chunkId !== old.id);
      this.trafficActors = this.trafficActors.filter((actor) => actor.chunkId !== old.id);
      this.pedestrianActors = this.pedestrianActors.filter((actor) => actor.chunkId !== old.id);
      this.scanTargets = this.scanTargets.filter((target) => target.chunkId !== old.id);
    }

    this.ground.position.z = Math.round(droneZ / 300) * 300;
  }

  createChunk(zStart) {
    const group = new THREE.Group();
    const chunkId = `${zStart.toFixed(2)}-${this.chunks.length}`;

    const road = new THREE.Mesh(this.geometries.road, this.materials.road);
    road.rotation.x = -Math.PI / 2;
    road.position.set(0, 0, zStart + this.config.chunkLength * 0.5);
    road.receiveShadow = true;
    group.add(road);

    for (const laneX of [-8, 0, 8]) {
      const lane = new THREE.Mesh(this.geometries.lane, this.materials.lane);
      lane.rotation.x = -Math.PI / 2;
      lane.position.set(laneX, 0.015, zStart + this.config.chunkLength * 0.5);
      group.add(lane);
    }

    this.addBuildings(group, chunkId, zStart);
    this.addStreetDetails(group, chunkId, zStart);
    this.addTraffic(group, chunkId, zStart);
    this.addPedestrians(group, chunkId, zStart);
    this.addTrees(group, chunkId, zStart);
    this.addFlightHazard(group, chunkId, zStart);

    this.scene.add(group);
    this.chunks.push({ id: chunkId, z: zStart, group });
  }

  addBuildings(group, chunkId, zStart) {
    for (const side of [-1, 1]) {
      for (let i = 0; i < this.config.buildingDensity; i += 1) {
        const width = randRange(this.rand, 5, 14);
        const depth = randRange(this.rand, 6, 16);
        const height = randRange(this.rand, 12, 58);
        const x = side * randRange(this.rand, 25, 78);
        const z = zStart + randRange(this.rand, 2, this.config.chunkLength - 2);
        const y = height * 0.5;
        const mesh = new THREE.Mesh(
          this.geometries.cube,
          this.rand() > 0.45 ? this.materials.buildingA : this.materials.buildingB
        );
        mesh.scale.set(width, height, depth);
        mesh.position.set(x, y, z);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        group.add(mesh);

        const glass = new THREE.Mesh(this.geometries.cube, this.materials.glass);
        glass.scale.set(width * 1.01, height * 0.92, 0.08);
        glass.position.set(x, y + 0.8, z - depth * 0.51);
        group.add(glass);
        this.addWindowGrid(group, mesh.position, { width, height, depth, side });

        this.obstacles.push({
          chunkId,
          type: "building",
          bounds: makeBounds(new THREE.Vector3(x, y, z), new THREE.Vector3(width, height, depth)),
          passed: false
        });
      }
    }
  }

  addWindowGrid(group, center, size) {
    const dummy = new THREE.Object3D();
    const litMatrices = [];
    const dimMatrices = [];
    const floorCount = Math.max(2, Math.floor((size.height - 4) / 3.1));
    const frontColumns = Math.max(2, Math.floor(size.width / 1.65));
    const sideColumns = Math.max(2, Math.floor(size.depth / 1.9));

    const pushWindow = (x, y, z, rotationY) => {
      dummy.position.set(x, y, z);
      dummy.rotation.set(0, rotationY, 0);
      dummy.scale.setScalar(randRange(this.rand, 0.82, 1.12));
      dummy.updateMatrix();
      (this.rand() > 0.34 ? litMatrices : dimMatrices).push(dummy.matrix.clone());
    };

    for (let floor = 0; floor < floorCount; floor += 1) {
      const y = 2.5 + floor * 3.1;
      for (let col = 0; col < frontColumns; col += 1) {
        const t = frontColumns === 1 ? 0.5 : col / (frontColumns - 1);
        const x = center.x - size.width * 0.36 + t * size.width * 0.72;
        pushWindow(x, y, center.z - size.depth * 0.515, Math.PI);
        pushWindow(x, y, center.z + size.depth * 0.515, 0);
      }
      for (let col = 0; col < sideColumns; col += 1) {
        const t = sideColumns === 1 ? 0.5 : col / (sideColumns - 1);
        const z = center.z - size.depth * 0.34 + t * size.depth * 0.68;
        pushWindow(center.x - size.width * 0.515, y, z, -Math.PI / 2);
        pushWindow(center.x + size.width * 0.515, y, z, Math.PI / 2);
      }
    }

    for (const [matrices, material] of [
      [litMatrices, this.materials.windowLit],
      [dimMatrices, this.materials.windowDim]
    ]) {
      if (!matrices.length) continue;
      const windows = new THREE.InstancedMesh(this.geometries.window, material, matrices.length);
      matrices.forEach((matrix, index) => windows.setMatrixAt(index, matrix));
      windows.instanceMatrix.needsUpdate = true;
      group.add(windows);
    }
  }

  addStreetDetails(group, chunkId, zStart) {
    for (const side of [-1, 1]) {
      const sidewalk = new THREE.Mesh(this.geometries.sidewalk, this.materials.asphaltCurb);
      sidewalk.scale.set(5.2, 1, this.config.chunkLength);
      sidewalk.position.set(side * 19.6, 0.04, zStart + this.config.chunkLength * 0.5);
      sidewalk.receiveShadow = true;
      group.add(sidewalk);

      if (this.rand() > 0.44) {
        const lightPole = new THREE.Mesh(this.geometries.pole, this.materials.hazard);
        lightPole.scale.set(0.28, 8.5, 0.28);
        lightPole.position.set(side * 14.8, 4.25, zStart + randRange(this.rand, 4, this.config.chunkLength - 4));
        lightPole.castShadow = true;
        group.add(lightPole);

        const lamp = new THREE.PointLight(0xffe5a0, 0.7, 28, 2);
        lamp.position.set(side * 14.8, 8.8, lightPole.position.z);
        group.add(lamp);
      }
    }

    if (Math.abs(Math.round(zStart / this.config.chunkLength)) % 3 === 0) {
      const crosswalkZ = zStart + this.config.chunkLength * 0.5;
      for (let i = -4; i <= 4; i += 1) {
        const stripe = new THREE.Mesh(this.geometries.cube, this.materials.lane);
        stripe.scale.set(1.3, 0.035, 8.8);
        stripe.position.set(i * 3.2, 0.04, crosswalkZ);
        group.add(stripe);
      }

      for (const side of [-1, 1]) {
        const signal = new THREE.Group();
        signal.position.set(side * 14.2, 0, crosswalkZ - 8);
        const pole = new THREE.Mesh(this.geometries.pole, this.materials.carBlack);
        pole.scale.set(0.18, 5.2, 0.18);
        pole.position.y = 2.6;
        signal.add(pole);

        const red = new THREE.Mesh(new THREE.SphereGeometry(0.32, 14, 10), this.materials.trafficRed);
        red.position.set(0, 5.6, 0);
        signal.add(red);
        const green = new THREE.Mesh(new THREE.SphereGeometry(0.32, 14, 10), this.materials.trafficGreen);
        green.position.set(0, 4.72, 0);
        signal.add(green);
        group.add(signal);
      }
    }
  }

  addTraffic(group, chunkId, zStart) {
    const count = Math.max(2, Math.floor(this.config.buildingDensity * 0.72));
    const carMaterials = [this.materials.carBlue, this.materials.carYellow, this.materials.carRed, this.materials.carBlack];

    for (let i = 0; i < count; i += 1) {
      const laneIndex = Math.floor(this.rand() * TRAFFIC_LANES.length);
      const laneX = TRAFFIC_LANES[laneIndex];
      const direction = laneIndex < TRAFFIC_LANES.length * 0.5 ? 1 : -1;
      const z = zStart + randRange(this.rand, 2, this.config.chunkLength - 2);
      const plateCode = `ND-${Math.floor(randRange(this.rand, 100, 999))}${String.fromCharCode(65 + Math.floor(this.rand() * 26))}`;
      const vehicle = this.createVehicle(plateCode, carMaterials[i % carMaterials.length]);
      vehicle.position.set(laneX, 0, z);
      vehicle.rotation.y = direction < 0 ? Math.PI : 0;
      group.add(vehicle);

      const actor = {
        chunkId,
        type: "car",
        group: vehicle,
        speed: direction * randRange(this.rand, 4.6, 10.8),
        zMin: zStart + 1.5,
        zMax: zStart + this.config.chunkLength - 1.5,
        bounds: makeBounds(new THREE.Vector3(laneX, 0.85, z), new THREE.Vector3(2.7, 1.8, 4.8)),
        scanId: plateCode
      };
      this.trafficActors.push(actor);
      this.scanTargets.push({
        chunkId,
        kind: "placa",
        id: plateCode,
        detail: `placa vehicular en carril ${laneIndex + 1}`,
        object: vehicle.userData.plate,
        actor,
        priority: 1.08
      });
    }
  }

  createVehicle(plateCode, bodyMaterial) {
    const vehicle = new THREE.Group();
    const body = new THREE.Mesh(this.geometries.carBody, bodyMaterial);
    body.position.y = 0.66;
    body.castShadow = true;
    body.receiveShadow = true;
    vehicle.add(body);

    const cabin = new THREE.Mesh(this.geometries.carCabin, this.materials.windshield);
    cabin.position.set(0, 1.18, -0.2);
    cabin.castShadow = true;
    vehicle.add(cabin);

    for (const x of [-1.22, 1.22]) {
      for (const z of [-1.48, 1.48]) {
        const wheel = new THREE.Mesh(this.geometries.wheel, this.materials.tire);
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(x, 0.38, z);
        wheel.castShadow = true;
        vehicle.add(wheel);
      }
    }

    const plateTexture = makeLabelTexture(plateCode, { width: 192, height: 64, fontSize: 32 });
    const plate = new THREE.Mesh(
      this.geometries.plate,
      new THREE.MeshBasicMaterial({ map: plateTexture, side: THREE.DoubleSide })
    );
    plate.position.set(0, 0.62, -2.18);
    plate.rotation.y = Math.PI;
    vehicle.add(plate);
    vehicle.userData.plate = plate;
    return vehicle;
  }

  addPedestrians(group, chunkId, zStart) {
    const count = Math.max(3, Math.floor(this.config.treeDensity * 0.42));
    const clothes = [this.materials.personA, this.materials.personB, this.materials.personC];

    for (let i = 0; i < count; i += 1) {
      const sidewalkSide = this.rand() > 0.5 ? 1 : -1;
      const onCrosswalk = this.rand() > 0.72;
      const personId = `FACE-${Math.floor(Math.abs(zStart) + i * 17)}`;
      const person = this.createPedestrian(clothes[i % clothes.length]);
      person.position.set(
        onCrosswalk ? randRange(this.rand, -12, 12) : sidewalkSide * randRange(this.rand, 17.2, 21.5),
        0,
        zStart + randRange(this.rand, 2, this.config.chunkLength - 2)
      );
      group.add(person);

      const actor = {
        chunkId,
        type: "person",
        group: person,
        axis: onCrosswalk ? "x" : "z",
        speed: (this.rand() > 0.5 ? 1 : -1) * randRange(this.rand, 0.7, 1.8),
        min: onCrosswalk ? -13.2 : zStart + 1.2,
        max: onCrosswalk ? 13.2 : zStart + this.config.chunkLength - 1.2,
        phase: this.rand() * Math.PI * 2,
        bounds: makeBounds(new THREE.Vector3(person.position.x, 1, person.position.z), new THREE.Vector3(0.85, 2.1, 0.85)),
        scanId: personId
      };
      this.pedestrianActors.push(actor);
      this.scanTargets.push({
        chunkId,
        kind: "rostro",
        id: personId,
        detail: onCrosswalk ? "rostro de peaton cruzando" : "rostro de peaton en acera",
        object: person.userData.head,
        actor,
        priority: 1.16
      });
    }
  }

  createPedestrian(clothingMaterial) {
    const person = new THREE.Group();
    const body = new THREE.Mesh(this.geometries.pedestrianBody, clothingMaterial);
    body.position.y = 1.04;
    body.castShadow = true;
    person.add(body);

    const head = new THREE.Mesh(this.geometries.pedestrianHead, this.materials.skin);
    head.position.y = 1.84;
    head.castShadow = true;
    person.add(head);

    const eyes = new THREE.Mesh(
      new THREE.PlaneGeometry(0.24, 0.08),
      new THREE.MeshBasicMaterial({ color: 0x121212, side: THREE.DoubleSide })
    );
    eyes.position.set(0, 1.89, 0.275);
    person.add(eyes);

    const legs = [];
    for (const x of [-0.12, 0.12]) {
      const leg = new THREE.Mesh(this.geometries.pedestrianLeg, this.materials.carBlack);
      leg.position.set(x, 0.36, 0);
      leg.castShadow = true;
      person.add(leg);
      legs.push(leg);
    }
    person.userData.head = head;
    person.userData.legs = legs;
    return person;
  }

  updateDynamicActors(dt) {
    for (const actor of this.trafficActors) {
      actor.group.position.z += actor.speed * dt;
      if (actor.group.position.z > actor.zMax) actor.group.position.z = actor.zMin;
      if (actor.group.position.z < actor.zMin) actor.group.position.z = actor.zMax;
      actor.bounds = makeBounds(
        new THREE.Vector3(actor.group.position.x, 0.85, actor.group.position.z),
        new THREE.Vector3(2.7, 1.8, 4.8)
      );
    }

    for (const actor of this.pedestrianActors) {
      actor.group.position[actor.axis] += actor.speed * dt;
      if (actor.group.position[actor.axis] > actor.max) actor.group.position[actor.axis] = actor.min;
      if (actor.group.position[actor.axis] < actor.min) actor.group.position[actor.axis] = actor.max;
      actor.group.rotation.y = actor.axis === "x" ? Math.sign(actor.speed) * Math.PI * 0.5 : actor.speed < 0 ? Math.PI : 0;
      const stride = Math.sin(performance.now() * 0.008 + actor.phase) * 0.55;
      actor.group.userData.legs[0].rotation.x = stride;
      actor.group.userData.legs[1].rotation.x = -stride;
      actor.bounds = makeBounds(
        new THREE.Vector3(actor.group.position.x, 1, actor.group.position.z),
        new THREE.Vector3(0.85, 2.1, 0.85)
      );
    }
  }

  getCollisionObstacles() {
    const traffic = this.trafficActors.map((actor) => ({
      chunkId: actor.chunkId,
      type: "car",
      dynamic: true,
      bounds: actor.bounds,
      passed: true
    }));
    const pedestrians = this.pedestrianActors.map((actor) => ({
      chunkId: actor.chunkId,
      type: "person",
      dynamic: true,
      bounds: actor.bounds,
      passed: true
    }));
    return [...this.obstacles, ...traffic, ...pedestrians];
  }

  addTrees(group, chunkId, zStart) {
    for (const side of [-1, 1]) {
      for (let i = 0; i < this.config.treeDensity; i += 1) {
        const x = side * randRange(this.rand, 13.5, 22);
        const z = zStart + randRange(this.rand, 1, this.config.chunkLength - 1);
        const height = randRange(this.rand, 5.4, 10.5);
        const tree = new THREE.Group();
        tree.position.set(x, 0, z);

        const trunk = new THREE.Mesh(this.geometries.trunk, this.materials.trunk);
        trunk.scale.set(1, height * 0.5, 1);
        trunk.position.y = height * 0.25;
        trunk.castShadow = true;
        tree.add(trunk);

        const leaves = new THREE.Mesh(this.geometries.leaves, this.materials.leaves);
        leaves.scale.set(1.4, height * 0.42, 1.4);
        leaves.position.y = height * 0.72;
        leaves.castShadow = true;
        tree.add(leaves);
        group.add(tree);

        this.obstacles.push({
          chunkId,
          type: "tree",
          bounds: {
            min: new THREE.Vector3(x - 1.7, 0, z - 1.7),
            max: new THREE.Vector3(x + 1.7, height + 1.2, z + 1.7)
          },
          passed: false
        });
      }
    }
  }

  addFlightHazard(group, chunkId, zStart) {
    if (zStart < 55 || this.rand() > this.config.obstacleChance) return;

    const z = zStart + randRange(this.rand, 8, this.config.chunkLength - 5);
    const variant = this.rand();
    if (variant < 0.34) {
      const width = randRange(this.rand, 5.5, 10);
      const depth = randRange(this.rand, 4, 7);
      const height = randRange(this.rand, 10, 24);
      const x = randRange(this.rand, -11, 11);
      const y = height * 0.5;
      const block = new THREE.Mesh(this.geometries.cube, this.materials.hazard);
      block.scale.set(width, height, depth);
      block.position.set(x, y, z);
      block.castShadow = true;
      group.add(block);
      this.obstacles.push({
        chunkId,
        type: "central-block",
        bounds: makeBounds(new THREE.Vector3(x, y, z), new THREE.Vector3(width, height, depth)),
        passed: false
      });
      return;
    }

    if (variant < 0.68) {
      const gapX = randRange(this.rand, -5.5, 5.5);
      const gapWidth = randRange(this.rand, 7, 10);
      for (const side of [-1, 1]) {
        const width = randRange(this.rand, 3.2, 5.2);
        const x = gapX + side * (gapWidth + width) * 0.5;
        const height = randRange(this.rand, 17, 30);
        const pole = new THREE.Mesh(this.geometries.pole, this.materials.hazard);
        pole.scale.set(width, height, width);
        pole.position.set(x, height * 0.5, z);
        pole.castShadow = true;
        group.add(pole);
        this.obstacles.push({
          chunkId,
          type: "gate-pole",
          bounds: makeBounds(new THREE.Vector3(x, height * 0.5, z), new THREE.Vector3(width, height, width)),
          passed: false
        });
      }
      const beam = new THREE.Mesh(this.geometries.cube, this.materials.hazard);
      beam.scale.set(gapWidth + 10, 1.2, 1.2);
      beam.position.set(gapX, randRange(this.rand, 18, 28), z);
      group.add(beam);
      this.obstacles.push({
        chunkId,
        type: "gate-beam",
        bounds: makeBounds(beam.position, new THREE.Vector3(gapWidth + 10, 1.2, 1.2)),
        passed: false
      });
      return;
    }

    const lowY = randRange(this.rand, 6, 11);
    const highY = lowY + randRange(this.rand, 9, 14);
    for (const y of [lowY, highY]) {
      const slab = new THREE.Mesh(this.geometries.cube, this.materials.hazard);
      slab.scale.set(randRange(this.rand, 16, 24), 1.4, 2.2);
      slab.position.set(randRange(this.rand, -2, 2), y, z);
      slab.castShadow = true;
      group.add(slab);
      this.obstacles.push({
        chunkId,
        type: "air-slab",
        bounds: makeBounds(slab.position, new THREE.Vector3(slab.scale.x, 1.4, 2.2)),
        passed: false
      });
    }
  }
}

class DroneGame {
  constructor(modeName) {
    this.modeName = modeName;
    this.config = MODES[modeName];
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0d0c);
    this.scene.fog = new THREE.FogExp2(0x0a0d0c, 0.012);

    this.renderer = new THREE.WebGLRenderer({
      canvas: document.querySelector("#world"),
      antialias: true,
      alpha: false
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.camera = new THREE.PerspectiveCamera(62, 1, 0.1, 900);
    this.clock = new THREE.Clock();
    this.rewardHistory = new Array(80).fill(0);
    this.chartContext = hud.rewardChart.getContext("2d");
    this.city = new ProceduralCity(this.scene, this.config);
    this.agent = new DqnAgent(this.config);
    this.velocity = new THREE.Vector3(0, 0, this.config.baseSpeed);
    this.drone = this.createDrone();
    this.scene.add(this.drone);
    this.evidenceTools = this.createEvidenceTools();
    this.rotors = this.drone.userData.rotors;
    this.controls = this.createOrbitControls();
    this.episode = 1;
    this.totalReward = 0;
    this.totalPenalty = 0;
    this.lastReward = 0;
    this.lastPenalty = 0;
    this.lastScan = null;
    this.previousState = null;
    this.previousAction = ACTIONS.length - 1;
    this.lastEvent = "ciudad procedural activa";
    this.startZ = 0;
    this.orbitHoldUntil = 0;
    this.lightCycleTime = 0;
    this.lightMode = "noche: faro frontal";
    this.lightOverride = readExplicitLightMode();
    this.flightAlert = { type: "neutral", message: "", until: 0 };
    this.evidenceFocus = null;
    this.scanLock = 0;
    this.scanSnapshot = {
      kind: "sin target",
      id: "NEURODRIVER-SEARCH",
      detail: "buscando rostro o placa",
      confidence: 0,
      zoom: 1
    };
    this.skyNight = new THREE.Color(0x070b12);
    this.skyDay = new THREE.Color(0x8ec7df);
    this.fogNight = new THREE.Color(0x070b12);
    this.fogDay = new THREE.Color(0xa9d6db);

    this.addLighting();
    this.bindModes();
    this.buildQBars();
    this.reset(false);
    this.resize();
    window.addEventListener("resize", () => this.resize());
    this.renderer.setAnimationLoop(() => this.update());
  }

  addLighting() {
    const hemi = new THREE.HemisphereLight(0xd7fff7, 0x1a1d17, 1.6);
    this.scene.add(hemi);

    const sun = new THREE.DirectionalLight(0xfff1c9, 2.2);
    sun.position.set(-60, 86, -42);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    sun.shadow.camera.left = -120;
    sun.shadow.camera.right = 120;
    sun.shadow.camera.top = 120;
    sun.shadow.camera.bottom = -120;
    this.scene.add(sun);

    const droneLight = new THREE.PointLight(0x37d8ff, 2.2, 36);
    droneLight.position.set(0, 0.4, 0.5);
    this.drone.add(droneLight);

    const frontLight = new THREE.SpotLight(0xcdf7ff, 0, 90, 0.34, 0.74, 1.1);
    frontLight.position.set(0, 0.12, 1.65);
    frontLight.target.position.set(0, -0.4, 72);
    frontLight.castShadow = false;
    this.drone.add(frontLight);
    this.drone.add(frontLight.target);

    const beamMaterial = new THREE.MeshBasicMaterial({
      color: 0xbdefff,
      transparent: true,
      opacity: 0,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide
    });
    const beam = new THREE.Mesh(new THREE.ConeGeometry(8.4, 56, 32, 1, true), beamMaterial);
    beam.rotation.x = Math.PI / 2;
    beam.position.set(0, -0.04, 29);
    beam.renderOrder = 4;
    this.drone.add(beam);

    const beaconLight = new THREE.PointLight(0xff1f1f, 0, 32, 2);
    beaconLight.position.set(0, 0, 0);
    this.drone.userData.beacon.add(beaconLight);

    this.lights = {
      hemi,
      sun,
      droneLight,
      frontLight,
      beam,
      beamMaterial,
      beacon: this.drone.userData.beacon,
      beaconMaterial: this.drone.userData.beaconMaterial,
      beaconHalo: this.drone.userData.beaconHalo,
      beaconHaloMaterial: this.drone.userData.beaconHaloMaterial,
      beaconLight
    };
  }

  createOrbitControls() {
    const controls = new OrbitControls(this.camera, this.renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.minDistance = 16;
    controls.maxDistance = 120;
    controls.minPolarAngle = 0.18;
    controls.maxPolarAngle = Math.PI * 0.48;
    controls.rotateSpeed = 0.72;
    controls.zoomSpeed = 0.78;
    controls.addEventListener("start", () => {
      this.orbitHoldUntil = performance.now() + 9000;
    });
    controls.addEventListener("end", () => {
      this.orbitHoldUntil = performance.now() + 5200;
    });
    return controls;
  }

  createEvidenceTools() {
    const group = new THREE.Group();
    group.visible = false;

    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0x37d8ff,
      transparent: true,
      opacity: 0.86,
      depthWrite: false,
      side: THREE.DoubleSide
    });
    const lockMaterial = new THREE.MeshBasicMaterial({
      color: 0x7df27a,
      transparent: true,
      opacity: 0.72,
      depthWrite: false,
      side: THREE.DoubleSide
    });
    const outer = new THREE.Mesh(new THREE.RingGeometry(1.5, 1.62, 48), ringMaterial);
    const inner = new THREE.Mesh(new THREE.RingGeometry(0.68, 0.74, 36), lockMaterial);
    group.add(outer, inner);

    const tag = new THREE.Mesh(
      new THREE.PlaneGeometry(3.4, 0.64),
      new THREE.MeshBasicMaterial({
        map: makeLabelTexture("TARGET", {
          width: 256,
          height: 64,
          background: "#061311",
          border: "#37d8ff",
          color: "#7df27a",
          fontSize: 28
        }),
        transparent: true,
        side: THREE.DoubleSide,
        depthWrite: false
      })
    );
    tag.position.y = 2.2;
    group.add(tag);
    this.scene.add(group);

    const lineGeometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(),
      new THREE.Vector3()
    ]);
    const scanLine = new THREE.Line(
      lineGeometry,
      new THREE.LineBasicMaterial({
        color: 0x37d8ff,
        transparent: true,
        opacity: 0.52,
        depthWrite: false
      })
    );
    scanLine.visible = false;
    this.scene.add(scanLine);

    return { group, outer, inner, tag, line: scanLine };
  }

  createDrone() {
    const group = new THREE.Group();
    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: 0xbfc7bd,
      roughness: 0.42,
      metalness: 0.62
    });
    const darkMaterial = new THREE.MeshStandardMaterial({
      color: 0x171c1a,
      roughness: 0.58,
      metalness: 0.42
    });
    const glowMaterial = new THREE.MeshStandardMaterial({
      color: 0x37d8ff,
      emissive: 0x0d9fc4,
      emissiveIntensity: 1.4,
      roughness: 0.35
    });
    const beaconMaterial = new THREE.MeshStandardMaterial({
      color: 0xff3030,
      emissive: 0xff0000,
      emissiveIntensity: 0.35,
      roughness: 0.2
    });
    const beaconHaloMaterial = new THREE.SpriteMaterial({
      color: 0xff2a2a,
      transparent: true,
      opacity: 0,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });

    const body = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.65, 3.2), bodyMaterial);
    body.castShadow = true;
    group.add(body);

    const nose = new THREE.Mesh(new THREE.ConeGeometry(0.72, 1.4, 4), glowMaterial);
    nose.rotation.x = Math.PI / 2;
    nose.position.z = 2.08;
    group.add(nose);

    const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.2, 18, 10), beaconMaterial);
    beacon.position.set(0, 0.48, -0.1);
    group.add(beacon);

    const beaconHalo = new THREE.Sprite(beaconHaloMaterial);
    beaconHalo.position.set(0, 0.6, -0.1);
    beaconHalo.scale.set(1.8, 1.8, 1);
    group.add(beaconHalo);

    const armGeometry = new THREE.BoxGeometry(4.4, 0.16, 0.2);
    for (const z of [-1.1, 1.1]) {
      const arm = new THREE.Mesh(armGeometry, darkMaterial);
      arm.position.z = z;
      arm.castShadow = true;
      group.add(arm);
    }

    const rotors = [];
    const rotorGeometry = new THREE.TorusGeometry(0.58, 0.045, 8, 28);
    const bladeGeometry = new THREE.BoxGeometry(1.35, 0.035, 0.16);
    for (const x of [-2.35, 2.35]) {
      for (const z of [-1.25, 1.25]) {
        const pod = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.22, 16), darkMaterial);
        pod.position.set(x, 0.05, z);
        pod.castShadow = true;
        group.add(pod);

        const rotor = new THREE.Group();
        const ring = new THREE.Mesh(rotorGeometry, glowMaterial);
        ring.rotation.x = Math.PI / 2;
        rotor.add(ring);
        const bladeA = new THREE.Mesh(bladeGeometry, bodyMaterial);
        const bladeB = new THREE.Mesh(bladeGeometry, bodyMaterial);
        bladeB.rotation.y = Math.PI / 2;
        rotor.add(bladeA, bladeB);
        rotor.position.set(x, 0.24, z);
        group.add(rotor);
        rotors.push(rotor);
      }
    }

    group.userData.rotors = rotors;
    group.userData.beacon = beacon;
    group.userData.beaconMaterial = beaconMaterial;
    group.userData.beaconHalo = beaconHalo;
    group.userData.beaconHaloMaterial = beaconHaloMaterial;
    return group;
  }

  bindModes() {
    hud.modeButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.mode === this.modeName);
      button.addEventListener("click", () => {
        const requested = button.dataset.mode;
        if (!Object.prototype.hasOwnProperty.call(MODES, requested)) return;
        const params = new URLSearchParams(window.location.search);
        params.set(MODE_QUERY_KEY, requested);
        window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
        this.switchMode(requested);
      });
    });
  }

  switchMode(modeName) {
    this.modeName = modeName;
    this.config = MODES[modeName];
    this.agent = new DqnAgent(this.config);
    this.city.reset(this.config);
    hud.modeButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.mode === modeName);
    });
    this.reset(false);
  }

  buildQBars() {
    hud.qBars.innerHTML = "";
    for (const action of ACTIONS) {
      const row = document.createElement("div");
      row.className = "q-row";
      row.innerHTML = `
        <span>${action.id}</span>
        <div class="q-track"><div class="q-fill"></div></div>
        <b class="q-value">0.00</b>
      `;
      hud.qBars.append(row);
    }
  }

  resize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  reset(countEpisode = true) {
    if (countEpisode) this.episode += 1;
    const z = Math.max(0, this.drone.position.z + 18);
    this.drone.position.set(0, 14, z);
    this.velocity.set(0, 0, this.config.baseSpeed);
    this.previousState = null;
    this.previousAction = ACTIONS.length - 1;
    this.lastPenalty = countEpisode ? 8 : 0;
    this.lastReward = countEpisode ? -8 : 0;
    this.startZ = Math.min(this.startZ, z);
    this.city.ensureAhead(z);
    this.lastEvent = countEpisode ? "impacto penalizado, episodio nuevo" : "vuelo autonomo iniciado";
  }

  update() {
    const dt = Math.min(this.clock.getDelta(), 0.05);
    this.city.ensureAhead(this.drone.position.z);
    this.city.updateDynamicActors(dt);

    const scan = this.scanObstacles();
    const state = this.buildState(scan);
    const bias = this.buildSafetyBias(scan);
    const actionIndex = this.agent.act(state, bias);
    const action = ACTIONS[actionIndex];

    this.applyAction(action, dt, scan);
    const rewardResult = this.computeReward(scan, actionIndex, dt);
    const nextScan = this.scanObstacles();
    const nextState = this.buildState(nextScan);

    if (this.previousState) {
      this.agent.remember({
        state: this.previousState,
        action: this.previousAction,
        reward: rewardResult.reward,
        nextState,
        done: rewardResult.done
      });
      this.agent.learn();
    }

    this.previousState = state;
    this.previousAction = actionIndex;
    this.lastScan = nextScan;

    if (rewardResult.done) {
      this.reset(true);
      if (rewardResult.event) this.lastEvent = rewardResult.event;
    }

    this.updateDroneModel(dt);
    this.updateLighting(dt);
    this.updateCamera(dt);
    this.updateEvidenceScanner(dt);
    this.updateHud(rewardResult.reward, rewardResult.penalty, nextScan);
    this.renderer.render(this.scene, this.camera);
  }

  updateLighting(dt) {
    this.lightCycleTime += dt;
    const phase = (this.lightCycleTime % DAY_NIGHT_CYCLE_SECONDS) / DAY_NIGHT_CYCLE_SECONDS;
    const autoDayAmount = 0.5 - Math.cos(phase * Math.PI * 2) * 0.5;
    const dayAmount =
      this.lightOverride === "day" ? 1 : this.lightOverride === "night" ? 0 : autoDayAmount;
    const nightAmount = 1 - dayAmount;
    const nightBeam = clamp((nightAmount - 0.18) / 0.82, 0, 1);
    const dayBeacon = clamp((dayAmount - 0.2) / 0.8, 0, 1);
    const sky = this.skyNight.clone().lerp(this.skyDay, dayAmount);
    const fog = this.fogNight.clone().lerp(this.fogDay, dayAmount);

    this.scene.background.copy(sky);
    this.scene.fog.color.copy(fog);
    this.scene.fog.density = lerp(0.014, 0.0045, dayAmount);

    this.lights.hemi.intensity = lerp(0.74, 1.72, dayAmount);
    this.lights.sun.intensity = lerp(0.22, 2.45, dayAmount);
    this.lights.droneLight.intensity = lerp(2.8, 0.55, dayAmount);

    this.lights.frontLight.visible = nightBeam > 0.03;
    this.lights.frontLight.intensity = 18 * nightBeam;
    this.lights.beam.visible = nightBeam > 0.04;
    this.lights.beamMaterial.opacity = 0.16 * nightBeam;

    const blink = Math.sin(performance.now() * 0.014) > 0.08 ? 1 : 0;
    const beaconPulse = dayBeacon * blink;
    this.lights.beacon.visible = dayBeacon > 0.03;
    this.lights.beaconMaterial.emissiveIntensity = 0.25 + beaconPulse * 5.4;
    this.lights.beaconHalo.visible = dayBeacon > 0.03;
    this.lights.beaconHaloMaterial.opacity = dayBeacon * (0.14 + beaconPulse * 0.72);
    this.lights.beaconLight.intensity = beaconPulse * 10;
    this.lights.beacon.scale.setScalar(1 + beaconPulse * 0.72);
    this.lights.beaconHalo.scale.setScalar(1.45 + beaconPulse * 0.9);

    this.lightMode = dayAmount >= 0.5 ? "dia: baliza roja" : "noche: faro frontal";
  }

  applyAction(action, dt, scan) {
    const pos = this.drone.position;
    const targetAltitude = 15 + Math.sin(pos.z * 0.018) * 3;
    const centerPull = -pos.x * 0.55;
    const altitudePull = (targetAltitude - pos.y) * 0.34;

    this.velocity.x += (action.steer * 18 + centerPull) * dt;
    this.velocity.y += (action.lift * 13 + altitudePull) * dt;
    this.velocity.z += action.throttle * 8.5 * dt;

    if (scan.minDistance < 16 && action.throttle > 0) {
      this.velocity.z -= 7 * dt;
    }

    this.velocity.x = clamp(this.velocity.x, -17, 17);
    this.velocity.y = clamp(this.velocity.y, -12, 12);
    this.velocity.z = clamp(this.velocity.z, this.config.baseSpeed * 0.55, this.config.speedLimit);

    pos.x += this.velocity.x * dt;
    pos.y += this.velocity.y * dt;
    pos.z += this.velocity.z * dt;

    if (pos.x < -28 || pos.x > 28) {
      pos.x = clamp(pos.x, -28, 28);
      this.velocity.x *= -0.32;
    }
    if (pos.y < 4.5 || pos.y > 44) {
      pos.y = clamp(pos.y, 4.5, 44);
      this.velocity.y *= -0.22;
    }
  }

  scanObstacles() {
    const pos = this.drone.position;
    const range = this.config.sensorRange;
    const rays = [
      { id: "center", x: 0, y: 0 },
      { id: "left", x: -0.34, y: 0 },
      { id: "right", x: 0.34, y: 0 },
      { id: "up", x: 0, y: 0.2 },
      { id: "down", x: 0, y: -0.2 },
      { id: "high-left", x: -0.26, y: 0.16 },
      { id: "high-right", x: 0.26, y: 0.16 },
      { id: "low-left", x: -0.25, y: -0.14 },
      { id: "low-right", x: 0.25, y: -0.14 }
    ];

    const distances = rays.map(() => range);
    let minDistance = range;
    let nearest = null;

    for (const obstacle of this.city.getCollisionObstacles()) {
      if (obstacle.bounds.max.z < pos.z - 4) continue;
      if (obstacle.bounds.min.z > pos.z + range) continue;
      const forward = obstacle.bounds.min.z - pos.z;
      if (forward < 0) {
        if (sphereIntersectsAabb(pos, DRONE_RADIUS, obstacle.bounds)) {
          minDistance = 0;
          nearest = obstacle;
        }
        continue;
      }

      minDistance = Math.min(minDistance, forward);
      if (!nearest || forward < nearest.forward) {
        nearest = { ...obstacle, forward };
      }

      for (let i = 0; i < rays.length; i += 1) {
        const ray = rays[i];
        const probeX = pos.x + ray.x * forward;
        const probeY = pos.y + ray.y * forward;
        const xHit = probeX > obstacle.bounds.min.x - 1.2 && probeX < obstacle.bounds.max.x + 1.2;
        const yHit = probeY > obstacle.bounds.min.y - 1.2 && probeY < obstacle.bounds.max.y + 1.2;
        if (xHit && yHit) {
          distances[i] = Math.min(distances[i], forward);
        }
      }
    }

    return {
      rays,
      distances,
      normalized: distances.map((distance) => clamp(distance / range, 0, 1)),
      minDistance,
      nearest
    };
  }

  buildState(scan) {
    const pos = this.drone.position;
    return [
      clamp(pos.x / 28, -1, 1),
      clamp((pos.y - 15) / 25, -1, 1),
      clamp(this.velocity.x / 17, -1, 1),
      clamp(this.velocity.y / 12, -1, 1),
      clamp((this.velocity.z - this.config.baseSpeed) / this.config.speedLimit, -1, 1),
      ...scan.normalized,
      clamp((scan.distances[1] - scan.distances[2]) / this.config.sensorRange, -1, 1),
      clamp((scan.distances[3] - scan.distances[4]) / this.config.sensorRange, -1, 1),
      Math.sin(pos.z * 0.026),
      Math.cos(pos.z * 0.026)
    ];
  }

  buildSafetyBias(scan) {
    const bias = new Array(ACTIONS.length).fill(0);
    const center = scan.distances[0];
    const left = scan.distances[1];
    const right = scan.distances[2];
    const up = scan.distances[3];
    const down = scan.distances[4];

    if (center < this.config.sensorRange * 0.62) {
      if (left > right) bias[0] += 2.8;
      if (right > left) bias[1] += 2.8;
      if (up > down) bias[2] += 1.9;
      if (down > up && this.drone.position.y > 12) bias[3] += 1.3;
      bias[5] += 1.2;
      bias[4] -= 2.4;
    }

    if (this.drone.position.y < 8) bias[2] += 2.2;
    if (this.drone.position.y > 34) bias[3] += 1.6;
    if (Math.abs(this.drone.position.x) > 18) {
      bias[this.drone.position.x > 0 ? 0 : 1] += 1.4;
    }
    return bias;
  }

  computeReward(scan, actionIndex, dt) {
    const pos = this.drone.position;
    let reward = this.velocity.z * dt * 0.18;
    let penalty = 0;
    let done = false;
    let event = null;
    let eventType = null;
    let collisionType = null;
    let celebrationType = null;

    const centerPenalty = Math.abs(pos.x) * 0.012;
    const altitudePenalty = Math.abs(pos.y - 16) * 0.006;
    penalty += centerPenalty + altitudePenalty;

    if (scan.minDistance < 18) {
      penalty += (18 - scan.minDistance) * 0.055;
    } else {
      reward += 0.05;
    }

    if (actionIndex === 4 && scan.minDistance < 28) penalty += 0.16;
    if (actionIndex === 5 && scan.minDistance > 45) penalty += 0.04;

    for (const obstacle of this.city.getCollisionObstacles()) {
      if (!obstacle.dynamic && !obstacle.passed && obstacle.bounds.max.z < pos.z - 1) {
        obstacle.passed = true;
        if (obstacle.type !== "building" && obstacle.type !== "tree") {
          reward += 1.3;
          celebrationType = obstacle.type;
          this.lastEvent = `obstaculo superado: ${obstacle.type}`;
        }
      }

      if (sphereIntersectsAabb(pos, DRONE_RADIUS, obstacle.bounds)) {
        penalty += 11;
        done = true;
        collisionType = obstacle.type;
        break;
      }
    }

    const corridorHit = pos.y <= 4.7 || Math.abs(pos.x) > 27.5;
    if (corridorHit) {
      penalty += 3.5;
    }

    const netReward = clamp(reward - penalty, -12, 4);
    if (collisionType) {
      eventType = "danger";
      event = `FUGAS EN EL AIRE: penalidad ${penalty.toFixed(2)} por ${collisionType}`;
      this.lastEvent = event;
      this.pushFlightAlert(eventType, event);
    } else if (corridorHit && penalty >= 3.5) {
      eventType = "danger";
      event = `FUGAS EN EL AIRE: penalidad ${penalty.toFixed(2)} por limite de vuelo`;
      this.lastEvent = event;
      this.pushFlightAlert(eventType, event);
    } else if (celebrationType) {
      eventType = "success";
      event = `FELICITACION: ${celebrationType} superado, recompensa +1.30`;
      this.lastEvent = event;
      this.pushFlightAlert(eventType, event);
    }

    this.lastReward = reward;
    this.lastPenalty = penalty;
    this.totalReward += Math.max(0, netReward);
    this.totalPenalty += Math.max(0, -netReward);
    this.rewardHistory.push(netReward);
    if (this.rewardHistory.length > 80) this.rewardHistory.shift();
    return { reward: netReward, penalty, done, event, eventType };
  }

  updateDroneModel(dt) {
    const pos = this.drone.position;
    this.drone.rotation.z = THREE.MathUtils.damp(this.drone.rotation.z, -this.velocity.x * 0.035, 8, dt);
    this.drone.rotation.x = THREE.MathUtils.damp(this.drone.rotation.x, this.velocity.y * 0.025, 8, dt);
    this.drone.rotation.y = THREE.MathUtils.damp(this.drone.rotation.y, this.velocity.x * 0.012, 5, dt);

    for (const rotor of this.rotors) {
      rotor.rotation.y += dt * (42 + this.velocity.z * 1.4);
    }

    const pulse = 1 + Math.sin(performance.now() * 0.014) * 0.015;
    this.drone.scale.setScalar(pulse);
    pos.y += Math.sin(performance.now() * 0.006) * 0.002;
  }

  updateCamera(dt) {
    const pos = this.drone.position;
    const desired = new THREE.Vector3(
      pos.x * 0.45 - this.velocity.x * 0.22,
      pos.y + 12,
      pos.z - 36
    );
    const lookAt = new THREE.Vector3(pos.x * 0.55, pos.y + 1.8, pos.z + 24);
    const targetBlend = 1 - Math.pow(0.0008, dt);
    this.controls.target.lerp(lookAt, targetBlend);

    if (performance.now() > this.orbitHoldUntil) {
      this.camera.position.lerp(desired, 1 - Math.pow(0.001, dt));
    }
    this.controls.update();
  }

  pushFlightAlert(type, message) {
    this.flightAlert = {
      type,
      message,
      until: performance.now() + FLIGHT_ALERT_MS
    };
  }

  renderFlightAlert() {
    if (!hud.alert) return;
    const active = this.flightAlert.message && performance.now() < this.flightAlert.until;
    hud.alert.hidden = !active;
    hud.alert.textContent = active ? this.flightAlert.message : "";
    hud.alert.className = active ? `flight-alert ${this.flightAlert.type} show` : "flight-alert";
  }

  selectEvidenceTarget() {
    const origin = new THREE.Vector3();
    this.drone.getWorldPosition(origin);
    origin.y += 0.25;
    origin.z += 1.7;
    const forward = new THREE.Vector3(0, 0, 1).applyQuaternion(this.drone.quaternion).normalize();
    let best = null;

    for (const target of this.city.scanTargets) {
      const world = new THREE.Vector3();
      target.object.getWorldPosition(world);
      const delta = world.clone().sub(origin);
      const distance = delta.length();
      if (distance > EVIDENCE_SCAN_RANGE || distance < 4) continue;
      const direction = delta.normalize();
      const alignment = forward.dot(direction);
      if (alignment < 0.55) continue;

      const projected = world.clone().project(this.camera);
      const onScreen =
        projected.z > -1 &&
        projected.z < 1 &&
        Math.abs(projected.x) < 1.14 &&
        Math.abs(projected.y) < 1.14;
      const screenWeight = onScreen ? 0.26 : -0.22;
      const score =
        alignment * 1.35 +
        (1 - distance / EVIDENCE_SCAN_RANGE) * 0.86 +
        target.priority +
        screenWeight;
      if (!best || score > best.score) {
        best = {
          target,
          world,
          distance,
          alignment,
          projected,
          onScreen,
          score
        };
      }
    }

    if (!best) return null;
    best.confidence = clamp(
      ((best.alignment - 0.55) / 0.45) * 0.58 + (1 - best.distance / EVIDENCE_SCAN_RANGE) * 0.42,
      0,
      1
    );
    best.zoom = lerp(2.2, 18, best.confidence);
    return best;
  }

  updateEvidenceScanner(dt) {
    const selected = this.selectEvidenceTarget();
    const tools = this.evidenceTools;

    if (!selected) {
      this.scanLock = Math.max(0, this.scanLock - dt * 0.72);
      tools.group.visible = false;
      tools.line.visible = false;
      if (hud.reticle) hud.reticle.hidden = true;
      this.scanSnapshot = {
        kind: "sin target",
        id: "NEURODRIVER-SEARCH",
        detail: "buscando rostro o placa",
        confidence: this.scanLock * 0.28,
        zoom: 1
      };
      return;
    }

    if (this.evidenceFocus !== selected.target.id) {
      this.evidenceFocus = selected.target.id;
      this.scanLock = 0.12;
    }
    this.scanLock = clamp(this.scanLock + (dt / SCAN_LOCK_SECONDS) * (0.35 + selected.confidence), 0, 1);

    tools.group.visible = true;
    tools.group.position.copy(selected.world);
    tools.group.quaternion.copy(this.camera.quaternion);
    const targetScale = lerp(0.9, 2.35, 1 - selected.distance / EVIDENCE_SCAN_RANGE);
    tools.group.scale.setScalar(targetScale);
    tools.outer.rotation.z += dt * 1.4;
    tools.inner.rotation.z -= dt * 2.2;
    tools.inner.material.opacity = 0.38 + this.scanLock * 0.54;

    const beamStart = new THREE.Vector3();
    this.drone.getWorldPosition(beamStart);
    beamStart.z += 1.6;
    tools.line.geometry.setFromPoints([beamStart, selected.world]);
    tools.line.visible = true;
    tools.line.material.opacity = 0.24 + this.scanLock * 0.38;

    if (hud.reticle && selected.onScreen) {
      const x = (selected.projected.x * 0.5 + 0.5) * window.innerWidth;
      const y = (-selected.projected.y * 0.5 + 0.5) * window.innerHeight;
      hud.reticle.hidden = false;
      hud.reticle.style.left = `${x}px`;
      hud.reticle.style.top = `${y}px`;
    } else if (hud.reticle) {
      hud.reticle.hidden = true;
    }

    const confidence = clamp(selected.confidence * 0.76 + this.scanLock * 0.24, 0, 1);
    this.scanSnapshot = {
      kind: selected.target.kind,
      id: selected.target.id,
      detail: `${selected.target.detail} a ${selected.distance.toFixed(1)} m`,
      confidence,
      zoom: selected.zoom
    };
    if (this.scanLock > 0.96) {
      this.lastEvent = `evidencia fijada: ${selected.target.kind} ${selected.target.id}`;
    }
  }

  updateHud(netReward, penalty, scan) {
    hud.distance.textContent = `${Math.max(0, this.drone.position.z - this.startZ).toFixed(0)} m`;
    hud.altitude.textContent = `${this.drone.position.y.toFixed(1)} m`;
    hud.speed.textContent = `${this.velocity.z.toFixed(1)} m/s`;
    hud.episode.textContent = `${this.episode}`;
    hud.reward.textContent = `${netReward.toFixed(2)}`;
    hud.penalty.textContent = `${penalty.toFixed(2)}`;
    hud.mode.textContent = this.modeName;
    hud.policy.textContent = this.agent.exploring
      ? `politica: explorando e=${this.agent.epsilon.toFixed(2)}`
      : `politica: explotando e=${this.agent.epsilon.toFixed(2)}`;
    hud.clearance.textContent = `clearance: ${scan.minDistance.toFixed(1)} m`;
    hud.event.textContent = `${this.lightMode} | target ${this.scanSnapshot.kind}: ${this.lastEvent}`;
    if (hud.targetKind) hud.targetKind.textContent = this.scanSnapshot.kind;
    if (hud.targetId) hud.targetId.textContent = this.scanSnapshot.id;
    if (hud.targetDetail) hud.targetDetail.textContent = this.scanSnapshot.detail;
    if (hud.targetZoom) hud.targetZoom.textContent = `${this.scanSnapshot.zoom.toFixed(1)}x`;
    if (hud.targetConfidence) {
      hud.targetConfidence.textContent = `${Math.round(this.scanSnapshot.confidence * 100)}%`;
    }
    if (hud.targetLock) {
      hud.targetLock.style.width = `${Math.round(this.scanLock * 100)}%`;
    }
    this.renderFlightAlert();
    this.updateQBars();
    this.drawRewardChart();
  }

  updateQBars() {
    const rows = [...hud.qBars.querySelectorAll(".q-row")];
    const min = Math.min(...this.agent.lastQ);
    const max = Math.max(...this.agent.lastQ);
    const span = Math.max(0.001, max - min);
    rows.forEach((row, index) => {
      const value = this.agent.lastQ[index];
      const percent = ((value - min) / span) * 100;
      row.classList.toggle("active", index === this.agent.lastAction);
      row.querySelector(".q-fill").style.width = `${clamp(percent, 4, 100)}%`;
      row.querySelector(".q-value").textContent = value.toFixed(2);
    });
  }

  drawRewardChart() {
    const canvas = hud.rewardChart;
    const ctx = this.chartContext;
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "rgba(255,255,255,0.04)";
    ctx.fillRect(0, height * 0.5, width, 1);

    const step = width / (this.rewardHistory.length - 1);
    ctx.beginPath();
    for (let i = 0; i < this.rewardHistory.length; i += 1) {
      const x = i * step;
      const y = height * 0.5 - clamp(this.rewardHistory[i], -6, 6) * 5.4;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "#7df27a";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.beginPath();
    for (let i = 0; i < this.rewardHistory.length; i += 1) {
      if (this.rewardHistory[i] >= 0) continue;
      const x = i * step;
      const y = height * 0.5 - clamp(this.rewardHistory[i], -6, 6) * 5.4;
      ctx.moveTo(x, height * 0.5);
      ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "#ff5f56";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

start();
