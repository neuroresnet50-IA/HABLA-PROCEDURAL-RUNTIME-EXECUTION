import { useEffect, useMemo, useState } from "react";
import { SOCKET_URL } from "../appUtils.js";

function fmtRisk(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) return "0";
  return String(Math.round(numeric));
}

export default function CyberLACEPanel() {
  const [health, setHealth] = useState(null);
  const [events, setEvents] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);

  async function loadCyberLACE({ includeEvidence = expanded } = {}) {
    try {
      const healthResponse = await fetch(`${SOCKET_URL}/api/cyberlace/health`);
      const healthPayload = await healthResponse.json();
      setHealth(healthPayload || null);
      if (includeEvidence) {
        const evidenceResponse = await fetch(`${SOCKET_URL}/api/cyberlace/evidence/recent?limit=8`);
        const evidencePayload = await evidenceResponse.json();
        setEvents(Array.isArray(evidencePayload?.events) ? evidencePayload.events.slice(-8).reverse() : []);
        setDecisions(Array.isArray(evidencePayload?.decisions) ? evidencePayload.decisions.slice(-8).reverse() : []);
      }
      setError(healthPayload?.ok === false ? healthPayload?.error || "CyberLACE no disponible." : "");
    } catch (loadError) {
      setError(loadError?.message || "No fue posible cargar CyberLACE.");
    }
  }

  useEffect(() => {
    loadCyberLACE({ includeEvidence: expanded });
    const timer = window.setInterval(
      () => loadCyberLACE({ includeEvidence: expanded }),
      expanded ? 10000 : 30000
    );
    return () => window.clearInterval(timer);
  }, [expanded]);

  const latestDecision = decisions[0] || null;
  const mode = health?.mode || "off";
  const enabled = Boolean(health?.enabled);
  const engineReady = health?.engineAvailable !== false;
  const evidenceCounts = health?.evidence || {};
  const panelClass = useMemo(() => (
    `cyberlace-panel ${expanded ? "is-expanded" : "is-collapsed"} is-${mode} ${enabled ? "is-enabled" : "is-off"}`
  ), [enabled, expanded, mode]);

  return (
    <section className={panelClass} aria-label="CyberLACE">
      <div className="panel-header compact">
        <div>
          <h2>CyberLACE</h2>
          <p>{enabled ? "capa cognitiva activa" : "capa cognitiva apagada"} · {engineReady ? "engine listo" : "engine pendiente"}</p>
        </div>
        <div className="toolbar-inline compact">
          <span className="meta-pill">{mode}</span>
          <span className="meta-pill">riesgo {fmtRisk(latestDecision?.riskScore)}</span>
          <button type="button" onClick={() => loadCyberLACE({ includeEvidence: true })}>Actualizar</button>
          <button type="button" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Ocultar" : "Ver evidencia"}
          </button>
        </div>
      </div>

      {expanded ? (
        <div className="cyberlace-grid">
          <article className="cyberlace-summary">
            <strong>{latestDecision?.runtimeAction || latestDecision?.action || "ALLOW"}</strong>
            <p>{latestDecision?.reason || health?.engine || "HABLA CyberLACE Security Engine"}</p>
            <div className="cyberlace-metrics">
              <span><strong>{fmtRisk(latestDecision?.riskScore)}</strong><small>riesgo</small></span>
              <span><strong>{evidenceCounts.recentEvents || events.length || 0}</strong><small>eventos</small></span>
              <span><strong>{evidenceCounts.recentDecisions || decisions.length || 0}</strong><small>decisiones</small></span>
            </div>
            {error ? <small className="cyberlace-error">{error}</small> : null}
          </article>

          <article className="cyberlace-stream">
            <strong>Evidencia reciente</strong>
            <div className="cyberlace-events">
              {decisions.length ? decisions.map((decision, index) => (
                <div key={`${decision.eventId || index}-${decision.timestamp || index}`} className="cyberlace-event">
                  <small>{decision.stage || "guard"} · {decision.mode || mode} · riesgo {fmtRisk(decision.riskScore)}</small>
                  <span>{decision.runtimeAction || decision.action || "ALLOW"}: {decision.reason || "decision registrada"}</span>
                </div>
              )) : <p className="lint-clean">Sin decisiones registradas.</p>}
            </div>
          </article>
        </div>
      ) : null}
    </section>
  );
}
