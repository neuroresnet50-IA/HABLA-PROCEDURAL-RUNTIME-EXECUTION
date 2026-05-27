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
  onToggleEditorExpanded,
}) {
  return (
    <>
      <SectionDividerMenu id="agents" label="05 Agentes" title="Agentes" />

      <AgentStudio
        socketUrl={SOCKET_URL}
        onSceneFocus={onSceneFocus}
        onWorkspaceClean={onWorkspaceClean}
        onCyberlaceBlock={onCyberlaceBlock}
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
