export default function CodeWorkbenchSandboxModal({
  open,
  sandbox,
  selectedProject,
  onRefresh,
  onClose,
}) {
  if (!open || !sandbox?.embedUrl) return null;

  return (
    <div className="code-workbench-sandbox-modal" role="dialog" aria-modal="true" aria-label="Sandbox runtime interno">
      <div className="code-workbench-sandbox-modal-panel">
        <div className="code-workbench-sandbox-browser-bar">
          <span className={`socket-pill ${sandbox.running ? "is-online" : "is-offline"}`}>
            {sandbox.running ? "en vivo" : "detenido"}
          </span>
          <code>{sandbox.embedUrl}</code>
          <button type="button" className="tool-button" onClick={onRefresh}>
            Refrescar
          </button>
          <button type="button" className="tool-button" onClick={onClose}>
            Cerrar
          </button>
        </div>
        <iframe
          key={`${sandbox.projectId || selectedProject}-${sandbox.embedUrl}-${sandbox.startedAt || ""}`}
          title={`Sandbox ${selectedProject || sandbox.projectId || "runtime"}`}
          src={sandbox.embedUrl}
          sandbox="allow-forms allow-modals allow-pointer-lock allow-popups allow-same-origin allow-scripts"
        />
      </div>
    </div>
  );
}
