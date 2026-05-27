import { useMemo, useState } from "react";
import { SECTION_MENU_COPY, SECTION_MENU_ITEMS } from "./SectionDividerMenu.jsx";

const PROTECTED_PROJECTS = new Set(["sesion-20260524210420", "sesion-20260524233805", "sesion-20260518014728-jeego-en-3d"]);

const RUNTIME_SECTIONS = [
  { id: "runtime", label: "01 Runtime", title: "Runtime" },
  { id: "audit", label: "02 Auditoria", title: "Auditoria" },
  { id: "observer", label: "02B Observer", title: "Observer" },
  { id: "input", label: "03 Entrada", title: "Entrada" },
  { id: "toolbox", label: "04 Toolbox", title: "Toolbox" },
  { id: "agents", label: "05 Agentes", title: "Agentes" },
  { id: "editor", label: "06 Editor", title: "Editor" },
  { id: "map", label: "07 Mapa", title: "Mapa" },
  { id: "flow", label: "08 Flujo", title: "Flujo" },
  { id: "layers", label: "09 Capas", title: "Capas" },
];

function normalizeProjectLabel(project) {
  return project?.name || project?.slug || "Proyecto";
}

function isDemoProject(project) {
  return Boolean(project?.systemDemo || project?.nativeExample || project?.demoLabel || PROTECTED_PROJECTS.has(project?.slug));
}

