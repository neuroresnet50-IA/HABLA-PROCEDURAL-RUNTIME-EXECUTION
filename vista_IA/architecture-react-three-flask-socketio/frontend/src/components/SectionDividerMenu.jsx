import { useMemo, useState } from "react";

export const SECTION_MENU_ITEMS = {
  runtime: ["Estado del runtime", "Modo autonomo", "Escenas activas", "Reiniciar vista"],
  audit: ["Auditar mapa", "Hallazgos por severidad", "Navegar a errores", "Reporte de coherencia"],
  observer: ["Decision actual", "Memoria", "Behavior tree", "Timeline"],
  input: ["Analizar ruta", "Transcribir con agente", "Escenas cargadas", "Limpiar entrada"],
  toolbox: ["Mapa conceptual", "Nuevo programa", "Bloque manual", "Persistencia"],
  agents: ["Crear tarea", "Continuar sesion", "Borrar colas pendientes", "Revisar locks"],
  editor: ["Explorador de archivos", "Editor expandido", "Problemas", "Sandbox"],
  map: ["Seleccionar nodos", "Conectar bloques", "Centrar escena", "Ver dependencias"],
  flow: ["Iniciar secuencia", "Mover pasos", "Conectar flujo", "Sandbox interno"],
  layers: ["Vista por capa", "Filtrar capa", "Seleccionar bloque", "Orden visual"],
};

export const SECTION_MENU_COPY = {
  runtime: "Panel operativo de estado, escena activa y control superior.",
  audit: "Herramientas de revision para coherencia del mapa y hallazgos navegables.",
  observer: "Lectura de decisiones, memoria y eventos del plano Observer.",
  input: "Entrada de rutas locales y transcripcion inicial con agente.",
  toolbox: "Creacion y persistencia de bloques, programas y conexiones.",
  agents: "Control del runtime agentico, tareas, colas y sesiones.",
  editor: "Edicion directa de archivos del proyecto con vista ampliada.",
  map: "Mapa conceptual editable con nodos, flechas y dependencias.",
  flow: "Diagrama interno de pasos, decisiones y secuencia del algoritmo.",
  layers: "Organizacion por capas para navegar bloques del ecosistema.",
};

export default function SectionDividerMenu({
  id,
  label,
  title,
  menuItems,
  children,
  align = "left",
}) {
  const [open, setOpen] = useState(false);
  const items = useMemo(() => menuItems || SECTION_MENU_ITEMS[id] || [], [id, menuItems]);
  const summary = SECTION_MENU_COPY[id] || "Menu contextual de la seccion.";

  return (
    <div id={`section-${id}`} className={`gemini-section-divider ${open ? "is-open" : ""} align-${align}`} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        className="gemini-section-divider-button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((current) => !current)}
      >
        <span>{label}</span>
      </button>

      {open ? (
        <div className={`section-menu-popover ${id === "editor" ? "is-editor-menu" : ""}`} role="dialog" aria-label={`Menu ${label}`}>
          <div className="section-menu-header">
            <strong>{title || label}</strong>
            <small>{summary}</small>
          </div>
          <div className="section-menu-list">
            {items.map((item) => (
              <button key={item} type="button">
                {item}
              </button>
            ))}
          </div>
          {children ? <div className="section-menu-custom">{children}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
