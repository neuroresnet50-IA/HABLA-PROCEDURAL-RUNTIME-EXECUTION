from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_relative_path(value: str) -> str:
    normalized = str(PurePosixPath(os.path.normpath(value or "."))).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    while normalized.startswith("../"):
        normalized = normalized[3:]
    return normalized.lstrip("/")


def normalize_source_path(value: str) -> str:
    raw_value = str(value or ".")
    path = Path(raw_value)
    if path.is_absolute():
        return path.as_posix()
    return normalize_relative_path(raw_value)


def resolve_context() -> Dict[str, str]:
    project_dir = Path(os.environ.get("VISTA_AGENT_PROJECT_DIR") or os.getcwd()).resolve()
    project_slug = os.environ.get("VISTA_AGENT_PROJECT_SLUG") or project_dir.name
    session_id = os.environ.get("VISTA_AGENT_SESSION_ID") or "agent-manual"
    event_file = Path(os.environ.get("VISTA_AGENT_EVENT_FILE") or project_dir / ".vista" / f"{session_id}.jsonl")
    return {
        "projectDir": str(project_dir),
        "projectSlug": project_slug,
        "sessionId": session_id,
        "eventFile": str(event_file),
    }


def append_event(payload: Dict[str, Any]) -> None:
    context = resolve_context()
    event_file = Path(context["eventFile"])
    event_file.parent.mkdir(parents=True, exist_ok=True)

    final_payload = {
        "sessionId": context["sessionId"],
        "projectSlug": context["projectSlug"],
        "projectDir": context["projectDir"],
        "timestamp": utc_now(),
        **payload,
    }

    with event_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(final_payload, ensure_ascii=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge visual para el editor agentico.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    phase_parser = subparsers.add_parser("phase")
    phase_parser.add_argument("--label", required=True)
    phase_parser.add_argument("--message", required=True)

    node_parser = subparsers.add_parser("upsert-node")
    node_parser.add_argument("--path", required=True)
    node_parser.add_argument("--name")
    node_parser.add_argument("--layer")
    node_parser.add_argument("--layer-label")
    node_parser.add_argument("--language")
    node_parser.add_argument("--description")
    node_parser.add_argument("--status")
    node_parser.add_argument("--color")
    node_parser.add_argument("--x", type=float)
    node_parser.add_argument("--y", type=float)

    edge_parser = subparsers.add_parser("connect-nodes")
    edge_parser.add_argument("--from-path", required=True)
    edge_parser.add_argument("--to-path", required=True)
    edge_parser.add_argument("--type", default="uses")
    edge_parser.add_argument("--label", default="")

    focus_parser = subparsers.add_parser("focus-node")
    focus_parser.add_argument("--path", required=True)

    step_parser = subparsers.add_parser("upsert-step")
    step_parser.add_argument("--node-path", required=True)
    step_parser.add_argument("--step-id", required=True)
    step_parser.add_argument("--type", required=True)
    step_parser.add_argument("--label", required=True)
    step_parser.add_argument("--x", type=float)
    step_parser.add_argument("--y", type=float)
    step_parser.add_argument("--color")
    step_parser.add_argument("--code-file")

    flow_edge_parser = subparsers.add_parser("connect-steps")
    flow_edge_parser.add_argument("--node-path", required=True)
    flow_edge_parser.add_argument("--from-step", required=True)
    flow_edge_parser.add_argument("--to-step", required=True)
    flow_edge_parser.add_argument("--label", default="")

    sync_parser = subparsers.add_parser("sync-file")
    sync_parser.add_argument("--path", required=True)
    sync_parser.add_argument("--source-path")
    sync_parser.add_argument("--name")
    sync_parser.add_argument("--layer")
    sync_parser.add_argument("--layer-label")
    sync_parser.add_argument("--language")
    sync_parser.add_argument("--description")
    sync_parser.add_argument("--status")
    sync_parser.add_argument("--color")
    sync_parser.add_argument("--x", type=float)
    sync_parser.add_argument("--y", type=float)

    return parser


def load_code_text(project_dir: Path, maybe_path: str | None) -> str:
    if not maybe_path:
        return ""
    source_path = (project_dir / maybe_path).resolve()
    if not source_path.exists() or not source_path.is_file():
        return ""
    try:
        return source_path.read_text(encoding="utf-8")
    except OSError:
        return ""


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    context = resolve_context()
    project_dir = Path(context["projectDir"])

    if args.command == "phase":
        append_event(
            {
                "op": "phase",
                "phase": str(args.label),
                "message": str(args.message),
            }
        )
        return 0

    if args.command == "upsert-node":
        payload: Dict[str, Any] = {
            "op": "upsert_node",
            "relativePath": normalize_relative_path(args.path),
        }
        if args.name:
            payload["name"] = str(args.name)
        if args.layer:
            payload["layer"] = str(args.layer)
        if args.layer_label:
            payload["layerLabel"] = str(args.layer_label)
        if args.language:
            payload["codeLanguage"] = str(args.language)
        if args.description:
            payload["description"] = str(args.description)
        if args.status:
            payload["status"] = str(args.status)
        if args.color:
            payload["color"] = str(args.color)
        if args.x is not None and args.y is not None:
            payload["position"] = {"x": float(args.x), "y": float(args.y)}
        append_event(payload)
        return 0

    if args.command == "connect-nodes":
        append_event(
            {
                "op": "upsert_edge",
                "fromPath": normalize_relative_path(args.from_path),
                "toPath": normalize_relative_path(args.to_path),
                "edgeType": str(args.type),
                "label": str(args.label or ""),
            }
        )
        return 0

    if args.command == "focus-node":
        append_event(
            {
                "op": "focus_node",
                "relativePath": normalize_relative_path(args.path),
            }
        )
        return 0

    if args.command == "upsert-step":
        payload = {
            "op": "upsert_flow_step",
            "nodePath": normalize_relative_path(args.node_path),
            "step": {
                "id": str(args.step_id),
                "type": str(args.type),
                "label": str(args.label),
            },
        }
        if args.x is not None and args.y is not None:
            payload["step"]["x"] = float(args.x)
            payload["step"]["y"] = float(args.y)
        if args.color:
            payload["step"]["color"] = str(args.color)
        if args.code_file:
            payload["step"]["code"] = load_code_text(project_dir, normalize_relative_path(args.code_file))
        append_event(payload)
        return 0

    if args.command == "connect-steps":
        append_event(
            {
                "op": "upsert_flow_edge",
                "nodePath": normalize_relative_path(args.node_path),
                "fromStep": str(args.from_step),
                "toStep": str(args.to_step),
                "label": str(args.label or ""),
            }
        )
        return 0

    if args.command == "sync-file":
        payload = {
            "op": "sync_file",
            "relativePath": normalize_relative_path(args.path),
            "sourcePath": normalize_source_path(args.source_path or args.path),
        }
        if args.name:
            payload["name"] = str(args.name)
        if args.layer:
            payload["layer"] = str(args.layer)
        if args.layer_label:
            payload["layerLabel"] = str(args.layer_label)
        if args.language:
            payload["codeLanguage"] = str(args.language)
        if args.description:
            payload["description"] = str(args.description)
        if args.status:
            payload["status"] = str(args.status)
        if args.color:
            payload["color"] = str(args.color)
        if args.x is not None and args.y is not None:
            payload["position"] = {"x": float(args.x), "y": float(args.y)}
        append_event(payload)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
