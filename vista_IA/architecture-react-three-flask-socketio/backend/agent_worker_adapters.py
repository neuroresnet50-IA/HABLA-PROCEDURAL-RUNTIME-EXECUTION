"""Session worker adapters for AgentRuntime."""

from __future__ import annotations

from typing import Any, Protocol


class SessionWorkerAdapter(Protocol):
    """Adapter contract for one AgentRuntime session execution path."""

    name: str
    worker_kind: str

    def run(self, runtime: Any, session_id: str) -> None:
        """Run one session using the selected execution backend."""


class ControlPlaneSessionWorkerAdapter:
    name = "control_plane_session"
    worker_kind = "control_plane"

    def run(self, runtime: Any, session_id: str) -> None:
        runtime._run_control_plane_session(session_id)


class LegacyPtySessionWorkerAdapter:
    name = "legacy_pty_session"
    worker_kind = "legacy_pty"

    def run(self, runtime: Any, session_id: str) -> None:
        runtime._run_legacy_pty_session(session_id)


def select_session_worker_adapter(control_plane_enabled: bool) -> SessionWorkerAdapter:
    if control_plane_enabled:
        return ControlPlaneSessionWorkerAdapter()
    return LegacyPtySessionWorkerAdapter()
