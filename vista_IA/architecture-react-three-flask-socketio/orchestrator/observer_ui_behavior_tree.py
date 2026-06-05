from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node(node_id: str, label: str, selector: str = "", expected: str = "", timeout_ms: int = 2200) -> Dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "status": "pending",
        "selector": selector,
        "expected": expected,
        "timeoutMs": timeout_ms,
    }


def build_observer_ui_behavior_tree(action: Dict[str, Any]) -> Dict[str, Any]:
    """Build the Observer-governed UI behavior tree for an operational mouse action.

    The frontend executes these nodes visually and reports per-node evidence. The
    Observer/control plane owns the intended sequence so UI action execution does
    not depend on ad-hoc frontend timing.
    """
    target_tool = str(action.get("targetTool") or "").replace("-", "_")
    action_id = str(action.get("actionId") or "")
    project_slug = str(action.get("projectSlug") or "")
    auto_run = action.get("autoRun") is not False
    tool_selector = f'[data-operational-tool="{target_tool}"]'
    modal_selector = f'[data-operational-modal-tool="{target_tool}"]'
    run_selector = f'[data-operational-run-button="{target_tool}"]'
    minimize_selector = f'[data-operational-minimize-button="{target_tool}"]'
    minimized_selector = f'[data-operational-minimized-tool="{target_tool}"]'
    minimized_close_selector = f'[data-operational-minimized-close="{target_tool}"]'
    nodes: List[Dict[str, Any]] = [
        _node("select_project", "Seleccionar proyecto de accion", expected=project_slug),
        _node("find_tool_button", "Encontrar boton real de herramienta", tool_selector, "button exists and is clickable"),
        _node("focus_tool_button", "Posicionar cursor sobre recuadro real", tool_selector, "elementFromPoint hits target"),
        _node("click_tool_button", "Click real en boton de herramienta", tool_selector, "React dock handler confirms click"),
        _node("wait_tool_modal", "Esperar modal real de herramienta", modal_selector, "modal mounted", 3200),
    ]
    if auto_run:
        nodes.extend([
            _node("find_execute_button", "Encontrar boton interno de ejecucion", run_selector, "button exists and is clickable", 4200),
            _node("focus_execute_button", "Posicionar cursor sobre boton interno", run_selector, "elementFromPoint hits run button"),
            _node("click_execute_button", "Click real en boton interno", run_selector, "React run handler confirms click"),
            _node("find_minimize_button", "Encontrar boton de minimizar", minimize_selector, "button exists and is clickable"),
            _node("focus_minimize_button", "Posicionar cursor sobre minimizar", minimize_selector, "elementFromPoint hits minimize button"),
            _node("click_minimize_modal", "Minimizar modal mientras la herramienta trabaja", minimize_selector, "React minimize handler confirms click"),
            _node("wait_minimized_tray", "Confirmar tarjeta recogida inferior", minimized_selector, "minimized task card mounted", 3200),
            _node("wait_tool_result", "Esperar resultado real de herramienta", minimized_selector, "toolResult status becomes completed, blocked, or failed", 12000),
            _node("close_completed_modal", "Cerrar tarjeta si termino correctamente", minimized_close_selector, "only when result status is completed", 3600),
        ])
    else:
        nodes.append(_node("stop_after_modal", "Detenerse con modal abierto", modal_selector, "autoRun false"))
    return {
        "schemaVersion": 1,
        "treeId": f"BT-{action_id}" if action_id else f"BT-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "kind": "observer_ui_action_tree",
        "status": "pending",
        "createdAt": utc_now(),
        "source": str(action.get("source") or "observer_plane"),
        "actionId": action_id,
        "projectSlug": project_slug,
        "targetTool": target_tool,
        "autoRun": auto_run,
        "reason": str(action.get("reason") or "runtime_requested_tool"),
        "root": {
            "type": "sequence",
            "policy": "fail_fast",
            "nodes": nodes,
        },
        "invariants": [
            "No node may be marked success without DOM or runtime evidence.",
            "If any node fails, the UI action result must be blocked.",
            "The frontend executes clicks; the Observer plane owns the plan.",
        ],
    }


def persist_observer_ui_behavior_tree(observer_root: Path, tree: Dict[str, Any]) -> str:
    root = Path(observer_root) / "ui_behavior_trees"
    root.mkdir(parents=True, exist_ok=True)
    tree_id = str(tree.get("treeId") or f"BT-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}")
    safe_tree_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in tree_id)
    path = root / f"{safe_tree_id}.json"
    path.write_text(json.dumps(tree, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path)
