from __future__ import annotations

import difflib
import hashlib
import hmac
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List


class IntegrityService:
    def __init__(
        self,
        *,
        baseline_anchor_root: Path,
        agent_file_manifest_name: str,
        agent_file_manifest_seal_name: str,
        agent_baseline_seal_ledger_name: str,
        file_integrity_report_name: str,
        observer_findings_report_name: str,
        frozen_sniper_report_name: str,
        file_write_ledger_name: str,
        list_editor_files: Callable[[Path], List[Dict[str, Any]]],
        resolve_editor_file: Callable[..., tuple[str, Path] | None],
        load_json_file: Callable[[Path, Any], Any],
        normalize_relative_fragment: Callable[[Any], str],
        normalize_project_id: Callable[[Any], str],
        now_provider: Callable[[], str],
    ) -> None:
        self.baseline_anchor_root = baseline_anchor_root
        self.agent_file_manifest_name = agent_file_manifest_name
        self.agent_file_manifest_seal_name = agent_file_manifest_seal_name
        self.agent_baseline_seal_ledger_name = agent_baseline_seal_ledger_name
        self.file_integrity_report_name = file_integrity_report_name
        self.observer_findings_report_name = observer_findings_report_name
        self.frozen_sniper_report_name = frozen_sniper_report_name
        self.file_write_ledger_name = file_write_ledger_name
        self.list_editor_files = list_editor_files
        self.resolve_editor_file = resolve_editor_file
        self.load_json_file = load_json_file
        self.normalize_relative_fragment = normalize_relative_fragment
        self.normalize_project_id = normalize_project_id
        self.now = now_provider

    def artifacts_dir(self, project_dir: Path) -> Path:
        return project_dir / "runtime" / "artifacts"

    def agent_file_manifest_path(self, project_dir: Path) -> Path:
        return self.artifacts_dir(project_dir) / self.agent_file_manifest_name

    def agent_file_manifest_seal_path(self, project_dir: Path) -> Path:
        return self.artifacts_dir(project_dir) / self.agent_file_manifest_seal_name

    def baseline_vault_root(self, project_dir: Path) -> Path:
        return project_dir / "runtime" / "baseline_vault"

    def baseline_seal_ledger_path(self, project_dir: Path) -> Path:
        return self.baseline_vault_root(project_dir) / self.agent_baseline_seal_ledger_name

    def baseline_vault_manifest_path(self, project_dir: Path, manifest_sha256: str) -> Path:
        safe_hash = re.sub(r"[^a-fA-F0-9]", "", str(manifest_sha256 or ""))[:64]
        if len(safe_hash) != 64:
            safe_hash = hashlib.sha256(str(manifest_sha256 or "").encode("utf-8")).hexdigest()
        return self.baseline_vault_root(project_dir) / safe_hash / self.agent_file_manifest_name

    def baseline_external_anchor_dir(self, project_id: str) -> Path:
        slug = self.normalize_project_id(project_id or "unknown-project")
        return self.baseline_anchor_root / slug

    def baseline_external_anchor_path(self, project_id: str) -> Path:
        return self.baseline_external_anchor_dir(project_id) / "latest_anchor.json"

    def baseline_external_anchor_ledger_path(self, project_id: str) -> Path:
        return self.baseline_external_anchor_dir(project_id) / "anchors.jsonl"

    def file_integrity_report_path(self, project_dir: Path) -> Path:
        return self.artifacts_dir(project_dir) / self.file_integrity_report_name

    def observer_findings_report_path(self, project_dir: Path) -> Path:
        return self.artifacts_dir(project_dir) / self.observer_findings_report_name

    def frozen_sniper_report_path(self, project_dir: Path) -> Path:
        return self.artifacts_dir(project_dir) / self.frozen_sniper_report_name

    def frozen_sniper_root(self, project_dir: Path) -> Path:
        return project_dir / "runtime" / "frozen_sniper"

    def file_write_ledger_path(self, project_dir: Path) -> Path:
        return project_dir / "runtime" / self.file_write_ledger_name

    def build_agent_file_manifest(
        self,
        project_slug: str,
        scanner_report: Dict[str, Any],
        *,
        project_dir: Path | None = None,
        source: str = "manual_baseline",
    ) -> Dict[str, Any]:
        files = []
        for entry in scanner_report.get("files") or []:
            if not isinstance(entry, dict):
                continue
            relative_path = str(entry.get("path") or "")
            baseline_content = ""
            if project_dir is not None and relative_path:
                resolved_file = self.resolve_editor_file(project_dir, relative_path)
                if resolved_file is not None:
                    try:
                        baseline_content = resolved_file[1].read_text(encoding="utf-8")
                    except (UnicodeDecodeError, OSError):
                        baseline_content = ""
            files.append(
                {
                    "path": relative_path,
                    "name": str(entry.get("name") or ""),
                    "sha256": str(entry.get("sha256") or ""),
                    "lineCount": int(entry.get("lineCount") or 0),
                    "characterCount": int(entry.get("characterCount") or 0),
                    "byteCount": int(entry.get("byteCount") or 0),
                    "maxLineLength": int(entry.get("maxLineLength") or 0),
                    "language": str(entry.get("language") or ""),
                    "status": "agent_final",
                    "content": baseline_content,
                }
            )
        return {
            "schema_version": 1,
            "report_type": "agent_file_manifest",
            "projectId": project_slug,
            "createdAt": self.now(),
            "source": source,
            "scannerReport": {
                "generatedAt": scanner_report.get("generatedAt"),
                "artifact": (scanner_report.get("validation") or {}).get("artifact"),
                "checkpoint": (scanner_report.get("validation") or {}).get("checkpoint"),
                "visual_playback": (scanner_report.get("scanner") or {}).get("visual_playback"),
            },
            "summary": {
                "files": len(files),
                "lines": sum(int(entry.get("lineCount") or 0) for entry in files),
                "characters": sum(int(entry.get("characterCount") or 0) for entry in files),
                "bytes": sum(int(entry.get("byteCount") or 0) for entry in files),
            },
            "files": files,
        }

    @staticmethod
    def canonical_json_sha256(value: Any) -> str:
        payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def seal_sha256(self, seal: Dict[str, Any]) -> str:
        payload = {key: value for key, value in seal.items() if key != "sealSha256"}
        return self.canonical_json_sha256(payload)

    @staticmethod
    def baseline_signing_key() -> str:
        return str(os.environ.get("HABLA_BASELINE_SIGNING_KEY") or "")

    def baseline_anchor_signature(self, anchor: Dict[str, Any]) -> str:
        payload = {key: value for key, value in anchor.items() if key != "signature"}
        serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        key = self.baseline_signing_key()
        if not key:
            return ""
        return hmac.new(key.encode("utf-8"), serialized.encode("utf-8"), hashlib.sha256).hexdigest()

    def build_baseline_external_anchor(self, seal: Dict[str, Any]) -> Dict[str, Any]:
        project_id = str(seal.get("projectId") or "")
        anchor_path = self.baseline_external_anchor_path(project_id)
        key = self.baseline_signing_key()
        anchor = {
            "schema_version": 1,
            "report_type": "baseline_external_anchor",
            "projectId": project_id,
            "anchoredAt": self.now(),
            "manifestSha256": str(seal.get("manifestSha256") or ""),
            "sealSha256": str(seal.get("sealSha256") or ""),
            "manifestPath": str(seal.get("manifestPath") or ""),
            "sealPath": str(seal.get("sealPath") or ""),
            "vaultPath": str(seal.get("vaultPath") or ""),
            "anchorPath": str(anchor_path),
            "signatureAlgorithm": "hmac-sha256" if key else "unsigned",
        }
        signature = self.baseline_anchor_signature(anchor)
        if signature:
            anchor["signature"] = signature
        return anchor

    def build_agent_file_manifest_seal(
        self,
        project_dir: Path,
        manifest: Dict[str, Any],
        manifest_path: Path,
    ) -> Dict[str, Any]:
        manifest_sha256 = self.canonical_json_sha256(manifest)
        vault_path = self.baseline_vault_manifest_path(project_dir, manifest_sha256)
        project_id = str(manifest.get("projectId") or "")
        seal = {
            "schema_version": 1,
            "report_type": "agent_file_manifest_seal",
            "projectId": project_id,
            "sealedAt": self.now(),
            "manifestCreatedAt": manifest.get("createdAt"),
            "manifestPath": str(manifest_path),
            "manifestSha256": manifest_sha256,
            "manifestSummary": manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {},
            "vaultPath": str(vault_path),
            "sealPath": str(self.agent_file_manifest_seal_path(project_dir)),
            "externalAnchorPath": str(self.baseline_external_anchor_path(project_id)),
            "source": str(manifest.get("source") or ""),
            "protection": "tamper_evident_vault_copy_external_anchor",
        }
        seal["sealSha256"] = self.seal_sha256(seal)
        return seal

    def persist_agent_file_manifest(self, project_dir: Path, manifest: Dict[str, Any]) -> Path:
        path = self.agent_file_manifest_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        seal = self.build_agent_file_manifest_seal(project_dir, manifest, path)
        seal_path = self.agent_file_manifest_seal_path(project_dir)
        seal_path.parent.mkdir(parents=True, exist_ok=True)
        seal_path.write_text(json.dumps(seal, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        vault_path = Path(str(seal.get("vaultPath") or ""))
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        ledger_path = self.baseline_seal_ledger_path(project_dir)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(seal, ensure_ascii=True) + "\n")
        anchor = self.build_baseline_external_anchor(seal)
        anchor_path = self.baseline_external_anchor_path(str(seal.get("projectId") or ""))
        anchor_path.parent.mkdir(parents=True, exist_ok=True)
        anchor_path.write_text(json.dumps(anchor, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        anchor_ledger_path = self.baseline_external_anchor_ledger_path(str(seal.get("projectId") or ""))
        with anchor_ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(anchor, ensure_ascii=True) + "\n")
        return path

    def append_file_write_ledger(
        self,
        project_dir: Path,
        *,
        project_slug: str,
        relative_path: str,
        source: str,
        reason: str,
        before_content: str = "",
        after_content: str = "",
    ) -> None:
        path = self.file_write_ledger_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": self.now(),
            "projectId": project_slug,
            "path": relative_path,
            "source": source,
            "reason": reason,
            "beforeSha256": hashlib.sha256(before_content.encode("utf-8")).hexdigest() if before_content else "",
            "afterSha256": hashlib.sha256(after_content.encode("utf-8")).hexdigest() if after_content else "",
            "beforeCharacters": len(before_content),
            "afterCharacters": len(after_content),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    def read_file_write_ledger(self, project_dir: Path) -> List[Dict[str, Any]]:
        path = self.file_write_ledger_path(project_dir)
        if not path.exists():
            return []
        events: List[Dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
        return events

    @staticmethod
    def registered_write_after_baseline(
        ledger: List[Dict[str, Any]],
        relative_path: str,
        baseline_at: str,
    ) -> bool:
        for event in reversed(ledger):
            if str(event.get("path") or "") != relative_path:
                continue
            if str(event.get("timestamp") or "") >= str(baseline_at or ""):
                return True
        return False

    @staticmethod
    def line_col_for_content(content: str, offset: int) -> tuple[int, int]:
        safe_offset = max(0, min(len(content), int(offset or 0)))
        prefix = content[:safe_offset]
        line = prefix.count("\n") + 1
        last_break = prefix.rfind("\n")
        column = safe_offset + 1 if last_break < 0 else safe_offset - last_break
        return line, max(1, column)

    def integrity_text_findings(
        self,
        *,
        path: str,
        expected_content: str,
        actual_content: str,
        expected_hash: str,
        actual_hash: str,
        finding_limit: int = 500,
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        matcher = difflib.SequenceMatcher(None, expected_content, actual_content, autojunk=False)
        for tag, expected_start, expected_end, actual_start, actual_end in matcher.get_opcodes():
            if tag == "equal":
                continue
            line, column = self.line_col_for_content(
                actual_content if tag != "delete" else expected_content,
                actual_start if tag != "delete" else expected_start,
            )
            expected_text = expected_content[expected_start:expected_end]
            actual_text = actual_content[actual_start:actual_end]
            if tag == "replace":
                finding_type = "char_replaced"
                message = "Caracter o segmento reemplazado externamente."
            elif tag == "delete":
                finding_type = "char_deleted"
                message = "Caracter o segmento eliminado externamente."
            else:
                finding_type = "char_inserted"
                message = "Caracter o segmento insertado externamente."
            findings.append(
                {
                    "id": f"{path}:{finding_type}:{line}:{column}:{len(findings)}",
                    "severity": "error",
                    "type": finding_type,
                    "path": path,
                    "line": line,
                    "column": column,
                    "length": max(1, len(actual_text) if actual_text else len(expected_text)),
                    "expectedText": expected_text[:120],
                    "actualText": actual_text[:120],
                    "expectedSha256": expected_hash,
                    "actualSha256": actual_hash,
                    "message": message,
                }
            )
            if len(findings) >= finding_limit:
                break
        return findings

    @staticmethod
    def baseline_protection_finding(
        *,
        finding_type: str,
        severity: str,
        message: str,
        path: str,
        expected_sha256: str = "",
        actual_sha256: str = "",
    ) -> Dict[str, Any]:
        return {
            "id": f"baseline:{finding_type}:{path}",
            "severity": severity,
            "type": finding_type,
            "path": path,
            "line": 1,
            "column": 1,
            "length": 1,
            "expectedSha256": expected_sha256,
            "actualSha256": actual_sha256,
            "message": message,
        }

    def load_external_anchor_manifest(self, anchor: Dict[str, Any]) -> tuple[Dict[str, Any], str, bool]:
        vault_path = Path(str(anchor.get("vaultPath") or ""))
        vault_manifest = self.load_json_file(vault_path, {})
        vault_sha = self.canonical_json_sha256(vault_manifest) if isinstance(vault_manifest, dict) and vault_manifest else ""
        expected_sha = str(anchor.get("manifestSha256") or "")
        return (vault_manifest if isinstance(vault_manifest, dict) else {}, vault_sha, bool(expected_sha and vault_sha == expected_sha))

    def verify_baseline_external_anchor(self, seal: Dict[str, Any]) -> Dict[str, Any]:
        project_id = str(seal.get("projectId") or "")
        anchor_path = self.baseline_external_anchor_path(project_id)
        findings: List[Dict[str, Any]] = []
        result: Dict[str, Any] = {
            "status": "missing",
            "passed": False,
            "anchorPath": str(anchor_path),
            "signed": False,
            "signatureValid": False,
            "canRestoreManifestFromExternalAnchor": False,
        }
        if not anchor_path.exists():
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_external_anchor_missing",
                    severity="critical",
                    path=str(anchor_path),
                    expected_sha256=str(seal.get("manifestSha256") or ""),
                    message="No existe ancla externa para verificar la baseline contra agentes.",
                )
            )
            result["findings"] = findings
            return result

        anchor = self.load_json_file(anchor_path, {})
        if not isinstance(anchor, dict) or not anchor:
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_external_anchor_unreadable",
                    severity="critical",
                    path=str(anchor_path),
                    message="El ancla externa de baseline no se puede leer.",
                )
            )
            result["status"] = "unreadable"
            result["findings"] = findings
            return result

        key = self.baseline_signing_key()
        signature = str(anchor.get("signature") or "")
        result.update(
            {
                "status": "loaded",
                "anchor": {
                    key_name: anchor.get(key_name)
                    for key_name in (
                        "projectId",
                        "manifestSha256",
                        "sealSha256",
                        "vaultPath",
                        "signatureAlgorithm",
                    )
                },
                "signed": bool(signature),
            }
        )
        if key:
            expected_signature = self.baseline_anchor_signature(anchor)
            signature_valid = bool(signature and hmac.compare_digest(signature, expected_signature))
            result["signatureValid"] = signature_valid
            if not signature:
                findings.append(
                    self.baseline_protection_finding(
                        finding_type="baseline_external_anchor_unsigned",
                        severity="critical",
                        path=str(anchor_path),
                        expected_sha256=expected_signature,
                        message="Existe clave de firma pero el ancla externa no esta firmada.",
                    )
                )
            elif not signature_valid:
                findings.append(
                    self.baseline_protection_finding(
                        finding_type="baseline_external_anchor_tampered",
                        severity="critical",
                        path=str(anchor_path),
                        expected_sha256=expected_signature,
                        actual_sha256=signature,
                        message="La firma HMAC del ancla externa no coincide.",
                    )
                )

        anchor_manifest_sha = str(anchor.get("manifestSha256") or "")
        anchor_seal_sha = str(anchor.get("sealSha256") or "")
        seal_manifest_sha = str(seal.get("manifestSha256") or "")
        seal_hash = str(seal.get("sealSha256") or "")
        if anchor_manifest_sha != seal_manifest_sha or anchor_seal_sha != seal_hash:
            vault_manifest, vault_sha, vault_valid = self.load_external_anchor_manifest(anchor)
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_external_anchor_mismatch",
                    severity="critical",
                    path=str(anchor_path),
                    expected_sha256=anchor_manifest_sha,
                    actual_sha256=seal_manifest_sha,
                    message="El sello interno de baseline no coincide con el ancla externa.",
                )
            )
            result.update({"status": "mismatch", "passed": False, "vaultSha256": vault_sha, "vaultValid": vault_valid})
            if vault_valid:
                result["canRestoreManifestFromExternalAnchor"] = True
                result["effectiveManifest"] = vault_manifest
            result["findings"] = findings
            return result

        vault_manifest, vault_sha, vault_valid = self.load_external_anchor_manifest(anchor)
        result.update({"vaultSha256": vault_sha, "vaultValid": vault_valid})
        if not vault_valid:
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_external_anchor_vault_tampered",
                    severity="critical",
                    path=str(anchor.get("vaultPath") or ""),
                    expected_sha256=anchor_manifest_sha,
                    actual_sha256=vault_sha,
                    message="La boveda apuntada por el ancla externa no coincide con su SHA-256.",
                )
            )
            result["status"] = "vault_tampered"
            result["findings"] = findings
            return result

        result["status"] = "verified"
        result["passed"] = not findings
        result["findings"] = findings
        return result

    def load_protected_agent_file_manifest(self, project_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        seal_path = self.agent_file_manifest_seal_path(project_dir)
        manifest_sha = self.canonical_json_sha256(manifest) if isinstance(manifest, dict) and manifest else ""
        findings: List[Dict[str, Any]] = []
        protection: Dict[str, Any] = {
            "status": "unsealed",
            "passed": False,
            "manifestSha256": manifest_sha,
            "sealPath": str(seal_path),
            "vaultPath": "",
            "vaultValid": False,
        }
        if not seal_path.exists():
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_unsealed",
                    severity="error",
                    path=f"runtime/artifacts/{self.agent_file_manifest_name}",
                    actual_sha256=manifest_sha,
                    message="Baseline forense existe pero no tiene sello de integridad.",
                )
            )
            protection["findings"] = findings
            return {"manifest": manifest, "protection": protection, "findings": findings}

        seal = self.load_json_file(seal_path, {})
        expected_seal_sha = str(seal.get("sealSha256") or "") if isinstance(seal, dict) else ""
        actual_seal_sha = self.seal_sha256(seal) if isinstance(seal, dict) and seal else ""
        if not isinstance(seal, dict) or not seal or expected_seal_sha != actual_seal_sha:
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_seal_tampered",
                    severity="critical",
                    path=f"runtime/artifacts/{self.agent_file_manifest_seal_name}",
                    expected_sha256=expected_seal_sha,
                    actual_sha256=actual_seal_sha,
                    message="El sello de la baseline fue alterado o no se puede verificar.",
                )
            )
            protection["status"] = "seal_tampered"
            protection["findings"] = findings
            return {"manifest": manifest, "protection": protection, "findings": findings}

        expected_manifest_sha = str(seal.get("manifestSha256") or "")
        vault_path = Path(str(seal.get("vaultPath") or self.baseline_vault_manifest_path(project_dir, expected_manifest_sha)))
        protection.update(
            {
                "status": "sealed",
                "passed": True,
                "expectedManifestSha256": expected_manifest_sha,
                "vaultPath": str(vault_path),
            }
        )
        vault_manifest = self.load_json_file(vault_path, {})
        vault_sha = self.canonical_json_sha256(vault_manifest) if isinstance(vault_manifest, dict) and vault_manifest else ""
        vault_valid = bool(expected_manifest_sha and vault_sha == expected_manifest_sha)
        protection["vaultSha256"] = vault_sha
        protection["vaultValid"] = vault_valid
        anchor_result = self.verify_baseline_external_anchor(seal)
        anchor_findings = [finding for finding in anchor_result.get("findings", []) if isinstance(finding, dict)]
        findings.extend(anchor_findings)
        protection["externalAnchor"] = {key: value for key, value in anchor_result.items() if key not in {"effectiveManifest", "findings"}}
        if anchor_result.get("canRestoreManifestFromExternalAnchor") and isinstance(anchor_result.get("effectiveManifest"), dict):
            protection["status"] = "external_anchor_mismatch"
            protection["passed"] = False
            protection["effectiveSource"] = "external_anchor_vault"
            protection["canRestoreManifestFromExternalAnchor"] = True
            protection["findings"] = findings
            return {"manifest": anchor_result["effectiveManifest"], "protection": protection, "findings": findings}
        if anchor_findings:
            protection["status"] = str(anchor_result.get("status") or "external_anchor_failed")
            protection["passed"] = False
            protection["findings"] = findings
            return {"manifest": manifest, "protection": protection, "findings": findings}

        if manifest_sha != expected_manifest_sha:
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_manifest_tampered",
                    severity="critical",
                    path=f"runtime/artifacts/{self.agent_file_manifest_name}",
                    expected_sha256=expected_manifest_sha,
                    actual_sha256=manifest_sha,
                    message="El manifiesto baseline no coincide con su sello; se detecto manipulacion de la baseline.",
                )
            )
            protection["status"] = "manifest_tampered"
            protection["passed"] = False
            if vault_valid:
                protection["effectiveSource"] = "vault"
                protection["canRestoreManifestFromVault"] = True
                protection["findings"] = findings
                return {"manifest": vault_manifest, "protection": protection, "findings": findings}
            protection["effectiveSource"] = "untrusted_manifest"
            protection["findings"] = findings
            return {"manifest": manifest, "protection": protection, "findings": findings}

        if not vault_path.exists():
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_vault_missing",
                    severity="warning",
                    path=str(vault_path),
                    expected_sha256=expected_manifest_sha,
                    actual_sha256="",
                    message="La copia de boveda de la baseline no existe.",
                )
            )
            protection["status"] = "vault_missing"
            protection["passed"] = False
        elif not vault_valid:
            findings.append(
                self.baseline_protection_finding(
                    finding_type="baseline_vault_tampered",
                    severity="critical",
                    path=str(vault_path),
                    expected_sha256=expected_manifest_sha,
                    actual_sha256=vault_sha,
                    message="La copia de boveda de la baseline no coincide con el sello.",
                )
            )
            protection["status"] = "vault_tampered"
            protection["passed"] = False

        protection["effectiveSource"] = "manifest"
        protection["findings"] = findings
        return {"manifest": manifest, "protection": protection, "findings": findings}

    def build_file_integrity_report(
        self,
        project_slug: str,
        project_dir: Path,
        *,
        persist: bool = False,
    ) -> Dict[str, Any]:
        manifest_path = self.agent_file_manifest_path(project_dir)
        manifest = self.load_json_file(manifest_path, {})
        generated_at = self.now()
        if not isinstance(manifest, dict) or not manifest.get("files"):
            report = {
                "schema_version": 1,
                "report_type": "file_integrity_report",
                "projectId": project_slug,
                "generatedAt": generated_at,
                "baselinePath": str(manifest_path),
                "baselineExists": False,
                "summary": {
                    "totalFindings": 0,
                    "modifiedFiles": 0,
                    "deletedFiles": 0,
                    "untrackedFiles": 0,
                    "registeredWrites": 0,
                },
                "validation": {"passed": True, "blockers": []},
                "findings": [],
            }
            if persist:
                self.persist_file_integrity_report(project_dir, report)
            return report

        protected_manifest = self.load_protected_agent_file_manifest(project_dir, manifest)
        manifest = protected_manifest.get("manifest") if isinstance(protected_manifest.get("manifest"), dict) else manifest
        baseline_protection = protected_manifest.get("protection") if isinstance(protected_manifest.get("protection"), dict) else {}
        baseline_findings = [finding for finding in protected_manifest.get("findings", []) if isinstance(finding, dict)]
        baseline_at = str(manifest.get("createdAt") or "")
        manifest_files = {str(entry.get("path") or ""): entry for entry in manifest.get("files") or [] if isinstance(entry, dict)}
        current_files = {str(entry.get("path") or ""): entry for entry in self.list_editor_files(project_dir)}
        ledger = self.read_file_write_ledger(project_dir)
        findings: List[Dict[str, Any]] = list(baseline_findings)
        registered_writes = 0

        for relative_path, manifest_entry in manifest_files.items():
            if not relative_path:
                continue
            current_entry = current_files.get(relative_path)
            expected_hash = str(manifest_entry.get("sha256") or "")
            if current_entry is None:
                if self.registered_write_after_baseline(ledger, relative_path, baseline_at):
                    registered_writes += 1
                    continue
                findings.append(
                    {
                        "id": f"{relative_path}:file_deleted",
                        "severity": "error",
                        "type": "file_deleted",
                        "path": relative_path,
                        "line": 1,
                        "column": 1,
                        "length": 1,
                        "expectedSha256": expected_hash,
                        "actualSha256": "",
                        "message": "Archivo generado por agente fue eliminado externamente.",
                    }
                )
                continue
            resolved_file = self.resolve_editor_file(project_dir, relative_path)
            if resolved_file is None:
                continue
            _, file_path = resolved_file
            try:
                actual_content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                findings.append(
                    {
                        "id": f"{relative_path}:file_unreadable",
                        "severity": "error",
                        "type": "file_unreadable",
                        "path": relative_path,
                        "line": 1,
                        "column": 1,
                        "length": 1,
                        "expectedSha256": expected_hash,
                        "actualSha256": "",
                        "message": "Archivo generado por agente ya no se puede leer como UTF-8.",
                    }
                )
                continue
            actual_hash = hashlib.sha256(actual_content.encode("utf-8")).hexdigest()
            if actual_hash == expected_hash:
                continue
            if self.registered_write_after_baseline(ledger, relative_path, baseline_at):
                registered_writes += 1
                continue
            baseline_text = str(manifest_entry.get("content") or "")
            expected_content = baseline_text if baseline_text else actual_content
            text_findings = self.integrity_text_findings(
                path=relative_path,
                expected_content=expected_content,
                actual_content=actual_content,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
            )
            if baseline_text and text_findings:
                findings.extend(text_findings)
            else:
                findings.append(
                    {
                        "id": f"{relative_path}:file_modified",
                        "severity": "error",
                        "type": "file_modified",
                        "path": relative_path,
                        "line": 1,
                        "column": 1,
                        "length": 1,
                        "expectedSha256": expected_hash,
                        "actualSha256": actual_hash,
                        "message": "Archivo generado por agente fue modificado externamente.",
                    }
                )

        for relative_path, current_entry in current_files.items():
            if relative_path in manifest_files:
                continue
            if self.registered_write_after_baseline(ledger, relative_path, baseline_at):
                registered_writes += 1
                continue
            actual_hash = str(current_entry.get("sha256") or "")
            resolved_file = self.resolve_editor_file(project_dir, relative_path)
            if not actual_hash and resolved_file is not None:
                try:
                    current_content = resolved_file[1].read_text(encoding="utf-8")
                    actual_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
                except (UnicodeDecodeError, OSError):
                    actual_hash = ""
            findings.append(
                {
                    "id": f"{relative_path}:untracked_file",
                    "severity": "warning",
                    "type": "untracked_file",
                    "path": relative_path,
                    "line": 1,
                    "column": 1,
                    "length": 1,
                    "expectedSha256": "",
                    "actualSha256": actual_hash,
                    "message": "Archivo nuevo no registrado en baseline del agente.",
                }
            )

        summary = {
            "totalFindings": len(findings),
            "modifiedFiles": len(
                {
                    finding["path"]
                    for finding in findings
                    if finding.get("type") not in {"file_deleted", "untracked_file"}
                    and not str(finding.get("type") or "").startswith("baseline_")
                }
            ),
            "deletedFiles": len([finding for finding in findings if finding.get("type") == "file_deleted"]),
            "untrackedFiles": len([finding for finding in findings if finding.get("type") == "untracked_file"]),
            "baselineFindings": len(baseline_findings),
            "registeredWrites": registered_writes,
        }
        report = {
            "schema_version": 1,
            "report_type": "file_integrity_report",
            "projectId": project_slug,
            "generatedAt": generated_at,
            "baselinePath": str(manifest_path),
            "baselineCreatedAt": baseline_at,
            "baselineExists": True,
            "baselineProtection": baseline_protection,
            "summary": summary,
            "validation": {
                "passed": not findings,
                "blockers": [finding.get("message") for finding in findings[:20]],
            },
            "findings": findings,
        }
        if persist:
            self.persist_file_integrity_report(project_dir, report)
        return report

    @staticmethod
    def frozen_sniper_run_id() -> str:
        now = datetime.now(timezone.utc)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        fingerprint = hashlib.sha256(now.isoformat().encode("utf-8")).hexdigest()[:8]
        return f"{stamp}-{fingerprint}"

    def relative_project_path(self, project_dir: Path, path: Path) -> str:
        try:
            return self.normalize_relative_fragment(path.resolve().relative_to(project_dir.resolve()))
        except ValueError:
            return str(path)

    def unique_nested_path(self, root: Path, relative_path: str) -> Path:
        normalized = self.normalize_relative_fragment(relative_path)
        candidate = (root / normalized).resolve()
        root_resolved = root.resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            candidate = root_resolved / hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if not candidate.exists():
            return candidate
        suffix = candidate.suffix
        stem = candidate.name[: -len(suffix)] if suffix else candidate.name
        for index in range(1, 1000):
            next_candidate = candidate.with_name(f"{stem}.{index}{suffix}")
            if not next_candidate.exists():
                return next_candidate
        return candidate.with_name(f"{stem}.{hashlib.sha256(str(time.time()).encode('utf-8')).hexdigest()[:8]}{suffix}")

    def freeze_existing_file(self, project_dir: Path, evidence_dir: Path, relative_path: str) -> str:
        resolved = self.resolve_editor_file(project_dir, relative_path)
        if resolved is None:
            return ""
        normalized, file_path = resolved
        target_path = self.unique_nested_path(evidence_dir, normalized)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target_path)
        return self.relative_project_path(project_dir, target_path)

    def build_frozen_sniper_recovery(
        self,
        project_slug: str,
        project_dir: Path,
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        manifest_path = self.agent_file_manifest_path(project_dir)
        manifest = self.load_json_file(manifest_path, {})
        before_report = self.build_file_integrity_report(project_slug, project_dir, persist=True)
        run_id = self.frozen_sniper_run_id()
        operation_root = self.frozen_sniper_root(project_dir) / run_id
        evidence_dir = operation_root / "evidence"
        quarantine_dir = operation_root / "quarantine"
        actions: List[Dict[str, Any]] = []
        errors: List[str] = []

        if not isinstance(manifest, dict) or not manifest.get("files"):
            report = {
                "schema_version": 1,
                "report_type": "frozen_sniper_recovery",
                "projectId": project_slug,
                "generatedAt": self.now(),
                "mode": "dry_run" if dry_run else "recover",
                "runId": run_id,
                "baselinePath": str(manifest_path),
                "baselineExists": False,
                "summary": {"restoredFiles": 0, "quarantinedFiles": 0, "frozenEvidenceFiles": 0, "skippedFindings": 0, "errors": 1},
                "validation": {"passed": False, "blockers": ["No existe baseline forense para Frozen Sniper."]},
                "actions": [],
                "beforeIntegrityReport": before_report,
                "afterIntegrityReport": before_report,
            }
            self.persist_frozen_sniper_report(project_dir, report)
            return report

        frozen_evidence_files = 0
        protected_manifest = self.load_protected_agent_file_manifest(project_dir, manifest)
        manifest = protected_manifest.get("manifest") if isinstance(protected_manifest.get("manifest"), dict) else manifest
        baseline_protection = protected_manifest.get("protection") if isinstance(protected_manifest.get("protection"), dict) else {}
        baseline_status = str(baseline_protection.get("status") or "")
        can_restore_manifest = bool(
            baseline_protection.get("canRestoreManifestFromVault")
            or baseline_protection.get("canRestoreManifestFromExternalAnchor")
        )
        if baseline_status in {"unsealed", "seal_tampered", "manifest_tampered", "vault_tampered"} and not can_restore_manifest:
            blocker = f"baseline_protection_failed:{baseline_status or 'unknown'}"
            report = {
                "schema_version": 1,
                "report_type": "frozen_sniper_recovery",
                "projectId": project_slug,
                "generatedAt": self.now(),
                "mode": "dry_run" if dry_run else "recover",
                "runId": run_id,
                "baselinePath": str(manifest_path),
                "baselineExists": True,
                "baselineProtection": baseline_protection,
                "summary": {
                    "restoredFiles": 0,
                    "quarantinedFiles": 0,
                    "frozenEvidenceFiles": 0,
                    "skippedFindings": 0,
                    "errors": 1,
                    "remainingFindings": len(before_report.get("findings") or []),
                },
                "validation": {"passed": False, "blockers": [blocker]},
                "actions": [],
                "beforeIntegrityReport": before_report,
                "afterIntegrityReport": before_report,
            }
            self.persist_frozen_sniper_report(project_dir, report)
            return report

        if can_restore_manifest:
            action = {
                "type": "restore_baseline_manifest_from_vault",
                "path": f"runtime/artifacts/{self.agent_file_manifest_name}",
                "status": "planned" if dry_run else "pending",
                "expectedSha256": baseline_protection.get("expectedManifestSha256"),
                "actualSha256": baseline_protection.get("manifestSha256"),
                "vaultPath": baseline_protection.get("vaultPath"),
            }
            if not dry_run:
                if manifest_path.exists():
                    target_path = self.unique_nested_path(evidence_dir, f"runtime/artifacts/{self.agent_file_manifest_name}")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(manifest_path, target_path)
                    action["frozenEvidencePath"] = self.relative_project_path(project_dir, target_path)
                    frozen_evidence_files = 1
                self.persist_agent_file_manifest(project_dir, manifest)
                action["status"] = "restored"
            actions.append(action)

        manifest_files = {str(entry.get("path") or ""): entry for entry in manifest.get("files") or [] if isinstance(entry, dict)}
        findings = [finding for finding in before_report.get("findings") or [] if isinstance(finding, dict)]
        restored_paths: set[str] = set()
        quarantined_paths: set[str] = set()
        skipped_findings = 0

        for finding in findings:
            finding_type = str(finding.get("type") or "")
            relative_path = self.normalize_relative_fragment(finding.get("path") or "")
            if not relative_path:
                skipped_findings += 1
                continue

            if finding_type == "untracked_file":
                if relative_path in quarantined_paths:
                    continue
                quarantined_paths.add(relative_path)
                action: Dict[str, Any] = {
                    "type": "quarantine_untracked_file",
                    "path": relative_path,
                    "status": "planned" if dry_run else "pending",
                    "findingType": finding_type,
                    "actualSha256": finding.get("actualSha256"),
                }
                resolved = self.resolve_editor_file(project_dir, relative_path)
                if resolved is None:
                    action["status"] = "missing"
                    action["message"] = "Archivo no registrado ya no existe."
                    actions.append(action)
                    continue
                normalized, source_path = resolved
                if dry_run:
                    action["quarantinePath"] = self.relative_project_path(project_dir, self.unique_nested_path(quarantine_dir, normalized))
                    actions.append(action)
                    continue
                frozen_path = self.freeze_existing_file(project_dir, evidence_dir, normalized)
                if frozen_path:
                    frozen_evidence_files += 1
                    action["frozenEvidencePath"] = frozen_path
                quarantine_path = self.unique_nested_path(quarantine_dir, normalized)
                quarantine_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(quarantine_path))
                action["status"] = "quarantined"
                action["quarantinePath"] = self.relative_project_path(project_dir, quarantine_path)
                actions.append(action)
                continue

            if finding_type not in {"file_deleted", "file_modified", "file_unreadable"} and not finding_type.startswith("char_"):
                skipped_findings += 1
                actions.append(
                    {
                        "type": "skip_unknown_finding",
                        "path": relative_path,
                        "findingType": finding_type,
                        "status": "skipped",
                    }
                )
                continue

            if relative_path in restored_paths:
                continue
            restored_paths.add(relative_path)
            manifest_entry = manifest_files.get(relative_path)
            action = {
                "type": "restore_from_baseline",
                "path": relative_path,
                "status": "planned" if dry_run else "pending",
                "findingType": finding_type,
                "expectedSha256": finding.get("expectedSha256") or (manifest_entry or {}).get("sha256"),
            }
            if not manifest_entry:
                action["status"] = "skipped"
                action["message"] = "No hay entrada baseline para restaurar este archivo."
                skipped_findings += 1
                actions.append(action)
                continue
            expected_content = str(manifest_entry.get("content") or "")
            expected_sha = str(manifest_entry.get("sha256") or "")
            if expected_sha and hashlib.sha256(expected_content.encode("utf-8")).hexdigest() != expected_sha:
                action["status"] = "skipped"
                action["message"] = "La copia baseline no coincide con su SHA-256; no se restaura."
                errors.append(f"baseline_sha_mismatch:{relative_path}")
                actions.append(action)
                continue
            resolved_target = self.resolve_editor_file(project_dir, relative_path, must_exist=False)
            if resolved_target is None:
                action["status"] = "skipped"
                action["message"] = "Ruta rechazada por politica de editor."
                errors.append(f"path_rejected:{relative_path}")
                actions.append(action)
                continue
            normalized, target_path = resolved_target
            if dry_run:
                action["targetPath"] = normalized
                actions.append(action)
                continue
            frozen_path = self.freeze_existing_file(project_dir, evidence_dir, normalized)
            if frozen_path:
                frozen_evidence_files += 1
                action["frozenEvidencePath"] = frozen_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(expected_content, encoding="utf-8")
            restored_sha = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
            action["status"] = "restored"
            action["actualSha256"] = restored_sha
            actions.append(action)

        after_report = before_report if dry_run else self.build_file_integrity_report(project_slug, project_dir, persist=True)
        remaining_findings = len(after_report.get("findings") or []) if isinstance(after_report, dict) else 0
        if remaining_findings:
            errors.append(f"remaining_findings:{remaining_findings}")

        summary = {
            "restoredFiles": len([action for action in actions if action.get("status") == "restored" and action.get("type") == "restore_from_baseline"]),
            "restoredBaselines": len([action for action in actions if action.get("status") == "restored" and action.get("type") == "restore_baseline_manifest_from_vault"]),
            "quarantinedFiles": len([action for action in actions if action.get("status") == "quarantined"]),
            "frozenEvidenceFiles": frozen_evidence_files,
            "skippedFindings": skipped_findings,
            "errors": len(errors),
            "remainingFindings": remaining_findings,
        }
        report = {
            "schema_version": 1,
            "report_type": "frozen_sniper_recovery",
            "projectId": project_slug,
            "generatedAt": self.now(),
            "mode": "dry_run" if dry_run else "recover",
            "runId": run_id,
            "operationRoot": self.relative_project_path(project_dir, operation_root),
            "evidenceDir": self.relative_project_path(project_dir, evidence_dir),
            "quarantineDir": self.relative_project_path(project_dir, quarantine_dir),
            "baselinePath": str(manifest_path),
            "integrityReportPath": str(self.file_integrity_report_path(project_dir)),
            "baselineExists": True,
            "baselineProtection": baseline_protection,
            "summary": summary,
            "validation": {"passed": not errors, "blockers": errors},
            "actions": actions,
            "beforeIntegrityReport": before_report,
            "afterIntegrityReport": after_report,
        }
        self.persist_frozen_sniper_report(project_dir, report)
        if not dry_run:
            operation_root.mkdir(parents=True, exist_ok=True)
            (operation_root / "report.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return report

    def persist_file_integrity_report(self, project_dir: Path, report: Dict[str, Any]) -> Path:
        path = self.file_integrity_report_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return path

    def persist_frozen_sniper_report(self, project_dir: Path, report: Dict[str, Any]) -> Path:
        path = self.frozen_sniper_report_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return path
