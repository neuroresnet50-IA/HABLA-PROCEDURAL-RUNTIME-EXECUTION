# Prompt Flight Report - prompt-flight-batch-20260529T050016Z-mixed-sci-prog-005

- result: `prompt_flight_ok`
- mode: `ui_session_rest`
- project: `continuity-mixed-pf-005`
- durationSeconds: `226.331311`

| Stage | Status | Latency ms | Message |
| --- | --- | ---: | --- |
| `prompt_received` | `ok` | `4.15` | Prompt persisted with trace hash. |
| `habla_basic_envelope` | `ok` | `28.633` | HABLA BASIC envelope persisted. |
| `cyberlace_preflight` | `ok` | `168.927` | CyberLACE preflight allowed diagnostic processing. |
| `policy_loaded` | `ok` | `14.536` | AGENTS.md policy loaded. |
| `plan_loaded` | `ok` | `17.41` | PLANS.md roadmap loaded. |
| `prompt_classified` | `ok` | `88.362` | Prompt classified for diagnostic routing. |
| `task_planned` | `ok` | `29.118` | UI REST session payload planned; execution goes through /api/agent/session. |
| `backend_health` | `ok` | `126.85` | Backend health checked. |
| `observer_status` | `ok` | `64.491` | Observer status checked without starting a mission. |
| `harness_summary` | `ok` | `1930.736` | Harness and Safety Learning checked. |
| `safe_canary_continuity` | `skipped` | `0.0` | Skipped because mode is ui_session_rest; runtime session follows. |
| `ui_rest_payload_built` | `ok` | `9.867` | Exact AgentStudio REST payload persisted for /api/agent/session. |
| `ui_agent_session_posted` | `ok` | `139.166` | Real UI session accepted by /api/agent/session. |
| `ui_agent_session_polled` | `ok` | `222820.544` | Real UI session reached terminal status: completed. |
| `ui_runtime_truth_read` | `ok` | `58.349` | runtime-truth read after real UI session. |
| `ui_runtime_artifacts_read` | `ok` | `41.689` | Runtime artifacts sampled from the real UI session project. |
| `response_synthesized` | `ok` | `4.137` | Response synthesized from stage evidence and runtime output. |