function scrollToSection(sectionId) {
  const target = document.getElementById(`section-${sectionId}`);
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

export default function RuntimeDashboardSidebar({
  projects = [],
  projectsLoading = false,
  projectActionStatus = "",
  newProjectName = "",
  selectedProjectSlug = "",
  onNewProjectNameChange,
  onCreateProject,
  onSelectProject,
  onArchiveProject,
  onDeleteProject,
  onOpenHarnessStudio,
}) {
  const [openSections, setOpenSections] = useState(() => ({ demoProjects: true, realProjects: true, runtime: true }));
  const [deleteModal, setDeleteModal] = useState(null);
  const sortedProjects = useMemo(
    () => [...projects].sort((a, b) => normalizeProjectLabel(a).localeCompare(normalizeProjectLabel(b))),
    [projects]
  );
  const demoProjects = useMemo(() => sortedProjects.filter(isDemoProject), [sortedProjects]);
  const realProjects = useMemo(() => sortedProjects.filter((project) => !isDemoProject(project)), [sortedProjects]);

  function toggleSection(sectionId) {
    setOpenSections((current) => ({ ...current, [sectionId]: !current[sectionId] }));
  }

  function handleCreate(event) {
    event.preventDefault();
    onCreateProject?.();
  }

  function openDeleteModal(project) {
    setDeleteModal({ project, step: "confirm", password: "", error: "", busy: false });
  }

  async function submitDeletePassword(event) {
    event.preventDefault();
    if (!deleteModal?.project?.slug || !deleteModal.password) return;
    setDeleteModal((current) => ({ ...current, busy: true, error: "" }));
    try {
      await onDeleteProject?.(deleteModal.project.slug, deleteModal.password);
      setDeleteModal(null);
    } catch (error) {
      setDeleteModal((current) => ({
        ...current,
        busy: false,
        error: error?.message || "No se pudo eliminar el proyecto.",
      }));
    }
  }

  function renderProjectRows(projectRows, emptyText) {
    if (projectsLoading) return <p>Cargando proyectos...</p>;
    if (!projectRows.length) return <p>{emptyText}</p>;
    return projectRows.map((project) => {
      const protectedProject = Boolean(project.protected || PROTECTED_PROJECTS.has(project.slug));
      const active = selectedProjectSlug === project.slug;
      const demoLabel = project.demoLabel || (project.systemDemo ? "demo interno de testeos" : "");
      return (
        <article key={project.slug} className={`runtime-project-row ${active ? "is-active" : ""}`}>
          <button type="button" className="runtime-project-select" onClick={() => onSelectProject?.(project.slug)}>
            <strong>{normalizeProjectLabel(project)}</strong>
            {demoLabel ? <span className="runtime-project-demo-label">{demoLabel}</span> : null}
            <small>{project.slug} · {project.fileCount ?? 0} archivo(s)</small>
          </button>
          <div className="runtime-project-actions">
            <button
              type="button"
              className="runtime-project-archive"
              onClick={() => onArchiveProject?.(project.slug)}
              disabled={protectedProject || projectsLoading}
              title={protectedProject ? "Proyecto protegido" : "Archivar proyecto con backup"}
            >
              {protectedProject ? "LOCK" : "Archivar"}
            </button>
            <button
              type="button"
              className="runtime-project-delete"
              onClick={() => openDeleteModal(project)}
              disabled={protectedProject || projectsLoading}
              title={protectedProject ? "Proyecto protegido" : "Eliminar proyecto con password"}
            >
              Eliminar
            </button>
          </div>
        </article>
      );
    });
  }

  const deleteProjectName = normalizeProjectLabel(deleteModal?.project || {});

  return (
    <>
    <aside className="runtime-dashboard-sidebar" aria-label="Menu lateral runtime">
      <div className="runtime-dashboard-identity">
        <button type="button" className="runtime-dashboard-primary" onClick={onOpenHarnessStudio}>
          Harness Engineering Studio
        </button>
        <small>Menu lateral de demos, proyectos reales y secciones del sistema</small>
      </div>

      <div className="runtime-dashboard-scroll" tabIndex="0">
        <section className="runtime-dashboard-card is-main">
          <button type="button" className="runtime-dashboard-toggle" onClick={() => toggleSection("demoProjects")} aria-expanded={Boolean(openSections.demoProjects)}>
            <span>PROYECTOS DEMO</span>
            <strong>{demoProjects.length}</strong>
          </button>

          {openSections.demoProjects ? (
            <div className="runtime-project-panel">
              <small className="runtime-project-panel-note">Ejemplos nativos protegidos para aprendizaje, agentes y evidencia evaluada.</small>
              <div className="runtime-project-list" aria-label="Lista de proyectos demo">
                {renderProjectRows(demoProjects, "No hay demos internos registrados.")}
              </div>
            </div>
          ) : null}
        </section>

        <section className="runtime-dashboard-card is-main">
          <button type="button" className="runtime-dashboard-toggle" onClick={() => toggleSection("realProjects")} aria-expanded={Boolean(openSections.realProjects)}>
            <span>PROYECTOS REALES</span>
            <strong>{realProjects.length}</strong>
          </button>

          {openSections.realProjects ? (
            <div className="runtime-project-panel">
              <form className="runtime-project-form" onSubmit={handleCreate}>
                <label>
                  <span>Crear nuevo proyecto real</span>
                  <input
                    value={newProjectName}
                    onChange={(event) => onNewProjectNameChange?.(event.target.value)}
                    placeholder="nombre del proyecto"
                    autoComplete="off"
                  />
                </label>
                <button type="submit" className="runtime-dashboard-action" disabled={projectsLoading || !newProjectName.trim()}>
                  OK
                </button>
              </form>

              {projectActionStatus ? <p className="runtime-dashboard-status">{projectActionStatus}</p> : null}

              <div className="runtime-project-list" aria-label="Lista de proyectos reales">
                {renderProjectRows(realProjects, "Aun no hay proyectos reales. Crea el primero con el campo superior.")}
              </div>
            </div>
          ) : null}
        </section>

        <nav className="runtime-dashboard-nav" aria-label="Secciones del sistema">
          {RUNTIME_SECTIONS.map((section) => {
            const menuItems = SECTION_MENU_ITEMS[section.id] || [];
            const open = Boolean(openSections[section.id]);
            return (
              <section key={section.id} className="runtime-dashboard-card runtime-nav-section">
                <div className="runtime-nav-row">
                  <button type="button" className="runtime-nav-jump" onClick={() => scrollToSection(section.id)}>
                    <span>{section.label}</span>
                    <strong>{section.title}</strong>
                  </button>
                  <button type="button" className="runtime-nav-expand" onClick={() => toggleSection(section.id)} aria-expanded={open}>
                    {open ? "-" : "+"}
                  </button>
                </div>
                {open ? (
                  <div className="runtime-nav-menu">
                    <small>{SECTION_MENU_COPY[section.id] || "Menu contextual"}</small>
                    {menuItems.map((item) => (
                      <button key={item} type="button" onClick={() => scrollToSection(section.id)}>
                        {item}
                      </button>
                    ))}
                  </div>
                ) : null}
              </section>
            );
          })}
        </nav>
      </div>
    </aside>

    {deleteModal ? (
      <div className="runtime-delete-overlay" role="dialog" aria-modal="true" aria-label="Eliminar proyecto">
        <div className="runtime-delete-modal">
          <div className="runtime-delete-badge">WARNING</div>
          <h2>Eliminar proyecto permanentemente</h2>
          <p>
            Vas a eliminar <strong>{deleteProjectName}</strong> de <code>workspace/projects</code>. Antes de borrar se creara un backup tecnico en runtime.
          </p>
          <code>{deleteModal.project?.slug}</code>

          {deleteModal.step === "confirm" ? (
            <div className="runtime-delete-actions">
              <button type="button" className="runtime-delete-cancel" onClick={() => setDeleteModal(null)}>Cancelar</button>
              <button type="button" className="runtime-delete-danger" onClick={() => setDeleteModal((current) => ({ ...current, step: "password", error: "" }))}>
                Si, continuar
              </button>
            </div>
          ) : (
            <form className="runtime-delete-form" onSubmit={submitDeletePassword}>
              <label>
                <span>Password eliminador de archivos</span>
                <input
                  type="password"
                  value={deleteModal.password}
                  onChange={(event) => setDeleteModal((current) => ({ ...current, password: event.target.value, error: "" }))}
                  autoFocus
                  autoComplete="current-password"
                />
              </label>
              {deleteModal.error ? <p className="runtime-delete-error">{deleteModal.error}</p> : null}
              <div className="runtime-delete-actions">
                <button type="button" className="runtime-delete-cancel" onClick={() => setDeleteModal(null)} disabled={deleteModal.busy}>Cancelar</button>
                <button type="submit" className="runtime-delete-danger" disabled={deleteModal.busy || !deleteModal.password}>
                  {deleteModal.busy ? "Eliminando..." : "Eliminar ahora"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    ) : null}
    </>
  );
}
