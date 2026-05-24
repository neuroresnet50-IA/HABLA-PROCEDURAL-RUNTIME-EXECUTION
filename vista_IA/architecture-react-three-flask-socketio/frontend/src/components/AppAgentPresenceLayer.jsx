export default function AppAgentPresenceLayer({ active, presence, mode }) {
  if (!active) return null;

  return (
    <>
      <div className={`agent-presence-overlay is-${presence.area} ${mode ? "is-repair-mode" : ""}`} aria-live="polite">
        <span className="agent-presence-orb" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <div>
          <strong>{mode || "Maquina agente en observacion"}</strong>
          <span>{presence.phase}</span>
          <small>{mode ? `${presence.detail} · reparacion agentica` : presence.detail}</small>
        </div>
      </div>
      <div className="agent-presence-cursor" aria-hidden="true">
        <span />
      </div>
      {presence.microMessage ? (
        <div className="agent-presence-micro-modal" aria-hidden="true">
          <strong>{presence.microMessage}</strong>
          <span>{presence.detail}</span>
        </div>
      ) : null}
    </>
  );
}
