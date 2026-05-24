import { createServer } from "node:http";
import { buildHealthReport, buildServiceSnapshot } from "./catalogService.js";
import { publishEcosystemPulse } from "./architectureBridge.js";

const PORT = Number(process.env.MICROSERVICE_PORT || 6201);

async function syncOnce() {
  const snapshot = buildServiceSnapshot();
  await publishEcosystemPulse(snapshot);
  return snapshot;
}

const server = createServer(async (request, response) => {
  if (request.url === "/health") {
    const report = buildHealthReport();
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify(report, null, 2));
    return;
  }

  if (request.url === "/sync") {
    const snapshot = await syncOnce();
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify(snapshot, null, 2));
    return;
  }

  response.writeHead(200, { "Content-Type": "application/json" });
  response.end(
    JSON.stringify(
      {
        service: "ecosystem-microservice-js",
        endpoints: ["/health", "/sync"],
      },
      null,
      2
    )
  );
});

if (process.argv.includes("--sync-once")) {
  syncOnce()
    .then((snapshot) => {
      console.log("ecosystem pulse published", snapshot.summary);
    })
    .catch((error) => {
      console.error("ecosystem pulse failed", error);
      process.exitCode = 1;
    });
} else {
  server.listen(PORT, () => {
    console.log(`microservice-js listening on http://127.0.0.1:${PORT}`);
  });
}
