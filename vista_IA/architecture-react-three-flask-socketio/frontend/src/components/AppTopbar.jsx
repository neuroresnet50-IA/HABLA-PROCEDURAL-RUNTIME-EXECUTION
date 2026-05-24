import { HABLA_OBSERVER_LOGO_SRC } from "../appUtils.js";

export default function AppTopbar({
  connected,
  agentVisual,
  autonomousMode,
  visibleGraph,
  workspaceSceneOptions,
  effectiveWorkspaceScene,
  viewAllWorkspaceScenes,
  defaultWorkspaceScene,
  isResetting,
  onToggleAutonomousMode,
  onViewAllScenes,
  onReturnActiveProject,
  onLoadHablaDemo,
  onResetView,
}) {
  return (
    <header className="topbar">
      <div className="habla-brand-lockup">
        <h1 className="habla-logo-title" aria-label="HABLA Observer IA">
          <img
            src={HABLA_OBSERVER_LOGO_SRC}
            alt="HABLA Observer IA Logo Animado"
            className="habla-logo-animado"
          />
          <span className="sr-only">HABLA Observer IA</span>
        </h1>
        <div className="habla-brand-copy">
          <p className="eyebrow">HABLA Observer IA</p>
          <p className="topbar-subtitle">Tu descubrimiento, tu destino</p>
        </div>
      </div>
      <div className="topbar-actions">
        <span className={`socket-pill ${connected ? "is-online" : "is-offline"}`}>
          {connected ? "Socket conectado" : "Socket desconectado"}
        </span>
        <span className={`socket-pill ${agentVisual?.phase || agentVisual?.op ? "is-online" : "is-offline"}`}>
          {agentVisual?.phase ? `Agente: ${agentVisual.phase}` : "Agente en espera"}
        </span>
        <button
          type="button"
          className={`tool-button ${autonomousMode ? "active" : ""}`}
          onClick={onToggleAutonomousMode}
          title="Atajo: tecla A"
          aria-keyshortcuts="A"
        >
          {autonomousMode ? "Autonomo activo" : "Modo autonomo"}
        </button>
        <span className="meta-pill">{visibleGraph.metadata?.generatedCount || visibleGraph.nodes.length} bloques</span>
        {workspaceSceneOptions.length ? (
          <span className="meta-pill">
            {viewAllWorkspaceScenes ? "Vista global" : `Proyecto: ${workspaceSceneOptions.find((scene) => scene.key === effectiveWorkspaceScene)?.label || effectiveWorkspaceScene}`}
          </span>
        ) : null}
        {effectiveWorkspaceScene && !viewAllWorkspaceScenes ? (
          <button type="button" className="tool-button" onClick={onViewAllScenes}>
            Ver todas las escenas
          </button>
        ) : null}
        {viewAllWorkspaceScenes && defaultWorkspaceScene ? (
          <button type="button" className="tool-button" onClick={onReturnActiveProject}>
            Volver al proyecto activo
          </button>
        ) : null}
        <a className="tool-button" href="#code-workbench">
          Abrir editor
        </a>
        <button type="button" className="tool-button" onClick={onLoadHablaDemo} disabled={isResetting}>
          Demo arquitectura HABLA
        </button>
        <button type="button" className="tool-button danger" onClick={onResetView} disabled={isResetting}>
          {isResetting ? "Reseteando..." : "Resetear vista"}
        </button>
      </div>
    </header>
  );
}
