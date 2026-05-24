import { fileGlyph, paneLabel } from "./codeWorkbenchUtils.js";

function formatTruthAge(seconds) {
  const value = Number(seconds);
  if (!Number.isFinite(value)) return "sin evidencia";
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${Math.round(value / 3600)}h ${Math.round((value % 3600) / 60)}m`;
}

function runtimeTruthLabel(truth) {
  const verdict = String(truth?.verdict || "unknown");
  if (verdict === "zombie") return "ZOMBIE / sin agente vivo";
  if (verdict === "live") return "Agente vivo";
  if (verdict === "idle") return "Idle verificable";
  if (verdict === "unverified_running") return "Running sin verificar";
  return "Sin diagnostico";
}

function runtimeTruthClass(truth) {
  const verdict = String(truth?.verdict || "unknown");
  if (verdict === "zombie") return "is-zombie";
  if (verdict === "live") return "is-live";
  if (verdict === "idle") return "is-idle";
  return "is-unverified";
}

export default function CodeWorkbenchSidebar({
  activePane,
  selectedProject,
  selectedPath,
  sortedProjects,
  selectedProjectMeta,
  files,
  loadingProjects,
  loadingFile,
  loadingProblems,
  finalSequenceActive,
  scannerActive,
  fileFilter,
  filteredFiles,
  problemRows,
  testFiles,
  lock,
  sandbox,
  sandboxBusy,
  runtimeTruth,
  runtimeTruthBusy,
  onReleaseRuntimeZombie,
  onPaneChange,
  onProjectChange,
  onRefresh,
  onFileFilterChange,
  onSelectFile,
  onProblemOpen,
  onLoadProblems,
  onOpenSandboxPreview,
  onStartSandbox,
  onStopSandbox,
  agentChangedPaths,
}) {
  return (
    <aside className="code-workbench-sidebar">
      <div className="code-workbench-sidebar-header">
        <span>{paneLabel(activePane)}</span>
        <button
          type="button"
          onClick={onRefresh}
          disabled={!selectedProject || loadingFile || loadingProblems || finalSequenceActive || scannerActive}
        >
          {loadingFile || loadingProblems ? "..." : "Refresh"}
        </button>
      </div>

      <label className="code-workbench-project-picker">
        <span>Workspace project</span>
        <select
          value={selectedProject}
          onChange={(event) => onProjectChange(event.target.value)}
          disabled={loadingProjects || !sortedProjects.length}
        >
          {sortedProjects.length ? (
            sortedProjects.map((project) => (
              <option key={project.slug} value={project.slug}>
                {project.name || project.slug}
              </option>
            ))
          ) : (
            <option value="">Sin proyectos</option>
          )}
        </select>
      </label>

      {selectedProjectMeta ? (
        <div className="code-workbench-project-meta">
          <strong>{selectedProjectMeta.slug}</strong>
          <small>{selectedProjectMeta.fileCount || files.length} archivos fuente</small>
          <small>{selectedProjectMeta.relativePath}</small>
        </div>
      ) : null}

      {activePane === "explorer" ? (
        <>
          <label className="code-workbench-filter">
            <span>Find file</span>
            <input
              value={fileFilter}
              onChange={(event) => onFileFilterChange(event.target.value)}
              placeholder="frontend/app.js, src/, tests..."
            />
          </label>
          <div className="code-workbench-file-list" role="listbox" aria-label="Project files">
            {filteredFiles.length ? (
              filteredFiles.map((entry) => (
                <button
                  key={entry.path}
                  type="button"
                  className={[entry.path === selectedPath ? "active" : "", agentChangedPaths?.has?.(entry.path) ? "agent-changed" : ""].filter(Boolean).join(" ")}
                  onClick={() => onSelectFile(entry.path)}
                  disabled={finalSequenceActive || scannerActive}
                  title={entry.path}
                >
                  <span className="code-workbench-file-glyph">{fileGlyph(entry.path)}</span>
                  <span className="code-workbench-file-main">
                    <strong>{entry.name}</strong>
                    <small>{entry.path}</small>
                  </span>
                </button>
              ))
            ) : (
              <p className="code-workbench-empty">No hay archivos que coincidan con el filtro.</p>
            )}
          </div>
        </>
      ) : null}

      {activePane === "problems" ? (
        <div className="code-workbench-problem-list">
          {problemRows.length ? (
            problemRows.map((problem) => (
              <button
                key={problem.id}
                type="button"
                className={`code-workbench-problem ${problem.severity || "info"}`}
                onClick={() => problem.target && onProblemOpen(problem)}
                disabled={!problem.target}
              >
                <strong>{problem.message}</strong>
                <small>{problem.path || "sin ruta"}{problem.line ? `:${problem.line}` : ""}</small>
                <span>{problem.code}</span>
                <em>Ver</em>
              </button>
            ))
          ) : (
            <p className="code-workbench-empty">
              {loadingProblems ? "Cargando problemas..." : "Sin hallazgos visuales ni huellas de integridad para este proyecto."}
            </p>
          )}
        </div>
      ) : null}

      {activePane === "runtime" ? (
        <div className="code-workbench-runtime-pane">
          <strong>{lock.locked ? "Runtime ocupado" : "Runtime disponible"}</strong>
          <span>{lock.message}</span>
          <code>status={lock.projectStatus || "idle"}</code>
          <code>task={lock.currentTaskId || "none"}</code>
          <code>session={lock.sessionId || "none"}</code>

          <section className={`code-workbench-runtime-truth ${runtimeTruthClass(runtimeTruth)}`}>
            <div>
              <strong>Supervisor real</strong>
              <span>{runtimeTruthLabel(runtimeTruth)}</span>
            </div>
            <code>sessions={runtimeTruth?.sessions?.activeCount ?? "?"} active / {runtimeTruth?.sessions?.totalRuntimeSessions ?? "?"} total</code>
            <code>worker={runtimeTruth?.worker?.alive === true ? `alive pid=${runtimeTruth?.worker?.pid || "?"}` : "none"}</code>
            <code>disk_silence={formatTruthAge(runtimeTruth?.disk?.lastActivityAgeSeconds)}</code>
            <code>queue={runtimeTruth?.controlPlane?.tasksCompleted ?? "?"}/{runtimeTruth?.controlPlane?.tasksTotal ?? "?"} completed · running={runtimeTruth?.controlPlane?.queueCounts?.running ?? "?"}</code>
            <code>integrity_findings={runtimeTruth?.integrity?.findings ?? "?"}</code>
            {runtimeTruth?.reasons?.length ? <small>{runtimeTruth.reasons.join(" · ")}</small> : null}
            {runtimeTruth?.canReleaseZombie ? (
              <button type="button" className="tool-button danger" onClick={onReleaseRuntimeZombie} disabled={runtimeTruthBusy}>
                {runtimeTruthBusy ? "Liberando..." : "Liberar zombie"}
              </button>
            ) : null}
          </section>

          <strong>Sandbox runtime</strong>
          <span>{sandbox.running ? "servidor local activo" : "sin servidor activo"}</span>
          <code>status={sandbox.status || "idle"}</code>
          <code>tech={sandbox.technology || "auto"}</code>
          <code>port={sandbox.port || "none"}</code>
          {sandbox.url ? (
            <a className="code-workbench-sandbox-link" href={sandbox.url} target="_blank" rel="noreferrer">
              Abrir preview local
            </a>
          ) : null}
          {sandbox.embedUrl ? (
            <button
              type="button"
              className="code-workbench-sandbox-preview-button"
              onClick={onOpenSandboxPreview}
              disabled={!sandbox.running}
            >
              Ver sandbox interno
            </button>
          ) : null}
          <div className="code-workbench-sandbox-actions">
            <button type="button" onClick={onStartSandbox} disabled={!selectedProject || sandboxBusy || sandbox.running || finalSequenceActive || scannerActive}>
              {sandboxBusy && !sandbox.running ? "Arrancando..." : "Arrancar"}
            </button>
            <button type="button" onClick={onStopSandbox} disabled={!selectedProject || sandboxBusy || !sandbox.running}>
              {sandboxBusy && sandbox.running ? "Deteniendo..." : "Detener"}
            </button>
          </div>
          {sandbox.logs?.length ? (
            <pre className="code-workbench-sandbox-log">{sandbox.logs.slice(-8).join("\n")}</pre>
          ) : null}
          <code>ready={sandbox.ready === true ? "true" : "false"}</code>
          <code>preview={sandbox.previewKind || "none"}</code>
        </div>
      ) : null}

      {activePane === "tests" ? (
        <div className="code-workbench-file-list" role="listbox" aria-label="Test files">
          {testFiles.length ? (
            testFiles.map((entry) => (
              <button
                key={entry.path}
                type="button"
                className={entry.path === selectedPath ? "active" : ""}
                onClick={() => onSelectFile(entry.path)}
                disabled={finalSequenceActive || scannerActive}
                title={entry.path}
              >
                <span className="code-workbench-file-glyph">TS</span>
                <span className="code-workbench-file-main">
                  <strong>{entry.name}</strong>
                  <small>{entry.path}</small>
                </span>
              </button>
            ))
          ) : (
            <p className="code-workbench-empty">Este proyecto no expone pruebas visibles.</p>
          )}
        </div>
      ) : null}
    </aside>
  );
}
