export default function CodeWorkbenchIntegrityAlert({
  findings,
  actionStatus,
  busy,
  selectedProject,
  onFocusFirst,
  onFrozenSniper,
  onAcceptBaseline,
}) {
  if (findings.length) {
    return (
      <div className="code-workbench-integrity-alert" role="status" aria-live="polite">
        <div>
          <strong>Observer detecto cambios externos no registrados</strong>
          <span>{findings.length} huella(s) rojas activas en archivos generados.</span>
          {actionStatus ? <small>{actionStatus}</small> : null}
        </div>
        <button type="button" className="tool-button danger" onClick={onFocusFirst}>
          Ver primera huella
        </button>
        <button type="button" className="tool-button danger" onClick={onFrozenSniper} disabled={busy || !selectedProject}>
          {busy ? "Ejecutando..." : "Frozen Sniper"}
        </button>
        <button type="button" className="tool-button" onClick={onAcceptBaseline} disabled={busy || !selectedProject}>
          Aceptar baseline
        </button>
      </div>
    );
  }

  if (!actionStatus) return null;

  return (
    <div className="code-workbench-integrity-alert is-clean" role="status" aria-live="polite">
      <div>
        <strong>Integridad</strong>
        <span>{actionStatus}</span>
      </div>
    </div>
  );
}
