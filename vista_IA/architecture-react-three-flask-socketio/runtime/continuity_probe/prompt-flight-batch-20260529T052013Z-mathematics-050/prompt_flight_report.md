# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-050

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-050`
- durationSeconds: `85.273809`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.039` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `6.447` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `27.218` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `7.288` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `10.938` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `9.114` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.927` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `22.184` | Backend health checked. |
| `observer_status` | `ok` | `16.159` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `916.383` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `5.105` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `593.437` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `82888.672` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `498.993` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `52.585` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `8.356` | Response synthesized from stage evidence and runtime output. |
