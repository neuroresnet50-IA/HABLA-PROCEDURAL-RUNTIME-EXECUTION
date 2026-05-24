import { useEffect, useRef } from "react";

function agentMessageLabel(role) {
  if (role === "user") return "Tu";
  if (role === "delegate") return "Monitor";
  return "Monitor";
}

export default function CodeWorkbenchAgentChat({
  selectedProject,
  selectedPath,
  selectedFileMeta,
  lock,
  messages,
  events,
  draft,
  sending,
  open = true,
  onDraftChange,
  onSubmit,
  onClear,
  onToggleOpen,
  automation,
  onDelegateAssist,
}) {
  const textareaRef = useRef(null);
  const submitButtonRef = useRef(null);
  const isAutomating = Boolean(automation?.active);
  const automationPhase = automation?.phase || "idle";
  const runtimeDisabled = sending || !selectedProject;
  const disabled = runtimeDisabled || isAutomating;
  const recentEvents = (events || []).slice(-8);
  const visibleMessages = (messages || []).slice(-6);
  const liveCount = recentEvents.filter((event) => event.kind !== "idle").length;

  useEffect(() => {
    if (!isAutomating) return;
    if (automationPhase === "focus" || automationPhase === "type") {
      textareaRef.current?.focus();
    }
    if (automationPhase === "submit") {
      submitButtonRef.current?.focus();
    }
  }, [automationPhase, isAutomating]);

  if (!open) {
    return (
      <section className={`code-workbench-agent-chat is-collapsed ${isAutomating ? "is-agent-piloted" : ""}`} aria-label="Agent chat collapsed">
        <button type="button" className="agent-chat-open-button" onClick={onToggleOpen}>
          <strong>Monitor verde</strong>
          <span>{isAutomating ? "consultando" : liveCount ? `${liveCount} evento(s)` : "abrir"}</span>
        </button>
      </section>
    );
  }

  return (
    <section className={`code-workbench-agent-chat ${isAutomating ? "is-agent-piloted" : ""} is-phase-${automationPhase}`} aria-label="Monitor verde">
      {isAutomating ? <div className="agent-chat-virtual-cursor" aria-hidden="true"><span /></div> : null}
      <div className="agent-chat-header">
        <div>
          <strong>Monitor verde</strong>
          <small>{selectedPath || "runtime del proyecto"}</small>
          {isAutomating ? <em className="agent-chat-pilot-label">{automation?.label || "agente operando chat"}</em> : null}
        </div>
        <div className="agent-chat-header-actions">
          <button type="button" onClick={onDelegateAssist} disabled={disabled || !onDelegateAssist}>
            Monitorear
          </button>
          <button type="button" onClick={onToggleOpen}>
            Ocultar
          </button>
          <button type="button" onClick={onClear} disabled={!messages?.length && !events?.length}>
            Limpiar
          </button>
        </div>
      </div>

      <div className="agent-chat-context">
        <span>{selectedProject || "sin proyecto"}</span>
        <span>{selectedFileMeta?.name || selectedPath || "sin archivo"}</span>
      </div>

      <div className="agent-chat-activity" aria-live="polite">
        {recentEvents.length ? (
          recentEvents.map((event) => (
            <article key={event.id} className={`agent-chat-event is-${event.kind || "working"}`}>
              <span className="agent-chat-event-dot" aria-hidden="true" />
              <div>
                <strong>{event.label}</strong>
                <small>{event.path || event.message}</small>
              </div>
            </article>
          ))
        ) : (
          <article className="agent-chat-event is-idle">
            <span className="agent-chat-event-dot" aria-hidden="true" />
            <div>
              <strong>Ready</strong>
              <small>monitor independiente listo</small>
            </div>
          </article>
        )}
      </div>

      <div className="agent-chat-messages">
        {visibleMessages.length ? (
          visibleMessages.map((message) => (
            <article key={message.id} className={`agent-chat-message is-${message.role}`}>
              <span>{agentMessageLabel(message.role)}</span>
              <p>{message.text}</p>
            </article>
          ))
        ) : (
          <article className="agent-chat-message is-system">
            <span>Monitor</span>
            <p>Pregunta que esta pasando en el runtime o en la tarea activa.</p>
          </article>
        )}
      </div>

      <form className="agent-chat-form" onSubmit={onSubmit}>
        <textarea
          ref={textareaRef}
          className={isAutomating ? "is-agent-typing" : ""}
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="Preguntar al monitor verde..."
          rows={3}
          disabled={sending || !selectedProject}
          readOnly={isAutomating}
        />
        <button ref={submitButtonRef} type="submit" className={automationPhase === "submit" ? "is-agent-submit-target" : ""} disabled={runtimeDisabled || !draft.trim()}>
          {sending ? "Consultando" : "Preguntar"}
        </button>
      </form>
    </section>
  );
}
