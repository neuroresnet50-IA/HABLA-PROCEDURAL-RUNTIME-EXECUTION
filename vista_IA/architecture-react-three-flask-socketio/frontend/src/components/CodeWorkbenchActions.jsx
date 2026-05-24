function runtimeTruthLabel(truth) {
  const verdict = String(truth?.verdict || "unknown");
  if (verdict === "zombie") return "supervisor: ZOMBIE sin agente vivo";
  if (verdict === "live") return "supervisor: agente vivo";
  if (verdict === "idle") return "supervisor: idle";
  if (verdict === "unverified_running") return "supervisor: running sin verificar";
  return "supervisor: sin diagnostico";
}

function runtimeTruthClass(truth) {
  const verdict = String(truth?.verdict || "unknown");
  if (verdict === "zombie") return "is-zombie";
  if (verdict === "live") return "is-live";
  if (verdict === "idle") return "is-idle";
  return "is-unverified";
}

export default function CodeWorkbenchActions({
  canSave,
  saving,
  selectedProject,
  selectedPath,
  loadingFile,
  liveWriterActive,
  finalSequenceActive,
  scannerActive,
  dirty,
  lock,
  integrityBusy,
  integrityFindings,
  runtimeTruth,
  runtimeTruthBusy,
  error,
  repairStatus,
  onSave,
  onReloadFile,
  onToggleScanner,
  onScanIntegrity,
  onReleaseRuntimeZombie,
}) {
  return (
    <div className="code-workbench-actions">
      <button type="button" className="tool-button primary" onClick={onSave} disabled={!canSave}>
        {saving ? "Guardando..." : "Guardar archivo"}
      </button>
      <button
        type="button"
        className="tool-button"
        onClick={onReloadFile}
        disabled={!selectedProject || !selectedPath || loadingFile || liveWriterActive || finalSequenceActive || scannerActive}
      >
        Recargar archivo
      </button>
      <button
        type="button"
        className="tool-button"
        onClick={onToggleScanner}
        disabled={!selectedProject || dirty || lock.locked || liveWriterActive || finalSequenceActive}
      >
        {scannerActive ? "Detener scanner" : "Scanner final"}
      </button>
      <button
        type="button"
        className={integrityFindings.length ? "tool-button danger" : "tool-button"}
        onClick={onScanIntegrity}
        disabled={!selectedProject || integrityBusy || liveWriterActive || finalSequenceActive}
      >
        {integrityBusy ? "Verificando..." : "Verificar integridad"}
      </button>
      <span className={`code-workbench-state ${lock.locked ? "locked" : "open"}`}>
        {lock.locked ? "edicion bloqueada por runtime" : "edicion habilitada"}
      </span>
      <span className={`code-workbench-truth-state ${runtimeTruthClass(runtimeTruth)}`}>
        {runtimeTruthLabel(runtimeTruth)}
      </span>
      {runtimeTruth?.canReleaseZombie ? (
        <button
          type="button"
          className="tool-button danger code-workbench-zombie-release"
          onClick={onReleaseRuntimeZombie}
          disabled={!selectedProject || runtimeTruthBusy}
        >
          {runtimeTruthBusy ? "Liberando zombie..." : "Liberar zombie"}
        </button>
      ) : null}
      {error ? <span className="code-workbench-error">{error}</span> : null}
      {repairStatus ? <span className="code-workbench-repair-status">{repairStatus}</span> : null}
    </div>
  );
}
