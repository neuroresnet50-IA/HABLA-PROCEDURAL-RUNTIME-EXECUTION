import SectionDividerMenu from "./SectionDividerMenu.jsx";

export default function AppObserverPanel({
  observerStatus,
  observerTimeline,
  observerRules,
  observerMemory,
  latestObserverEvent,
  observerActionStatus,
  effectiveWorkspaceScene,
  onObserveNow,
  onRunObserverAction,
  onUpdateObserverRule,
}) {
  return (
    <>
      <SectionDividerMenu id="observer" label="02B Observer" title="Observer" />

      <section className="observer-panel">
        <div className="panel-header compact">
          <div>
            <h2>Observer Plane</h2>
            <p>
              Estado: {observerStatus?.state || "idle"} · {observerStatus?.enabled === false ? "apagado" : "activo"}
              {observerStatus?.humanPinned ? " · fijado por humano" : ""}
            </p>
          </div>
          <div className="toolbar-inline compact">
            <button type="button" className="tool-button" onClick={onObserveNow}>Observar ahora</button>
            <button type="button" className="tool-button" onClick={() => onRunObserverAction("audit_map", { scene: effectiveWorkspaceScene })}>Reauditar mapa</button>
            <button type="button" className="tool-button" onClick={() => onRunObserverAction("refresh_graph")}>Refrescar grafo</button>
          </div>
        </div>

        <div className="observer-grid">
          <article className="observer-decision-card">
            <span className="toolbar-label">Decision actual</span>
            <strong>{latestObserverEvent?.state || observerStatus?.state || "idle"}{" -> "}{latestObserverEvent?.action || "observando"}</strong>
            <p>{latestObserverEvent?.reason || observerStatus?.memory?.lastDecision?.reason || "Sin decision nueva todavia."}</p>
            {latestObserverEvent?.message ? <small>{latestObserverEvent.message}</small> : null}
            {latestObserverEvent?.proposedActions?.length ? (
              <div className="observer-action-row">
                {latestObserverEvent.proposedActions.map((action) => (
                  <button
                    key={action.id}
                    type="button"
                    className={`tool-button ${action.requiresApproval ? "primary" : ""}`}
                    onClick={() => onRunObserverAction(action.id, { ...(action.payload || {}), projectSlug: latestObserverEvent.projectSlug })}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            ) : null}
            {observerActionStatus ? <small>{observerActionStatus}</small> : null}
          </article>

          <article className="observer-memory-card">
            <span className="toolbar-label">Memoria</span>
            <div className="observer-metrics">
              <span><strong>{observerMemory.visitedNodeCount || 0}</strong><small>nodos</small></span>
              <span><strong>{observerMemory.visitedIssueCount || 0}</strong><small>puntos</small></span>
              <span><strong>{observerMemory.seenWorkerCount || 0}</strong><small>workers</small></span>
              <span><strong>{observerMemory.repairAttemptCount || 0}</strong><small>repairs</small></span>
            </div>
            {observerMemory.lastDecision?.message ? <p>{observerMemory.lastDecision.message}</p> : null}
          </article>

          <article className="observer-tree-card">
            <span className="toolbar-label">Behavior tree</span>
            <div className="observer-rules">
              {observerRules.map((rule) => (
                <label key={rule.id} className="observer-rule">
                  <input
                    type="checkbox"
                    checked={rule.enabled !== false}
                    onChange={(event) => onUpdateObserverRule(rule.id, event.target.checked)}
                  />
                  <span>{rule.label}</span>
                  {rule.requiresApproval ? <small>autorizacion</small> : null}
                </label>
              ))}
            </div>
          </article>

          <article className="observer-timeline-card">
            <span className="toolbar-label">Timeline</span>
            <div className="observer-timeline">
              {observerTimeline.length ? observerTimeline.map((event, index) => (
                <div key={`${event.timestamp || index}-${event.action || index}`} className="observer-timeline-event">
                  <strong>{event.state || "state"}{" -> "}{event.action || "action"}</strong>
                  <span>{event.message || event.reason || "evento observer"}</span>
                  <small>{event.timestamp || ""}</small>
                </div>
              )) : <p className="lint-clean">Sin eventos del observer todavia.</p>}
            </div>
          </article>
        </div>
      </section>
    </>
  );
}
