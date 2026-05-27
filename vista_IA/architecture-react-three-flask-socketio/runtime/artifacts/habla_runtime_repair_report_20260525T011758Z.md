# HABLA/Codex runtime repair report

Generated: 2026-05-25T01:17:58.548576+00:00

## Result

Runtime repaired and validated against real HTTP endpoints and real Codex session starts. No protected project was deleted, no runtime directory was deleted, backend/app.py was patched in place, and CyberLACE remains in monitor mode.

## Main repairs

- Socket.IO runs polling-only under Werkzeug/threading; frontend clients use polling with upgrade disabled.
- `/api/agent/session` and `agent:session:start` return before graph sync; heavy preparation runs in background.
- Added `preparing`; API no longer reports `running` with `pid=null`.
- `runtime-truth` detects `running_without_pid`, orphaned persisted running state, dead worker PID, and blocked-state/pending-queue mismatches.
- Zombie release now backs up `project_state.json` and `task_queue.json`, requeues orphaned active tasks to `pending`, records failure, and writes checkpoint.
- Internal preflight emits terminal output before optional tools; internal tool timeout is warning/continue, not startup blocker.

## Protected projects

- `workspace/projects/sesion-20260524210420`: present, fileCount=4, runtime-truth `idle`, `stale=false`.
- `workspace/projects/sesion-20260524233805`: present, fileCount=4, runtime-truth `idle`, `stale=false`; zombie release checkpoint `runtime-zombie-recovered-20260525T011351Z`.

Visible editor files reopened by API for both projects: `LACE.md`, `LACE_LOG.md`, `docs/habla-session.md`. Hidden `.agent-project.json` exists physically in both project roots.

## Real session evidence

- `sesion-20260524210420`: `/api/agent/session` responded in 0.05s, session `agent-33161f4b63`, observed `running` with PID `2518092`, then stopped cleanly (`control_plane_stopped`).
- `sesion-20260524233805`: `/api/agent/session` responded in 0.048s, session `agent-d6ff031021`, observed `running` with real PIDs `2521187`/`2524159`; stop left an orphaned persisted running task, then runtime-truth marked it zombie and `/runtime-zombie/release` requeued it with backup/checkpoint.

## Final validation

- `python3 -B -m py_compile backend/app.py backend/agent_runtime.py orchestrator/*.py`: passed.
- `npm --prefix frontend run build`: passed.
- `OPEN_BROWSER=0 ./start.sh restart`: passed, backend PID `2548213`.
- `/api/health`: HTTP 200, 0.736s.
- `/api/agent/sessions`: HTTP 200, 0.034s.
- `/api/agent/projects`: HTTP 200, 0.778s; both protected projects listed.
- `/api/cyberlace/health`: HTTP 200, 0.337s; `mode=monitor`.
- `/api/projects/sesion-20260524210420/runtime-truth`: HTTP 200, 0.540s; `verdict=idle`, `stale=false`, warnings 0.
- `/api/projects/sesion-20260524233805/runtime-truth`: HTTP 200, 0.431s; `verdict=idle`, `stale=false`, warnings 0.
- Socket.IO polling: HTTP 200, `upgrades=[]`.
- UI root `/`: HTTP 200 and serves compiled assets.
- Final backend log scan: no `agent_session_start_timeout`, no HTTP 500, no traceback.

## Notes

Old browser tabs still attempted `transport=websocket` and received HTTP 400. The repaired server/client path uses controlled polling and no WebSocket 500 appeared in final logs.

Backups/checkpoints:

- `runtime/checkpoints/habla-runtime-repair-code-20260525T010640Z.json`
- `runtime/checkpoints/habla-runtime-repair-final-20260525T011758Z.json`
- `workspace/projects/sesion-20260524233805/runtime/backups/zombie_release/20260525T011351Z/`
- `workspace/projects/sesion-20260524233805/runtime/checkpoints/runtime-zombie-recovered-20260525T011351Z.json`
