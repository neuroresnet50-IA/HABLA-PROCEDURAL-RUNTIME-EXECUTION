# Prompt Flight Report - prompt-flight-batch-20260529T052013Z-mathematics-030

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-math-pf-030`
- durationSeconds: `255.202644`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `8.463` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `5.804` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `32.505` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `5.945` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `22.296` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `10.843` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `3.406` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `34.857` | Backend health checked. |
| `observer_status` | `ok` | `10.078` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `2201.23` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `7.801` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `386.22` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `251537.863` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `497.623` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `117.806` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `14.9` | Response synthesized from stage evidence and runtime output. |
