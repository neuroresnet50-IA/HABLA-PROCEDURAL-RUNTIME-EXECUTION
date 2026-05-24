export default function CodeWorkbenchRepairBubble({
  target,
  progressVisible,
  progress,
  structureLabel,
  instruction,
  sending,
  dirty,
  locked,
  lockMessage,
  onClose,
  onInstructionChange,
  onLaunch,
  onResetPrompt,
}) {
  if (!target) return null;

  return (
    <div className="code-workbench-repair-bubble">
      <div className="code-workbench-repair-header">
        <strong>Reparacion con agente</strong>
        <button type="button" onClick={onClose}>Cerrar</button>
      </div>
      <code>{target.path}:{target.line}</code>
      <p>{target.message}</p>
      {progressVisible ? (
        <div className={`code-workbench-repair-progress ${progress.active ? "is-active" : "is-complete"}`}>
          <div className="code-workbench-repair-progress-row">
            <span className="code-workbench-repair-spinner" aria-hidden="true" />
            <div>
              <small>{progress.label || "reparando codigo"}</small>
              <strong>{structureLabel}</strong>
            </div>
            <b>{Math.round(progress.percent)}%</b>
          </div>
          <div className="code-workbench-repair-progress-track" aria-label="Progreso de reparacion">
            <span style={{ width: `${Math.max(0, Math.min(100, progress.percent))}%` }} />
          </div>
          {progress.detail ? <em>{progress.detail}</em> : null}
          {progress.messages.length ? (
            <div className="code-workbench-repair-messages">
              {progress.messages.map((item) => (
                <span key={item.id}>{item.text}</span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      <label>
        <span>Orden para el agente</span>
        <textarea
          rows={4}
          value={instruction}
          onChange={(event) => onInstructionChange(event.target.value)}
          disabled={sending || locked}
        />
      </label>
      <div className="code-workbench-repair-actions">
        <button
          type="button"
          className="tool-button primary"
          onClick={onLaunch}
          disabled={sending}
        >
          {sending ? "Lanzando..." : "Lanzar agente"}
        </button>
        <button
          type="button"
          className="tool-button"
          onClick={onResetPrompt}
          disabled={sending}
        >
          Prompt basico
        </button>
      </div>
      {dirty ? <small>Guarda o recarga tus cambios humanos antes de lanzar un agente.</small> : null}
      {locked ? <small>{lockMessage}</small> : null}
    </div>
  );
}
