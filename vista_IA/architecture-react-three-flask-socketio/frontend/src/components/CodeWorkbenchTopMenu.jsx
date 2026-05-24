import { HABLA_OBSERVER_LOGO_SRC } from "./codeWorkbenchUtils.js";

export default function CodeWorkbenchTopMenu({
  lock,
  canSave,
  selectedProject,
  selectedPath,
  dirty,
  liveWriterActive,
  finalSequenceActive,
  scannerActive,
  integrityBusy,
  sandboxBusy,
  sandboxRunning,
  sandboxEmbedUrl,
  onSave,
  onRefreshFiles,
  onRevertFile,
  onPaneChange,
  onLoadProblems,
  onRunFinalSequence,
  onToggleScanner,
  onScanIntegrity,
  onStartSandbox,
  onOpenSandbox,
  onStopSandbox,
}) {
  return (
    <div className="code-workbench-menu">
      <div className="code-workbench-brand">
        <img
          src={HABLA_OBSERVER_LOGO_SRC}
          alt="HABLA Observer IA"
          className="code-workbench-logo"
        />
        <strong>HABLA Observer IA</strong>
      </div>
      <nav aria-label="Code editor menu">
        <button type="button" onClick={onSave} disabled={!canSave}>File: Save</button>
        <button type="button" onClick={onRefreshFiles} disabled={!selectedProject || finalSequenceActive || scannerActive}>File: Refresh</button>
        <button type="button" onClick={onRevertFile} disabled={!selectedPath || liveWriterActive || finalSequenceActive || scannerActive}>Edit: Revert</button>
        <button type="button" onClick={() => onPaneChange("explorer")}>View: Explorer</button>
        <button type="button" onClick={onLoadProblems} disabled={!selectedProject}>Go: Problems</button>
        <button type="button" onClick={() => onPaneChange("tests")}>Run: Tests</button>
        <button type="button" onClick={onRunFinalSequence} disabled={!selectedProject || dirty || lock.locked || liveWriterActive || finalSequenceActive || scannerActive}>Typewriter final</button>
        <button
          type="button"
          onClick={onToggleScanner}
          disabled={!selectedProject || dirty || lock.locked || liveWriterActive || finalSequenceActive}
        >
          {scannerActive ? "Detener scanner" : "Scanner final"}
        </button>
        <button type="button" onClick={onScanIntegrity} disabled={!selectedProject || integrityBusy || liveWriterActive || finalSequenceActive}>Integrity: Scan</button>
        <button type="button" onClick={onStartSandbox} disabled={!selectedProject || sandboxBusy || sandboxRunning || finalSequenceActive || scannerActive}>Sandbox: Start</button>
        <button type="button" onClick={onOpenSandbox} disabled={!sandboxRunning || !sandboxEmbedUrl}>Sandbox: Open</button>
        <button type="button" onClick={onStopSandbox} disabled={!selectedProject || sandboxBusy || !sandboxRunning}>Sandbox: Stop</button>
        <button type="button" onClick={() => onPaneChange("runtime")}>Terminal</button>
      </nav>
      <div className={`code-workbench-lock ${lock.locked ? "is-locked" : "is-open"}`}>
        {lock.locked ? "Agente trabajando" : "Edicion humana"}
      </div>
    </div>
  );
}
