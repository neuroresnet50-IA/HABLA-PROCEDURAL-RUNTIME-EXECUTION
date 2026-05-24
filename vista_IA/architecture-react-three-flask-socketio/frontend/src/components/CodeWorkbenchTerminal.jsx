export default function CodeWorkbenchTerminal({ activePane, terminalLines, onPaneChange }) {
  return (
    <div className="code-workbench-terminal">
      <div>
        <button type="button" className={activePane === "problems" ? "active" : ""} onClick={() => onPaneChange("problems")}>PROBLEMS</button>
        <button type="button" className={activePane === "explorer" ? "active" : ""} onClick={() => onPaneChange("explorer")}>OUTPUT</button>
        <button type="button" className={activePane === "runtime" ? "active" : ""} onClick={() => onPaneChange("runtime")}>TERMINAL</button>
      </div>
      <pre>{terminalLines.join("\n")}</pre>
    </div>
  );
}
