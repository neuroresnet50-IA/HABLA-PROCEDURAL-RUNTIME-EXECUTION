export const workerRegistry = [
  {
    id: "orders-stream",
    domain: "orders",
    transport: "webhook",
    status: "warm",
  },
  {
    id: "inventory-sync",
    domain: "inventory",
    transport: "polling",
    status: "warm",
  },
  {
    id: "insights-projection",
    domain: "analytics",
    transport: "socket",
    status: "building",
  },
];

export function collectRegistryStats() {
  const activeWorkers = workerRegistry.filter((worker) => worker.status !== "down");
  const domains = [...new Set(activeWorkers.map((worker) => worker.domain))];

  return {
    totalWorkers: workerRegistry.length,
    activeWorkers: activeWorkers.length,
    domains,
  };
}
