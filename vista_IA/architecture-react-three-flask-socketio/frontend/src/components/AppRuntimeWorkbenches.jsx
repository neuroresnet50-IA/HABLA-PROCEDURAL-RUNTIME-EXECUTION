import AgentStudio from "./AgentStudio.jsx";
import CodeWorkbench from "./CodeWorkbench.jsx";
import SectionDividerMenu from "./SectionDividerMenu.jsx";
import { SOCKET_URL } from "../appUtils.js";

export default function AppRuntimeWorkbenches({
  focusedProject,
  editorJumpTarget,
  editorExpanded,
  onSceneFocus,
  onWorkspaceClean,
  onCyberlaceBlock,
  onRepairPresenceStart,
  autonomousMode = false,
  onToggleEditorExpanded,
}) {
  function dispatchEditorAutonomy(action) {
    if (!autonomousMode) return;
    const actionId = `section-06-${String(action || "auto_closure").replace(/[^a-z0-9_-]/gi, "-")}-${Date.now()}`;
    const detail = {
      action,
      actionId,
      source: "section-06-editor",
      reason: "section_06_editor_button",
      projectSlug: focusedProject || "",
      requestedAt: new Date().toISOString(),
    };
    window.dispatchEvent(new CustomEvent("habla:section-menu-close", {
      detail: { id: "editor", reason: "editor_autonomy_action", actionId },
    }));
    window.setTimeout(() => {
      window.dispatchEvent(new CustomEvent("habla:editor-autonomy-action", { detail }));
    }, 180);
  }

  return (
    <>
      <SectionDividerMenu id="agents" label="05 Agentes" title="Agentes" />

      <AgentStudio
        socketUrl={SOCKET_URL}
        onSceneFocus={onSceneFocus}
        onWorkspaceClean={onWorkspaceClean}
        onCyberlaceBlock={onCyberlaceBlock}
        autonomousMode={autonomousMode}
      />

      <SectionDividerMenu id="editor" label="06 Editor" title="Editor de codigo">
        <button type="button" className="section-menu-primary" onClick={onToggleEditorExpanded}>
          {editorExpanded ? "Cerrar editor expandido" : "Abrir editor expandido"}
        </button>
        <button
          type="button"
          className="section-menu-secondary"
          onClick={() => document.getElementById("code-workbench")?.scrollIntoView({ behavior: "smooth", block: "start" })}
        >
          Enfocar editor
        </button>
        <div className="section-menu-autonomy">
          <strong>Autonomia de modales</strong>
          <small>{autonomousMode ? "Mouse operativo autorizado para clicks reales del editor." : "Activa modo autonomo para permitir estos clicks."}</small>
          <div>
            <button type="button" disabled={!autonomousMode} onClick={() => dispatchEditorAutonomy("auto_closure")}>Autoclick cierre pendiente</button>
            <button type="button" disabled={!autonomousMode} onClick={() => dispatchEditorAutonomy("send_repair")}>Enviar a reparador</button>
            <button type="button" disabled={!autonomousMode} onClick={() => dispatchEditorAutonomy("minimize_certificate")}>Minimizar certificado</button>
            <button type="button" disabled={!autonomousMode} onClick={() => dispatchEditorAutonomy("open_supervisor")}>Ver supervisor</button>
          </div>
        </div>
      </SectionDividerMenu>

      <CodeWorkbench
        socketUrl={SOCKET_URL}
        focusedProject={focusedProject}
        jumpTarget={editorJumpTarget}
        expanded={editorExpanded}
        onRepairPresenceStart={onRepairPresenceStart}
      />
    </>
  );
}
