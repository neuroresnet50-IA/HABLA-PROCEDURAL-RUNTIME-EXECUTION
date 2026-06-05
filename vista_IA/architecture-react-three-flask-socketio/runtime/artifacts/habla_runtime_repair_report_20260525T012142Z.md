# HABLA/Codex runtime repair report

Generated: 2026-05-25T01:21:42.881454+00:00

## Result

Runtime repaired and validated with real HTTP endpoints and real Codex session starts. No protected project was deleted, no runtime directory was deleted without backup, `backend/app.py` was patched in place, and CyberLACE remains in monitor mode.

## Repairs Applied

- Socket.IO is polling-only under Werkzeug/threading; backend advertises `upgrades: []`, and frontend clients set `transports: ["polling"]` with upgrade disabled.
- `/api/agent/session` and `agent:session:start` return before `sync_runtime_graph(save_state=True)`; heavy runtime preparation continues in background.
- Added `preparing` as an active session/project state. API serialization prevents `running` with `pid=null`.
- Control-plane `running` is assigned only after a real worker PID is attached.
- `stop_session` now persists manual stop for control-plane sessions: blocks all persisted `running` tasks, clears `current_task_id`, sets project state to `stopped`, and writes checkpoint/failure evidence.
- Runtime-truth/zombie release detects and repairs persisted running state with no live session or PID, with backups and checkpoint.
- Internal preflight writes terminal output before optional tools; observer/internal tool timeout is warning/continue, not a startup blocker.

## Protected Projects

- `workspace/projects/sesion-20260524210420`: present, `fileCount=4`, runtime-truth `verdict=idle`, `stale=false`, `running=0`.
- `workspace/projects/sesion-20260524233805`: present, `fileCount=4`, runtime-truth `verdict=idle`, `stale=false`, `running=0`; zombie release checkpoint `runtime-zombie-recovered-20260525T011351Z`.

Visible editor files reopened by API for both projects: `docs/habla-session.md`, `LACE.md`, `LACE_LOG.md`. Hidden `.agent-project.json` exists physically in both project roots and accounts for the fourth source file.

## Real Session Evidence

- `sesion-20260524210420`: `/api/agent/session` returned HTTP 200 in `0.014404s`; session `agent-33161f4b63` reached `running` with real PID `2518092`, then stopped with concrete reason `manual_stop/control_plane_stopped`.
- `sesion-20260524233805`: session `agent-d6ff031021` reached `running` with real worker evidence (`worker_pid=2521187` in reviewer log, later PID `2524159` observed), CyberLACE stayed `monitor`, and the stopped orphan persisted state was repaired to idle with backup/checkpoint.

## Final Validation After Restart

- `python3 -B -m py_compile backend/app.py backend/agent_runtime.py orchestrator/tool_invocation_policy.py`: passed.
- `python3 -B -m compileall -q orchestrator`: passed.
- `npm --prefix frontend run build`: passed.
- `OPEN_BROWSER=0 ./start.sh restart`: passed, backend PID `2556636`.
- `/api/health`: HTTP 200, `0.803612s`.
- `/api/agent/sessions`: HTTP 200, `0.030343s`, `sessions=[]`.
- `/api/agent/projects`: HTTP 200, `1.147446s`; both protected projects listed with `fileCount=4`.
- `/api/cyberlace/health`: HTTP 200, `0.277750s`, `mode=monitor`.
- `/api/projects/sesion-20260524210420/runtime-truth`: HTTP 200, `0.662816s`, `verdict=idle`, `stale=false`, `persistedRunning=false`.
- `/api/projects/sesion-20260524233805/runtime-truth`: HTTP 200, `0.435409s`, `verdict=idle`, `stale=false`, `persistedRunning=false`.
- UI root `/`: HTTP 200, `0.267122s`, compiled app served by backend.
- UI assets: JS HTTP 200 (`474296` bytes), CSS HTTP 200 (`95039` bytes).
- Socket.IO polling handshake: HTTP 200, `upgrades=[]`.
- Log scan: no `agent_session_start_timeout`, no WebSocket/Socket.IO HTTP 500. Old browser tabs still produced WebSocket HTTP 400 upgrade attempts; the repaired path is polling-only and does not produce 500.

## Backups And Checkpoints

- Initial checkpoint: `runtime/checkpoints/habla-runtime-repair-start-20260525T003746Z.json`.
- Code checkpoint: `runtime/checkpoints/habla-runtime-repair-code-20260525T010640Z.json`.
- This final checkpoint: `runtime/checkpoints/habla-runtime-repair-final-20260525T012142Z.json`.
- State repair backups: `workspace/projects/*/runtime/backups/habla_runtime_repair/20260525T005750Z/`.
- Zombie release backup: `workspace/projects/sesion-20260524233805/runtime/backups/zombie_release/20260525T011351Z/`.
- Zombie release checkpoint: `workspace/projects/sesion-20260524233805/runtime/checkpoints/runtime-zombie-recovered-20260525T011351Z.json`.
