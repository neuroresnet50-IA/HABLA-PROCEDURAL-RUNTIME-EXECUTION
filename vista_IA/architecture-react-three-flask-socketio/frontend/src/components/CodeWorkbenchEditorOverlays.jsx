export default function CodeWorkbenchEditorOverlays({
  visibleIntegrityMarkers,
  lock,
  liveWriter,
  finalSequence,
  codeScanner,
}) {
  return (
    <>
      {visibleIntegrityMarkers.length ? (
        <div className="code-workbench-integrity-overlay" aria-hidden="true">
          {visibleIntegrityMarkers.map((marker) => (
            <span
              key={marker.id}
              className={`code-workbench-integrity-marker ${marker.className}`}
              title={`${marker.label}: ${marker.message}`}
              style={{
                "--integrity-x": `${marker.x}px`,
                "--integrity-y": `${marker.y}px`,
                "--integrity-width": `${marker.width}px`,
              }}
            />
          ))}
        </div>
      ) : null}
      {lock.locked ? (
        <div className="code-workbench-readonly-banner">
          Lectura en vivo: {lock.message || "el agente sigue trabajando."}
        </div>
      ) : null}
      {liveWriter.active ? (
        <div className="code-workbench-writer-banner">
          <strong>{finalSequence.active ? "Typewriter final" : "IA escribiendo"}</strong>
          <span>{liveWriter.message || `IA escribiendo ${liveWriter.path}`}</span>
        </div>
      ) : null}
      {codeScanner.active ? (
        <div className="code-workbench-scanner-overlay" aria-live="polite">
          <div className="code-workbench-scanner-beam" />
          <div className="code-workbench-scanner-lens" aria-hidden="true">
            <span />
          </div>
          <div className="code-workbench-scanner-target" aria-hidden="true" />
          <div className="code-workbench-scanner-banner">
            <strong>Scanner final</strong>
            <span>{codeScanner.path || "preparando lectura"}</span>
            <small>
              archivo {codeScanner.fileIndex}/{codeScanner.totalFiles || "..."} · linea {codeScanner.line}/{codeScanner.totalLines || "..."} · {Math.round(codeScanner.percent)}%
            </small>
            <i><b style={{ width: `${Math.max(0, Math.min(100, codeScanner.percent))}%` }} /></i>
          </div>
        </div>
      ) : null}
    </>
  );
}
