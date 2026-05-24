import SectionDividerMenu from "./SectionDividerMenu.jsx";
import { formatLintSeverity, formatUpdatedAt } from "../appUtils.js";

export default function AppLintPanel({
  visibleGraph,
  lintReport,
  lintScopeLabel,
  lintScopeScene,
  lintError,
  isLinting,
  agentVisual,
  onLoadLintReport,
  onFindingNavigation,
}) {
  return (
    <>
      <section className="summary-card">
        <strong>{visibleGraph.metadata?.projectName || "Proyecto"}</strong>
        <span>{visibleGraph.metadata?.note || "Editor visual para mapa conceptual, diagrama de flujo y codigo interno."}</span>
        {lintReport.summary?.total ? <span className="meta-pill">Alertas visuales: {lintReport.summary.total}</span> : null}
        {agentVisual?.message ? <small>Actividad del agente: {agentVisual.message}</small> : null}
        <small>Ultima actualizacion: {formatUpdatedAt(visibleGraph.metadata?.updatedAt)}</small>
      </section>

      <SectionDividerMenu id="audit" label="02 Auditoria" title="Auditoria" />

      <section className="lint-panel">
        <div className="panel-header compact">
          <div>
            <h2>Auditoria del mapa</h2>
            <p>Revisa coherencia de escenas, capas y dependencias reales segun el codigo y los archivos del proyecto.</p>
          </div>
          <div className="toolbar-inline compact">
            <span className="meta-pill">{lintScopeLabel}</span>
            <button type="button" className="tool-button" onClick={() => onLoadLintReport(lintScopeScene)} disabled={isLinting}>
              {isLinting ? "Auditando..." : "Auditar mapa"}
            </button>
          </div>
        </div>

        <div className="lint-body">
          <div className="lint-summary">
            <span className="lint-count error">Errores: {lintReport.summary?.error || 0}</span>
            <span className="lint-count warning">Advertencias: {lintReport.summary?.warning || 0}</span>
            <span className="lint-count info">Info: {lintReport.summary?.info || 0}</span>
            <span className="lint-count total">Total: {lintReport.summary?.total || 0}</span>
          </div>

          {lintError ? <p className="agent-error">{lintError}</p> : null}

          {lintReport.findings?.length ? (
            <div className="lint-findings">
              {lintReport.findings.map((finding, index) => (
                <article
                  key={`${finding.code}-${finding.path || "global"}-${index}`}
                  className={`lint-finding ${finding.severity} is-clickable`}
                  role="button"
                  tabIndex="0"
                  onClick={() => onFindingNavigation(finding)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") onFindingNavigation(finding);
                  }}
                >
                  <div className="lint-finding-header">
                    <span className={`severity-badge ${finding.severity}`}>{formatLintSeverity(finding.severity)}</span>
                    <strong>{finding.message}</strong>
                  </div>
                  {finding.path ? <code className="lint-path">{finding.path}</code> : null}
                  {finding.line ? <small>Linea {finding.line}</small> : null}
                  {finding.hint ? <p>{finding.hint}</p> : null}
                  <small>{finding.code}</small>
                </article>
              ))}
            </div>
          ) : (
            <p className="lint-clean">
              {isLinting ? "Revisando coherencia del mapa..." : "Sin hallazgos en este alcance. Selecciona un bloque para auditar una escena especifica."}
            </p>
          )}
        </div>
      </section>
    </>
  );
}
