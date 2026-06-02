# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-032

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-032`
- durationSeconds: `63.208869`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `7.184` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.065` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `16.143` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.707` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `16.09` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `2.561` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.975` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `32.226` | Backend health checked. |
| `observer_status` | `ok` | `13.986` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1362.002` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.099` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `233.769` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `60609.593` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `407.458` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `82.64` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `3.143` | Response synthesized from stage evidence and runtime output. |
