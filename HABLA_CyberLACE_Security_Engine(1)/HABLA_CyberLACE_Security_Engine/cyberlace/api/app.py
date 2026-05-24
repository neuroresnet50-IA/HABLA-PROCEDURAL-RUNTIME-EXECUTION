from fastapi import FastAPI
from cyberlace.core.engine import CyberLACEEngine
from cyberlace.api.schemas import (
    PromptGuardRequest,
    MemoryGuardRequest,
    ToolGuardRequest,
    OutputGuardRequest,
    ExternalActionRequest,
    GenericEventRequest,
)

engine = CyberLACEEngine.from_config("cyberlace_config.yaml")

app = FastAPI(
    title="HABLA CyberLACE Security Engine",
    description="REST API para seguridad cognitiva de harnesses IA",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "engine": "HABLA CyberLACE Security Engine", "mode": engine.mode}


@app.post("/v1/guard/prompt")
def guard_prompt(req: PromptGuardRequest):
    return engine.before_prompt(req.agent_id, req.user_id, req.prompt, req.context, req.session_id)


@app.post("/v1/guard/memory")
def guard_memory(req: MemoryGuardRequest):
    return engine.before_memory_read(req.agent_id, req.user_id, req.memory_text, req.task_context, req.session_id)


@app.post("/v1/guard/tool")
def guard_tool(req: ToolGuardRequest):
    return engine.before_tool_call(req.agent_id, req.user_id, req.tool_name, req.tool_args, req.task_context, req.session_id)


@app.post("/v1/guard/output")
def guard_output(req: OutputGuardRequest):
    return engine.after_model_output(req.agent_id, req.user_id, req.output, req.context, req.session_id)


@app.post("/v1/guard/external-action")
def guard_external_action(req: ExternalActionRequest):
    return engine.before_external_action(req.agent_id, req.user_id, req.action_type, req.payload, req.context, req.session_id)


@app.post("/v1/evaluate/event")
def evaluate_event(req: GenericEventRequest):
    return engine.evaluate_event(req.event)


@app.get("/v1/evidence/recent")
def recent_evidence(limit: int = 20):
    return {"items": engine.evidence.recent(limit)}
