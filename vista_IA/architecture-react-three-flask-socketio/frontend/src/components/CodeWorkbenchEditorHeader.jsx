import { formatBytes, formatClock } from "./codeWorkbenchUtils.js";
import CodeWorkbenchIntegrityAlert from "./CodeWorkbenchIntegrityAlert.jsx";

export default function CodeWorkbenchEditorHeader({
  selectedProject,
  selectedPath,
  selectedFileMeta,
  finalSequence,
  codeScanner,
  liveWriter,
  dirty,
  integrityFindings,
  integrityActionStatus,
  integrityBusy,
  jumpNotice,
  repairSending,
  onStopScanner,
  onFocusFirstIntegrity,
  onFrozenSniper,
  onAcceptBaseline,
  onToggleRepair,
  onOpenRepair,
}) {
  return (
    <div className="code-workbench-editor-header-stack">
      <div className="code-workbench-tabs">
        <button type="button" className="active" title={selectedPath || "Sin archivo"}>
          {selectedPath || "Sin archivo abierto"}
        </button>
        <span className={dirty ? "is-dirty" : ""}>
          {finalSequence.active ? "secuencia final" : codeScanner.active ? "scanner final" : liveWriter.active ? "IA escribiendo" : dirty ? "sin guardar" : "sin cambios"}
        </span>
      </div>

      <div className="code-workbench-breadcrumb">
        <span>{selectedProject || "workspace"}</span>
        <span>/</span>
        <strong>{selectedPath || "selecciona un archivo"}</strong>
        {selectedFileMeta ? (
          <small>{formatBytes(selectedFileMeta.size)} · {selectedFileMeta.language} · {formatClock(selectedFileMeta.modifiedAt)}</small>
        ) : null}
      </div>

      {codeScanner.active ? (
        <div className="code-workbench-scanning-toast" role="status" aria-live="polite">
          <span aria-hidden="true" />
          <strong>Sistema escaneando</strong>
          <small>{codeScanner.path || "preparando primeras lineas"}</small>
          <button type="button" onClick={onStopScanner}>
            Detener
          </button>
        </div>
      ) : null}

      <CodeWorkbenchIntegrityAlert
        findings={integrityFindings}
        actionStatus={integrityActionStatus}
        busy={integrityBusy}
        selectedProject={selectedProject}
        onFocusFirst={onFocusFirstIntegrity}
        onFrozenSniper={onFrozenSniper}
        onAcceptBaseline={onAcceptBaseline}
      />

      {jumpNotice ? (
        <div className="code-workbench-jump-notice">
          <button type="button" onClick={onToggleRepair}>
            Punto rojo navegado: {jumpNotice}
          </button>
          <button
            type="button"
            className="code-workbench-repair-trigger"
            onClick={onOpenRepair}
            disabled={repairSending}
          >
            Reparar con agente
          </button>
          <button
            type="button"
            className="code-workbench-repair-trigger"
            onClick={onFrozenSniper}
            disabled={integrityBusy || !selectedProject}
          >
            {integrityBusy ? "Sniper trabajando..." : "Frozen Sniper"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
