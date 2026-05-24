const ARCHITECTURE_API =
  process.env.ARCHITECTURE_API || "http://127.0.0.1:5000/api/architecture";

export async function publishEcosystemPulse(snapshot) {
  const response = await fetch(ARCHITECTURE_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Ecosystem-Source": "microservice-js",
    },
    body: JSON.stringify({
      metadata: {
        source: "microservice-js",
        projectName: "Ecosystem Pulse",
        note: "Microservicio lateral que publica estado de workers y conecta el ecosistema.",
      },
      microserviceSnapshot: snapshot,
    }),
  });

  if (!response.ok) {
    throw new Error(`Architecture bridge failed with ${response.status}`);
  }

  return response.json();
}
