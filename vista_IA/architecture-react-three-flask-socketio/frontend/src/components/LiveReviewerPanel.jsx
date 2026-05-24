import { formatAgentStatus } from "./agentClosureCertificate.js";
import { formatDuration } from "./agentStudioUtils.js";

export default function LiveReviewerPanel({
  session,
  status,
  events,
  isOpen,
  isMinimized,
  isExpanded,
  onOpen,
  onClose,
  onMinimize,
  onExpand,
  onCopy,
  onExport,
}) {
  const timeline = Array.isArray(events) ? events.slice(-80).reverse() : [];
  const warnings = timeline.filter((event) => event.severity === "warning" || event.severity === "error");
  const latest = timeline[0] || null;
  const queueCounts = status?.queue_counts || {};
  const total = Number(status?.tasks_total || 0);
  const completed = Number(status?.tasks_completed || queueCounts.completed || 0);
  const found = status?.expected_files_found || [];
  const missing = status?.expected_files_missing || [];
  const currentTask = status?.current_task_id || session?.controlPlane?.activeTaskId || "sin tarea activa";
  const currentTaskTitle = status?.current_task_title || session?.controlPlane?.activeTask?.title || "";
  const workerLabel = status?.worker_alive === true
    ? `vivo${status?.worker_pid ? ` · PID ${status.worker_pid}` : ""}`
    : status?.worker_alive === false
      ? "no vivo"
      : "no detectado";

  if (!isOpen) {
    return null;
  }

  if (isMinimized) {
    return (
      <button type="button" className="reviewer-minibar" onClick={onMinimize}>
        <strong>Revisor en vivo</strong>
        <span>{latest?.message || "Esperando eventos del supervisor."}</span>
      </button>
    );
  }

  return (
    <div className={`reviewer-overlay ${isExpanded ? "is-expanded" : ""}`} role="dialog" aria-label="Operador Revisor En Vivo">
      <div className="reviewer-panel">
        <div className="reviewer-header">
          <div>
            <h2>Operador Revisor En Vivo</h2>
            <p>{session?.projectName || status?.project_id || "sesion activa"} · {formatAgentStatus(session?.status)}</p>
          </div>
          <div className="reviewer-actions">
            <button type="button" className="tool-button" onClick={onCopy}>Copiar bitacora</button>
            <button type="button" className="tool-button" onClick={onExport}>Exportar</button>
            <button type="button" className="tool-button" onClick={onExpand}>{isExpanded ? "Compactar" : "Expandir"}</button>
            <button type="button" className="tool-button" onClick={onMinimize}>Minimizar</button>
            <button type="button" className="tool-button danger" onClick={onClose}>Cerrar</button>
          </div>
        </div>

        <div className="reviewer-summary-grid">
          <div>
            <span>Sesion</span>
            <strong>{formatAgentStatus(session?.status)}</strong>
          </div>
          <div>
            <span>Tarea actual</span>
            <strong>{currentTask}</strong>
            {currentTaskTitle ? <small>{currentTaskTitle}</small> : null}
          </div>
          <div>
            <span>Cola</span>
            <strong>{completed}/{total || "?"}</strong>
            <small>{queueCounts.pending || 0} pending · {queueCounts.running || 0} running</small>
          </div>
          <div>
            <span>Tiempo total</span>
            <strong>{formatDuration(latest?.elapsed_seconds)}</strong>
            <small>Tarea {formatDuration(latest?.task_elapsed_seconds)}</small>
          </div>
          <div>
            <span>Worker</span>
            <strong>{workerLabel}</strong>
          </div>
          <div>
            <span>Checkpoint</span>
            <strong>{status?.latest_checkpoint || "ninguno"}</strong>
          </div>
        </div>

        <div className="reviewer-evidence-grid">
          <section>
            <h3>Archivos encontrados</h3>
            {found.length ? (
              <ul>{found.map((item) => <li key={item}>{item}</li>)}</ul>
            ) : (
              <p>Sin evidencia de archivos esperados todavia.</p>
            )}
          </section>
          <section>
            <h3>Archivos faltantes</h3>
            {missing.length ? (
              <ul>{missing.map((item) => <li key={item}>{item}</li>)}</ul>
            ) : (
              <p>No hay faltantes para la tarea observada.</p>
            )}
          </section>
          <section>
            <h3>Ultima historia</h3>
            <p>{status?.latest_history?.result?.task_id || "sin historial"} · {String(status?.latest_history?.result?.validation_passed ?? "sin validacion")}</p>
          </section>
        </div>

        {warnings.length ? (
          <div className="reviewer-warning-strip">
            {warnings.slice(0, 3).map((event) => (
              <p key={`${event.timestamp}-${event.message}`}>{event.message}</p>
            ))}
          </div>
        ) : null}

        <div className="reviewer-timeline" aria-live="polite">
          {timeline.length ? timeline.map((event) => (
            <article key={`${event.timestamp}-${event.type}-${event.message}`} className={`reviewer-event is-${event.severity || "info"}`}>
              <div>
                <strong>{event.type}</strong>
                <span>{event.timestamp}</span>
              </div>
              <p>{event.message}</p>
              <small>
                {event.current_task_id || "sin tarea"} · encontrados {(event.expected_files_found || []).length} · faltantes {(event.expected_files_missing || []).length}
              </small>
            </article>
          )) : (
            <article className="reviewer-event">
              <div>
                <strong>Sin eventos</strong>
                <span>esperando reviewer</span>
              </div>
              <p>Cuando la sesion empiece a emitir evidencia, el supervisor narrara aqui lo que ve y lo que espera despues.</p>
            </article>
          )}
        </div>
      </div>
      <button type="button" className="reviewer-backdrop" onClick={onOpen} aria-label="Mantener revisor abierto" />
    </div>
  );
}
