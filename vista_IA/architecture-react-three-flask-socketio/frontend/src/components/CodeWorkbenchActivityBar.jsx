export default function CodeWorkbenchActivityBar({ activePane, onPaneChange, onProblemsOpen }) {
  return (
    <aside className="code-workbench-activity" aria-label="Activity bar">
      <button type="button" className={activePane === "explorer" ? "active" : ""} title="Explorer" onClick={() => onPaneChange("explorer")}>EX</button>
      <button type="button" className={activePane === "problems" ? "active" : ""} title="Problems" onClick={onProblemsOpen}>PR</button>
      <button type="button" className={activePane === "runtime" ? "active" : ""} title="Runtime" onClick={() => onPaneChange("runtime")}>RT</button>
      <button type="button" className={activePane === "tests" ? "active" : ""} title="Tests" onClick={() => onPaneChange("tests")}>TS</button>
    </aside>
  );
}
