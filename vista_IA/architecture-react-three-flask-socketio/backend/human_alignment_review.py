"""Human Alignment Review (HAR) protocol.

HAR is a post-build human preference gate. It records what was built, which
technical decisions were detected, and waits for human direction before any
code-changing alignment task is queued.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TECH_STACK_OPTIONS: dict[str, list[str]] = {
    "languages": [
        "Python", "JavaScript", "TypeScript", "C#", "Java", "Go", "Rust",
        "C++", "PHP", "Ruby", "Kotlin", "Swift", "Dart", "Scala", "Elixir",
    ],
    "databases": [
        "SQL Server", "PostgreSQL", "MySQL", "MariaDB", "SQLite",
        "MongoDB", "Redis", "Cassandra", "Elasticsearch", "Neo4j",
        "Oracle", "Firebase", "Supabase", "DynamoDB", "CockroachDB",
    ],
    "backend": [
        "Flask", "FastAPI", "Django", "Express.js", "NestJS",
        "Spring Boot", "ASP.NET Core", "Laravel", "Ruby on Rails",
        "Gin", "Echo", "Fiber", "Actix Web",
    ],
    "frontend": [
        "React", "Next.js", "Vue.js", "Nuxt.js", "Svelte", "SvelteKit",
        "Angular", "Solid.js", "Qwik", "Astro", "Remix",
    ],
    "visualization": [
        "Three.js", "React Three Fiber", "Babylon.js", "D3.js",
        "Chart.js", "Recharts", "ECharts", "Deck.gl", "Mapbox GL", "Leaflet",
    ],
    "realtime": [
        "Socket.IO", "WebSockets", "SignalR", "Pusher", "Ably",
        "Centrifugo", "Phoenix Channels",
    ],
    "mobile": [
        "React Native", "Flutter", "SwiftUI", "Kotlin Multiplatform",
        "Ionic", "Expo", "Tauri",
    ],
    "devops": [
        "Docker", "Kubernetes", "AWS", "Azure", "Google Cloud",
        "Terraform", "CI/CD", "GitHub Actions", "Jenkins", "Nginx", "Traefik",
    ],
    "ai_ml": [
        "LangChain", "LlamaIndex", "OpenAI", "Anthropic", "Groq",
        "TensorFlow", "PyTorch", "Hugging Face", "Ollama", "CrewAI",
    ],
    "libraries": [
        "Tailwind CSS", "Bootstrap", "Shadcn/ui", "Redux", "Zustand",
        "Prisma", "SQLAlchemy", "Mongoose", "Pandas", "NumPy",
        "Pydantic", "Celery", "RabbitMQ", "Kafka",
    ],
    "embedded": [
        "Arduino", "ESP32", "Raspberry Pi", "ROS", "FreeRTOS", "MicroPython",
    ],
    "testing": [
        "Pytest", "Jest", "Cypress", "Playwright", "Selenium",
        "Postman", "JMeter",
    ],
    "others": [
        "Electron", "Tauri", "Blender", "Unity", "Unreal Engine",
        "Godot", "FFmpeg", "OpenCV", "gRPC", "GraphQL", "Apollo",
    ],
}


HAR_STATUS_WAITING = "waiting_for_human"
HAR_STATUS_TASKS_READY = "alignment_tasks_ready"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def har_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_review_id(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return f"HUMAN_ALIGNMENT_REVIEW-{har_timestamp()}"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-")
    return safe or f"HUMAN_ALIGNMENT_REVIEW-{har_timestamp()}"


def list_human_alignment_reviews(runtime_dir: str | Path) -> list[dict[str, Any]]:
    index_path = _har_index_path(Path(runtime_dir))
    if not index_path.exists():
        return []
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    reviews = payload.get("reviews") if isinstance(payload, dict) else None
    if not isinstance(reviews, list):
        return []
    return [review for review in reviews if isinstance(review, dict)]


def get_latest_human_alignment_review(runtime_dir: str | Path) -> dict[str, Any] | None:
    reviews = list_human_alignment_reviews(runtime_dir)
    return reviews[-1] if reviews else None


def get_human_alignment_review(runtime_dir: str | Path, review_id: str) -> dict[str, Any] | None:
    normalized_id = normalize_review_id(review_id)
    for review in list_human_alignment_reviews(runtime_dir):
        if review.get("id") == normalized_id:
            return review
    return None


def create_human_alignment_review(
    *,
    project_root: str | Path,
    runtime_dir: str | Path | None = None,
    source: str = "automatic",
    trigger: str = "project_completed",
    reason: str = "",
    task_id: str = "",
    session_id: str = "",
    dedupe: bool = True,
) -> dict[str, Any]:
    project = Path(project_root).resolve()
    runtime = Path(runtime_dir or project / "runtime").resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    summary = build_human_alignment_summary(project, runtime)
    fingerprint = _review_fingerprint(summary, trigger=trigger, task_id=task_id)

    if dedupe:
        for existing in reversed(list_human_alignment_reviews(runtime)):
            if existing.get("fingerprint") == fingerprint and existing.get("status") in {
                HAR_STATUS_WAITING,
                HAR_STATUS_TASKS_READY,
            }:
                return {"created": False, "review": existing, "techStackOptions": TECH_STACK_OPTIONS}

    review_id = normalize_review_id(f"HUMAN_ALIGNMENT_REVIEW-{har_timestamp()}")
    review = {
        "schema_version": 1,
        "id": review_id,
        "type": "HUMAN_ALIGNMENT_REVIEW",
        "status": HAR_STATUS_WAITING,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source": source,
        "trigger": trigger,
        "reason": reason or "Proyecto completado; esperando alineacion humana.",
        "task_id": task_id,
        "session_id": session_id,
        "project_id": summary.get("project_id"),
        "fingerprint": fingerprint,
        "summary": summary,
        "requested_changes": [],
        "alignment_tasks": [],
        "human_feedback": "",
        "selected_stack_preferences": {},
        "instructions": [
            "No tocar codigo automaticamente durante HAR.",
            "Esperar cambios o preferencias humanas.",
            "Convertir feedback humano en tareas prioritarias y auditables.",
        ],
    }
    review["markdown_path"] = str(_write_har_markdown(runtime, review))
    _upsert_review(runtime, review)
    _append_jsonl(runtime / "task_history.jsonl", _har_history_event(review, "HAR_CREATED"))
    _append_jsonl(_har_events_path(runtime), {"recorded_at": utc_now(), "event": "HAR_CREATED", "review": review})
    return {"created": True, "review": review, "techStackOptions": TECH_STACK_OPTIONS}


def submit_human_alignment_feedback(
    *,
    project_root: str | Path,
    runtime_dir: str | Path | None = None,
    review_id: str,
    feedback: str,
    requested_changes: Iterable[Any] | None = None,
    selected_stack_preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project = Path(project_root).resolve()
    runtime = Path(runtime_dir or project / "runtime").resolve()
    review = get_human_alignment_review(runtime, review_id)
    if review is None:
        raise ValueError("human_alignment_review_not_found")

    changes = _normalize_requested_changes(requested_changes, fallback=feedback)
    preferences = selected_stack_preferences if isinstance(selected_stack_preferences, dict) else {}
    tasks = build_alignment_tasks(review, changes, preferences)
    _enqueue_alignment_tasks(runtime, tasks)

    review = dict(review)
    review["status"] = HAR_STATUS_TASKS_READY
    review["updated_at"] = utc_now()
    review["human_feedback"] = str(feedback or "").strip()
    review["requested_changes"] = changes
    review["selected_stack_preferences"] = preferences
    review["alignment_tasks"] = tasks
    review["markdown_path"] = str(_write_har_markdown(runtime, review))
    _upsert_review(runtime, review)
    _append_jsonl(runtime / "task_history.jsonl", _har_history_event(review, "HAR_FEEDBACK_SUBMITTED"))
    _append_jsonl(_har_events_path(runtime), {"recorded_at": utc_now(), "event": "HAR_FEEDBACK_SUBMITTED", "review": review})
    _mark_project_alignment_pending(runtime, tasks)
    return {"review": review, "tasks": tasks, "techStackOptions": TECH_STACK_OPTIONS}


def build_human_alignment_summary(project_root: str | Path, runtime_dir: str | Path) -> dict[str, Any]:
    project = Path(project_root).resolve()
    runtime = Path(runtime_dir).resolve()
    project_state = _read_json(runtime / "project_state.json", default={})
    task_queue = _read_json(runtime / "task_queue.json", default=[])
    history = _read_jsonl(runtime / "task_history.jsonl")
    material_files = _material_files(project, task_queue)
    latest_results = [
        event.get("result")
        for event in history[-10:]
        if isinstance(event, dict) and isinstance(event.get("result"), dict)
    ]
    return {
        "project_id": _project_id(project, project_state),
        "project_root": str(project),
        "runtime_dir": str(runtime),
        "project_status": project_state.get("status") if isinstance(project_state, dict) else None,
        "current_task_id": project_state.get("current_task_id") if isinstance(project_state, dict) else None,
        "task_counts": _task_counts(task_queue),
        "completed_tasks": [
            task.get("id")
            for task in task_queue
            if isinstance(task, dict) and task.get("status") == "completed"
        ],
        "latest_task_results": latest_results,
        "material_files": material_files,
        "detected_stack": detect_tech_stack(project),
        "architecture_decisions": infer_architecture_decisions(project, material_files),
    }


def detect_tech_stack(project_root: str | Path) -> dict[str, list[str]]:
    project = Path(project_root)
    text_samples = _read_small_project_text(project)
    file_suffixes = {path.suffix.lower() for path in project.rglob("*") if path.is_file()}
    detected: dict[str, set[str]] = {key: set() for key in TECH_STACK_OPTIONS}

    if ".py" in file_suffixes:
        detected["languages"].add("Python")
    if file_suffixes & {".js", ".jsx"}:
        detected["languages"].add("JavaScript")
    if file_suffixes & {".ts", ".tsx"}:
        detected["languages"].add("TypeScript")
    if any(path.suffix.lower() in {".sqlite", ".sqlite3", ".db"} for path in project.rglob("*") if path.is_file()):
        detected["databases"].add("SQLite")

    joined = "\n".join(text_samples).lower()
    pattern_map = {
        "frontend": {
            "React": ("react", "jsx"),
            "Next.js": ("next/", "next.config"),
            "Vue.js": ("vue",),
            "Svelte": ("svelte",),
            "Angular": ("@angular",),
        },
        "visualization": {
            "Three.js": ("three", "three.js", "webgl"),
            "Babylon.js": ("babylon",),
            "D3.js": ("d3",),
            "Chart.js": ("chart.js",),
        },
        "backend": {
            "Flask": ("from flask", "import flask"),
            "FastAPI": ("fastapi",),
            "Django": ("django",),
            "Express.js": ("express",),
            "NestJS": ("nestjs",),
            "ASP.NET Core": ("asp.net",),
        },
        "realtime": {
            "Socket.IO": ("socket.io",),
            "WebSockets": ("websocket", "websockets"),
            "SignalR": ("signalr",),
        },
        "libraries": {
            "Tailwind CSS": ("tailwind",),
            "Bootstrap": ("bootstrap",),
            "Redux": ("redux",),
            "Zustand": ("zustand",),
            "SQLAlchemy": ("sqlalchemy",),
            "Pandas": ("pandas",),
            "NumPy": ("numpy",),
        },
        "testing": {
            "Pytest": ("pytest",),
            "Jest": ("jest",),
            "Playwright": ("playwright",),
            "Selenium": ("selenium",),
        },
        "ai_ml": {
            "OpenAI": ("openai",),
            "TensorFlow": ("tensorflow",),
            "PyTorch": ("torch", "pytorch"),
            "Hugging Face": ("huggingface", "transformers"),
            "Ollama": ("ollama",),
        },
    }
    for category, tools in pattern_map.items():
        for name, markers in tools.items():
            if any(marker.lower() in joined for marker in markers):
                detected[category].add(name)

    return {key: sorted(values) for key, values in detected.items() if values}


def infer_architecture_decisions(project_root: str | Path, material_files: list[dict[str, Any]]) -> list[str]:
    project = Path(project_root)
    decisions: list[str] = []
    if (project / "frontend" / "index.html").exists():
        decisions.append("Aplicacion frontend estatica con entrada HTML.")
    if (project / "frontend" / "app.js").exists():
        app_text = _read_text(project / "frontend" / "app.js")
        if "three" in app_text.lower():
            decisions.append("Visualizacion 3D implementada con Three.js/WebGL.")
        if "qtable" in app_text.lower() or "reward" in app_text.lower() or "dqn" in app_text.lower():
            decisions.append("Agente autonomo con telemetria de recompensa/castigo en navegador.")
    if any(item.get("path", "").startswith("backend/") for item in material_files):
        decisions.append("Backend dedicado detectado en el proyecto.")
    if not decisions:
        decisions.append("Decisiones principales pendientes de clasificacion humana.")
    return decisions


def build_alignment_tasks(
    review: dict[str, Any],
    requested_changes: list[str],
    selected_stack_preferences: dict[str, Any],
) -> list[dict[str, Any]]:
    review_id = normalize_review_id(review.get("id"))
    summary = review.get("summary") if isinstance(review.get("summary"), dict) else {}
    existing_files = [
        item.get("path")
        for item in summary.get("material_files", [])
        if isinstance(item, dict) and item.get("exists") and item.get("path")
    ]
    expected_files = existing_files[:8] or ["README.md"]
    if "README.md" not in expected_files and any(path == "README.md" for path in existing_files):
        expected_files.append("README.md")

    change_text = "\n".join(f"- {change}" for change in requested_changes) or "- Revisar preferencias humanas."
    stack_text = json.dumps(selected_stack_preferences, ensure_ascii=False, indent=2)
    task_id = f"{review_id}-001"
    return [
        {
            "id": task_id,
            "title": "Aplicar ajustes de alineacion humana",
            "goal": (
                "Aplicar de forma controlada los cambios solicitados por el humano despues del cierre tecnico.\n"
                f"Cambios solicitados:\n{change_text}\n"
                f"Preferencias de stack seleccionadas:\n{stack_text}"
            ),
            "status": "pending",
            "priority": 100,
            "dependencies": [],
            "expected_files": expected_files,
            "validation_commands": [_expected_files_command(expected_files)],
            "timeout_seconds": 900,
            "max_retries": 3,
            "mode": "build",
            "checkpoint_key": f"{task_id.lower()}-checkpoint",
        }
    ]


def _normalize_requested_changes(value: Iterable[Any] | None, *, fallback: str = "") -> list[str]:
    changes: list[str] = []
    for item in value or []:
        text = str(item or "").strip()
        if text:
            changes.append(text)
    fallback_text = str(fallback or "").strip()
    if fallback_text and not changes:
        changes = [line.strip("- ").strip() for line in fallback_text.splitlines() if line.strip("- ").strip()]
    return changes or ["Revisar y ajustar el proyecto segun preferencia humana."]


def _expected_files_command(expected_files: list[str]) -> str:
    return (
        "python3 -B -c "
        + repr(
            "from pathlib import Path; "
            f"missing=[p for p in {expected_files!r} if not Path(p).is_file()]; "
            "assert not missing, missing"
        )
    )


def _enqueue_alignment_tasks(runtime: Path, tasks: list[dict[str, Any]]) -> None:
    queue_path = runtime / "task_queue.json"
    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8")) if queue_path.exists() else []
        if not isinstance(queue, list):
            queue = []
    except Exception:
        queue = []
    existing_ids = {item.get("id") for item in queue if isinstance(item, dict)}
    for task in tasks:
        if task.get("id") not in existing_ids:
            queue.append(task)
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def _mark_project_alignment_pending(runtime: Path, tasks: list[dict[str, Any]]) -> None:
    state_path = runtime / "project_state.json"
    state = _read_json(state_path, default={})
    if not isinstance(state, dict):
        return
    state["status"] = "human_alignment_pending"
    state["current_task_id"] = None
    state["pending_human_alignment_tasks"] = [task.get("id") for task in tasks]
    state["updated_at"] = utc_now()
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _project_id(project: Path, state: Any) -> str:
    if isinstance(state, dict) and state.get("project_id"):
        return str(state["project_id"])
    return project.name


def _task_counts(task_queue: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not isinstance(task_queue, list):
        return counts
    for task in task_queue:
        if not isinstance(task, dict):
            continue
        status = str(task.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _material_files(project: Path, task_queue: Any) -> list[dict[str, Any]]:
    expected: list[str] = []
    if isinstance(task_queue, list):
        for task in task_queue:
            if not isinstance(task, dict):
                continue
            for relative in task.get("expected_files", []) or []:
                text = str(relative or "").strip()
                if text and text not in expected:
                    expected.append(text)
    if not expected:
        expected = [
            str(path.relative_to(project))
            for path in project.rglob("*")
            if path.is_file() and not _is_runtime_or_generated(path)
        ][:20]
    records = []
    for relative in expected:
        path = project / relative
        records.append(
            {
                "path": relative,
                "exists": path.is_file(),
                "size": path.stat().st_size if path.is_file() else None,
            }
        )
    return records


def _is_runtime_or_generated(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & {"runtime", "__pycache__", "node_modules", "dist", "build"})


def _read_small_project_text(project: Path) -> list[str]:
    samples: list[str] = []
    for path in sorted(project.rglob("*")):
        if not path.is_file() or _is_runtime_or_generated(path):
            continue
        if path.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".md"}:
            continue
        text = _read_text(path, limit=25_000)
        if text:
            samples.append(text)
        if len(samples) >= 40:
            break
    return samples


def _read_text(path: Path, *, limit: int = 120_000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except Exception:
        return ""


def _read_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _har_root(runtime: Path) -> Path:
    return runtime / "human_alignment_reviews"


def _har_index_path(runtime: Path) -> Path:
    return _har_root(runtime) / "index.json"


def _har_events_path(runtime: Path) -> Path:
    return _har_root(runtime) / "events.jsonl"


def _review_fingerprint(summary: dict[str, Any], *, trigger: str, task_id: str) -> str:
    return "|".join(
        [
            str(summary.get("project_id") or ""),
            str(summary.get("project_status") or ""),
            str(summary.get("task_counts") or {}),
            str((summary.get("completed_tasks") or [])[-3:]),
            trigger,
            task_id,
        ]
    )


def _upsert_review(runtime: Path, review: dict[str, Any]) -> None:
    root = _har_root(runtime)
    root.mkdir(parents=True, exist_ok=True)
    reviews = list_human_alignment_reviews(runtime)
    reviews = [item for item in reviews if item.get("id") != review.get("id")]
    reviews.append(review)
    _har_index_path(runtime).write_text(
        json.dumps({"schema_version": 1, "reviews": reviews}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / f"{review['id']}.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_har_markdown(runtime: Path, review: dict[str, Any]) -> Path:
    root = _har_root(runtime)
    root.mkdir(parents=True, exist_ok=True)
    summary = review.get("summary") if isinstance(review.get("summary"), dict) else {}
    detected_stack = summary.get("detected_stack") if isinstance(summary.get("detected_stack"), dict) else {}
    decisions = summary.get("architecture_decisions") if isinstance(summary.get("architecture_decisions"), list) else []
    requested = review.get("requested_changes") if isinstance(review.get("requested_changes"), list) else []
    tasks = review.get("alignment_tasks") if isinstance(review.get("alignment_tasks"), list) else []
    path = root / f"{review['id']}.md"
    path.write_text(
        "\n".join(
            [
                f"# {review['id']}",
                "",
                f"Estado HAR: {review.get('status')}",
                f"Proyecto: {summary.get('project_id')}",
                f"Disparador: {review.get('trigger')}",
                f"Motivo: {review.get('reason')}",
                "",
                "## Resumen de construccion",
                f"- Estado del proyecto: {summary.get('project_status')}",
                f"- Tareas: {json.dumps(summary.get('task_counts') or {}, ensure_ascii=False)}",
                f"- Archivos materiales: {', '.join(item.get('path') for item in summary.get('material_files', []) if isinstance(item, dict) and item.get('exists')) or 'sin evidencia'}",
                "",
                "## Decisiones detectadas",
                *(f"- {decision}" for decision in decisions),
                "",
                "## Stack detectado",
                *(f"- {category}: {', '.join(values)}" for category, values in detected_stack.items()),
                "",
                "## Feedback humano",
                *(f"- {change}" for change in requested),
                "",
                "## Tareas de alineacion",
                *(f"- {task.get('id')}: {task.get('title')}" for task in tasks),
                "",
                "Regla: HAR no toca codigo automaticamente; solo prepara tareas despues de feedback humano.",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _har_history_event(review: dict[str, Any], event_type: str) -> dict[str, Any]:
    return {
        "recorded_at": utc_now(),
        "human_alignment_review": {
            "event_type": event_type,
            "review_id": review.get("id"),
            "status": review.get("status"),
            "project_id": review.get("project_id"),
            "task_ids": [task.get("id") for task in review.get("alignment_tasks", []) if isinstance(task, dict)],
        },
    }
