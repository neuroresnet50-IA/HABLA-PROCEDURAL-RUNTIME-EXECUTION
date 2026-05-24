from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

EditorFileEntry = Dict[str, Any]
ListEditorFiles = Callable[[Path], List[EditorFileEntry]]
ResolveEditorFile = Callable[[Path, str], Optional[Tuple[str, Path]]]
NowProvider = Callable[[], str]
ManifestBuilder = Callable[..., Dict[str, Any]]
ManifestPersister = Callable[[Path, Dict[str, Any]], Path]


def build_code_scanner_report(
    project_slug: str,
    project_dir: Path,
    *,
    list_editor_files: ListEditorFiles,
    resolve_editor_file: ResolveEditorFile,
    report_name: str,
    checkpoint_name: str,
    now_provider: NowProvider,
) -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    blockers: List[str] = []
    scanned_bytes = 0
    scanned_characters = 0
    scanned_lines = 0

    for file_entry in list_editor_files(project_dir):
        relative_path = str(file_entry["path"])
        resolved_file = resolve_editor_file(project_dir, relative_path)
        if resolved_file is None:
            blockers.append(f"Archivo no resoluble: {relative_path}")
            continue
        _, file_path = resolved_file
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            blockers.append(f"Archivo binario o no UTF-8: {relative_path}")
            continue
        except OSError as error:
            blockers.append(f"No se pudo leer {relative_path}: {error}")
            continue

        line_count = len(content.splitlines()) if content else 0
        character_count = len(content)
        byte_count = len(content.encode("utf-8"))
        scanned_bytes += byte_count
        scanned_characters += character_count
        scanned_lines += line_count
        lines = content.splitlines()
        files.append(
            {
                **file_entry,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "lineCount": line_count,
                "characterCount": character_count,
                "byteCount": byte_count,
                "maxLineLength": max((len(line) for line in lines), default=0),
                "empty": character_count == 0,
            }
        )

    if not files:
        blockers.append("El scanner final no encontro archivos visibles para validar.")

    generated_at = now_provider()
    validation_passed = not blockers
    return {
        "schema_version": 1,
        "report_type": "final_code_scanner",
        "projectId": project_slug,
        "generatedAt": generated_at,
        "scanner": {
            "mode": "final-code-readthrough",
            "scope": "workspace_visible_source_files",
            "reads_every_utf8_character": True,
            "visual_playback": "magnifier_line_by_line_to_last_line",
            "scrolls_to_last_line": True,
        },
        "summary": {
            "filesScanned": len(files),
            "linesScanned": scanned_lines,
            "charactersScanned": scanned_characters,
            "bytesScanned": scanned_bytes,
        },
        "validation": {
            "passed": validation_passed,
            "blockers": blockers,
            "artifact": f"runtime/artifacts/{report_name}",
            "checkpoint": f"runtime/checkpoints/{checkpoint_name}",
        },
        "files": files,
    }


def persist_code_scanner_report(
    project_dir: Path,
    report: Dict[str, Any],
    *,
    report_name: str,
    checkpoint_name: str,
    build_agent_file_manifest: ManifestBuilder,
    persist_agent_file_manifest: ManifestPersister,
) -> Dict[str, str]:
    runtime_dir = project_dir / "runtime"
    artifacts_dir = runtime_dir / "artifacts"
    checkpoints_dir = runtime_dir / "checkpoints"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifacts_dir / report_name
    checkpoint_path = checkpoints_dir / checkpoint_name
    payload = json.dumps(report, ensure_ascii=True, indent=2)
    artifact_path.write_text(payload + "\n", encoding="utf-8")
    checkpoint_path.write_text(payload + "\n", encoding="utf-8")
    paths = {
        "artifactPath": str(artifact_path),
        "checkpointPath": str(checkpoint_path),
    }
    if bool((report.get("validation") or {}).get("passed")):
        manifest = build_agent_file_manifest(
            str(report.get("projectId") or ""),
            report,
            project_dir=project_dir,
            source="final_code_scanner",
        )
        manifest_path = persist_agent_file_manifest(project_dir, manifest)
        paths["manifestPath"] = str(manifest_path)
    return paths
