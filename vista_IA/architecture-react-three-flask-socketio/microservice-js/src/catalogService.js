import { collectRegistryStats, workerRegistry } from "./workerRegistry.js";

export function buildServiceSnapshot() {
  const stats = collectRegistryStats();

  const nodes = workerRegistry.map((worker) => ({
    id: worker.id,
    name: worker.id,
    domain: worker.domain,
    transport: worker.transport,
    status: worker.status,
  }));

  return {
    generatedAt: new Date().toISOString(),
    summary: stats,
    nodes,
  };
}

export function buildHealthReport() {
  const snapshot = buildServiceSnapshot();
  const degradedWorkers = snapshot.nodes.filter((worker) => worker.status !== "warm");

  return {
    status: degradedWorkers.length ? "degraded" : "healthy",
    summary: snapshot.summary,
    degradedWorkers,
  };
}
