export default function CodeWorkbenchGutter({
  gutterRef,
  lineNumbers,
  targetLine,
  visibleIntegrityLines,
  agentChangeLine,
  activeIssueTarget,
  onTargetClick,
}) {
  return (
    <pre ref={gutterRef} className="code-workbench-gutter" aria-hidden="true">
      {lineNumbers.map((line) => (
        <span
          key={line}
          className={[line === targetLine ? "is-target" : "", visibleIntegrityLines.has(line) ? "has-integrity" : "", line === agentChangeLine ? "has-agent-change" : ""].filter(Boolean).join(" ")}
          onClick={() => {
            if (line === targetLine && activeIssueTarget) onTargetClick();
          }}
        >
          {line}
        </span>
      ))}
    </pre>
  );
}
