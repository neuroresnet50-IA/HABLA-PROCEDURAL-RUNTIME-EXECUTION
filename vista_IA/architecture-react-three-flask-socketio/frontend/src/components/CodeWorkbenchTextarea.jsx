export default function CodeWorkbenchTextarea({
  editorRef,
  draft,
  readOnly,
  selectedPath,
  selectedProject,
  onDraftChange,
  onEditorScroll,
}) {
  return (
    <textarea
      ref={editorRef}
      spellCheck="false"
      value={draft}
      readOnly={readOnly}
      onChange={(event) => onDraftChange(event.target.value)}
      onScroll={onEditorScroll}
      placeholder={selectedProject ? "Selecciona un archivo generado por los agentes." : "No hay proyecto seleccionado."}
    />
  );
}
