"""Security decision layer for autonomous project execution."""

from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shlex import split as shlex_split
from typing import Any


DEFAULT_SECURITY_POLICY_PATH = Path("runtime/security_policy.json")
DEFAULT_SECURITY_EVENTS_PATH = Path("runtime/security_events.jsonl")
DEFAULT_OPERATOR_APPROVAL_PATH = Path("runtime/operator_approval.json")
DECISIONS = frozenset({"allow", "ask", "deny"})
RISK_LEVELS = frozenset({"low", "medium", "high", "forbidden"})
PASSWORD_HASH_ITERATIONS = 200000


class SecurityPolicyError(ValueError):
    """Raised when a security policy or decision request is invalid."""


def load_security_policy(path: str | Path = DEFAULT_SECURITY_POLICY_PATH) -> dict[str, Any]:
    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return validate_security_policy(payload)


def validate_security_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise SecurityPolicyError("Security policy must be an object")
    if policy.get("schema_version") != 1:
        raise SecurityPolicyError("SecurityPolicy.schema_version must be 1")

    default_decision = policy.get("default_decision", "ask")
    _expect_choice(default_decision, DECISIONS, "SecurityPolicy.default_decision")

    risk_categories = policy.get("risk_categories")
    if not isinstance(risk_categories, dict) or not risk_categories:
        raise SecurityPolicyError("SecurityPolicy.risk_categories must be a non-empty object")
    normalized_categories = {
        str(name): _validate_category(str(name), value)
        for name, value in risk_categories.items()
    }

    normalized = {
        **policy,
        "default_decision": default_decision,
        "risk_categories": normalized_categories,
        "allow_prefixes": [_normalize_command(item) for item in policy.get("allow_prefixes", [])],
        "ask_prefixes": [_normalize_command(item) for item in policy.get("ask_prefixes", [])],
        "deny_prefixes": [_normalize_command(item) for item in policy.get("deny_prefixes", [])],
        "security_events_log": policy.get("security_events_log", str(DEFAULT_SECURITY_EVENTS_PATH)),
    }
    return normalized


def decide_command(
    command: str | list[str],
    *,
    policy: dict[str, Any],
    cwd: str | Path = ".",
    workspace: str | Path = ".",
    operator_approval: dict[str, Any] | None = None,
    approval_password: str | None = None,
    plan_sha256: str | None = None,
) -> dict[str, Any]:
    validated_policy = validate_security_policy(policy)
    normalized_command = _normalize_command(command)
    workspace_path = Path(workspace).resolve()
    cwd_path = (workspace_path / cwd).resolve()

    category = _classify_command(normalized_command)
    decision = {
        "schema_version": 1,
        "recorded_at": _utc_now(),
        "decision": validated_policy["default_decision"],
        "risk_level": "medium",
        "category": category,
        "reason": "Default security decision",
        "command": normalized_command,
        "cwd": str(cwd_path),
        "workspace": str(workspace_path),
    }

    try:
        cwd_path.relative_to(workspace_path)
    except ValueError:
        return {
            **decision,
            "decision": "deny",
            "risk_level": "forbidden",
            "reason": "cwd escapes workspace",
        }

    if not cwd_path.exists() or not cwd_path.is_dir():
        return {
            **decision,
            "decision": "deny",
            "risk_level": "forbidden",
            "reason": "cwd does not exist or is not a directory",
        }

    matched = _match_prefix(normalized_command, validated_policy["deny_prefixes"])
    if matched is not None:
        return {
            **decision,
            "decision": "deny",
            "risk_level": "forbidden",
            "reason": f"Matched deny prefix: {_format_command(matched)}",
        }

    matched = _match_prefix(normalized_command, validated_policy["allow_prefixes"])
    if matched is not None:
        category_policy = validated_policy["risk_categories"].get(category, {})
        return {
            **decision,
            "decision": "allow",
            "risk_level": category_policy.get("risk_level", "low"),
            "reason": f"Matched allow prefix: {_format_command(matched)}",
        }

    matched = _match_prefix(normalized_command, validated_policy["ask_prefixes"])
    if matched is not None:
        category_policy = validated_policy["risk_categories"].get(category, {})
        ask_decision = {
            **decision,
            "decision": "ask",
            "risk_level": category_policy.get("risk_level", "high"),
            "reason": f"Matched ask prefix: {_format_command(matched)}",
        }
        return _apply_operator_approval(
            ask_decision,
            operator_approval=operator_approval,
            approval_password=approval_password,
            plan_sha256=plan_sha256,
            cwd=cwd,
        )

    category_policy = validated_policy["risk_categories"].get(category)
    if category_policy is not None:
        category_decision = {
            **decision,
            "decision": category_policy["decision"],
            "risk_level": category_policy["risk_level"],
            "reason": f"Matched risk category: {category}",
        }
        return _apply_operator_approval(
            category_decision,
            operator_approval=operator_approval,
            approval_password=approval_password,
            plan_sha256=plan_sha256,
            cwd=cwd,
        )

    return _apply_operator_approval(
        decision,
        operator_approval=operator_approval,
        approval_password=approval_password,
        plan_sha256=plan_sha256,
        cwd=cwd,
    )


def create_operator_approval(
    *,
    plan_path: str | Path,
    workspace: str | Path,
    categories: list[str],
    password: str,
    expires_hours: int,
    approval_file: str | Path = DEFAULT_OPERATOR_APPROVAL_PATH,
) -> dict[str, Any]:
    if not password:
        raise SecurityPolicyError("Operator approval password must not be empty")
    if isinstance(expires_hours, bool) or not isinstance(expires_hours, int) or expires_hours < 1:
        raise SecurityPolicyError("expires_hours must be a positive integer")
    normalized_categories = _normalize_categories(categories)
    plan_document = _read_json(Path(plan_path))
    command_fingerprints = _fingerprints_from_plan(plan_document)
    salt = secrets.token_hex(16)
    approved_at = _utc_now()
    expires_at = (
        datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=expires_hours)
    ).isoformat().replace("+00:00", "Z")
    approval = {
        "schema_version": 1,
        "approval_id": secrets.token_hex(12),
        "approved_at": approved_at,
        "expires_at": expires_at,
        "workspace": str(Path(workspace).resolve()),
        "plan_path": str(Path(plan_path).resolve()),
        "plan_sha256": sha256_file(plan_path),
        "approved_categories": normalized_categories,
        "approved_command_sha256": command_fingerprints,
        "password_hash": {
            "algorithm": "pbkdf2_sha256",
            "iterations": PASSWORD_HASH_ITERATIONS,
            "salt": salt,
            "hash": _hash_password(password, salt, PASSWORD_HASH_ITERATIONS),
        },
    }
    validated = validate_operator_approval(approval)
    _atomic_write_json(Path(approval_file), validated)
    return validated


def load_operator_approval(path: str | Path = DEFAULT_OPERATOR_APPROVAL_PATH) -> dict[str, Any]:
    return validate_operator_approval(_read_json(Path(path)))


def validate_operator_approval(approval: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(approval, dict):
        raise SecurityPolicyError("OperatorApproval must be an object")
    if approval.get("schema_version") != 1:
        raise SecurityPolicyError("OperatorApproval.schema_version must be 1")
    for key in {
        "approval_id",
        "approved_at",
        "expires_at",
        "workspace",
        "plan_path",
        "plan_sha256",
        "approved_categories",
        "approved_command_sha256",
        "password_hash",
    }:
        if key not in approval:
            raise SecurityPolicyError(f"OperatorApproval missing required field: {key}")
    if not isinstance(approval["approval_id"], str) or not approval["approval_id"]:
        raise SecurityPolicyError("OperatorApproval.approval_id must be a non-empty string")
    _parse_utc_datetime(approval["approved_at"], "OperatorApproval.approved_at")
    _parse_utc_datetime(approval["expires_at"], "OperatorApproval.expires_at")
    if not isinstance(approval["workspace"], str) or not approval["workspace"]:
        raise SecurityPolicyError("OperatorApproval.workspace must be a non-empty string")
    if not isinstance(approval["plan_path"], str) or not approval["plan_path"]:
        raise SecurityPolicyError("OperatorApproval.plan_path must be a non-empty string")
    _expect_sha256(approval["plan_sha256"], "OperatorApproval.plan_sha256")
    _normalize_categories(approval["approved_categories"])
    if not isinstance(approval["approved_command_sha256"], list) or not approval["approved_command_sha256"]:
        raise SecurityPolicyError("OperatorApproval.approved_command_sha256 must be a non-empty list")
    for value in approval["approved_command_sha256"]:
        _expect_sha256(value, "OperatorApproval.approved_command_sha256[]")
    _validate_password_hash(approval["password_hash"])
    return dict(approval)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_security_event(
    decision: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    target_path = Path(log_path or (policy or {}).get("security_events_log", DEFAULT_SECURITY_EVENTS_PATH))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "recorded_at": _utc_now(),
        "security_decision": decision,
    }
    with target_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def main(argv: list[str] | None = None) -> int:
    actual_argv = sys.argv[1:] if argv is None else argv
    if actual_argv and actual_argv[0] == "approve-plan":
        return _main_approve_plan(actual_argv[1:])
    return _main_decide(actual_argv)


def _main_decide(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Evaluate one command against the security policy.")
    parser.add_argument("--policy", default=str(DEFAULT_SECURITY_POLICY_PATH))
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--operator-approval", default=str(DEFAULT_OPERATOR_APPROVAL_PATH))
    parser.add_argument("--approval-password-env", default="SECURITY_APPROVAL_PASSWORD")
    args = parser.parse_args(argv)

    try:
        policy = load_security_policy(args.policy)
        command = json.loads(args.command_json)
        approval = None
        approval_password = None
        approval_path = Path(args.operator_approval)
        if approval_path.exists():
            approval = load_operator_approval(approval_path)
            approval_password = os.environ.get(args.approval_password_env)
        decision = decide_command(
            command,
            policy=policy,
            cwd=args.cwd,
            workspace=args.workspace,
            operator_approval=approval,
            approval_password=approval_password,
            plan_sha256=approval.get("plan_sha256") if approval else None,
        )
        if args.record:
            record_security_event(decision, policy=policy)
    except Exception as exc:
        print(
            json.dumps(
                {"decision": "deny", "error_type": type(exc).__name__, "message": str(exc)},
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps(decision, ensure_ascii=True, sort_keys=True))
    return 0 if decision["decision"] == "allow" else 1


def _main_approve_plan(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Approve one persisted command plan with a password.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--approval-file", default=str(DEFAULT_OPERATOR_APPROVAL_PATH))
    parser.add_argument("--categories", nargs="+", required=True)
    parser.add_argument("--expires-hours", type=int, default=10)
    parser.add_argument("--password-env", default="SECURITY_APPROVAL_PASSWORD")
    args = parser.parse_args(argv)

    try:
        password = os.environ.get(args.password_env)
        if password is None:
            password = getpass.getpass("Operator approval password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise SecurityPolicyError("Password confirmation did not match")
        approval = create_operator_approval(
            plan_path=args.plan,
            workspace=args.workspace,
            categories=args.categories,
            password=password,
            expires_hours=args.expires_hours,
            approval_file=args.approval_file,
        )
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "error_type": type(exc).__name__, "message": str(exc)},
                ensure_ascii=True,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps({k: v for k, v in approval.items() if k != "password_hash"}, ensure_ascii=True, sort_keys=True))
    return 0


def _validate_category(name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SecurityPolicyError(f"Risk category must be an object: {name}")
    decision = value.get("decision")
    risk_level = value.get("risk_level")
    _expect_choice(decision, DECISIONS, f"RiskCategory.{name}.decision")
    _expect_choice(risk_level, RISK_LEVELS, f"RiskCategory.{name}.risk_level")
    activated = value.get("activated", True)
    if not isinstance(activated, bool):
        raise SecurityPolicyError(f"RiskCategory.{name}.activated must be a boolean")
    return {**value, "decision": decision, "risk_level": risk_level, "activated": activated}


def _apply_operator_approval(
    decision: dict[str, Any],
    *,
    operator_approval: dict[str, Any] | None,
    approval_password: str | None,
    plan_sha256: str | None,
    cwd: str | Path,
) -> dict[str, Any]:
    if decision["decision"] != "ask" or operator_approval is None:
        return decision
    ok, reason = _operator_approval_matches(
        operator_approval,
        password=approval_password,
        plan_sha256=plan_sha256,
        command=decision["command"],
        cwd=cwd,
        workspace=decision["workspace"],
        category=decision["category"],
    )
    if not ok:
        return {**decision, "operator_approval_reason": reason}
    return {
        **decision,
        "decision": "allow",
        "reason": "Operator approval grant matched approved plan command",
        "operator_approval_id": operator_approval["approval_id"],
        "operator_approval_reason": reason,
    }


def _operator_approval_matches(
    approval: dict[str, Any],
    *,
    password: str | None,
    plan_sha256: str | None,
    command: list[str],
    cwd: str | Path,
    workspace: str,
    category: str,
) -> tuple[bool, str]:
    validated = validate_operator_approval(approval)
    if password is None:
        return False, "No approval password provided"
    if not _password_matches(password, validated["password_hash"]):
        return False, "Approval password did not match"
    if _parse_utc_datetime(validated["expires_at"], "OperatorApproval.expires_at") < datetime.now(timezone.utc):
        return False, "Operator approval expired"
    if Path(validated["workspace"]).resolve() != Path(workspace).resolve():
        return False, "Operator approval workspace does not match"
    if plan_sha256 != validated["plan_sha256"]:
        return False, "Operator approval plan hash does not match"
    approved_categories = set(validated["approved_categories"])
    if "*" not in approved_categories and category not in approved_categories:
        return False, f"Operator approval does not include category: {category}"
    command_hash = command_fingerprint(command, cwd)
    if command_hash not in set(validated["approved_command_sha256"]):
        return False, "Command is not part of the approved plan"
    return True, "Password, plan hash, workspace, category and command fingerprint matched"


def command_fingerprint(command: list[str], cwd: str | Path) -> str:
    payload = {
        "command": command,
        "cwd": str(cwd),
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fingerprints_from_plan(plan_document: Any) -> list[str]:
    if not isinstance(plan_document, list) or not plan_document:
        raise SecurityPolicyError("Approved plan must be a non-empty list")
    fingerprints: list[str] = []
    for index, item in enumerate(plan_document):
        if not isinstance(item, dict):
            raise SecurityPolicyError(f"Plan item {index} must be an object")
        command = _normalize_command(item.get("command"))
        cwd = item.get("cwd", ".")
        if not isinstance(cwd, str) or not cwd:
            raise SecurityPolicyError(f"Plan item {index}.cwd must be a non-empty string")
        fingerprints.append(command_fingerprint(command, cwd))
    return fingerprints


def _classify_command(command: list[str]) -> str:
    executable = Path(command[0]).name
    if executable in {"bash", "sh"}:
        return "shell"
    if executable in {"curl", "wget", "ssh", "scp"}:
        return "network"
    if executable == "npm" and len(command) > 1 and command[1] in {"install", "add", "publish"}:
        return "network"
    if executable in {"rm", "rmdir"}:
        return "delete"
    if executable in {"chmod", "chown", "sudo"}:
        return "permissions"
    if executable in {"kill", "pkill", "pgrep", "ps"}:
        return "processes"
    if executable == "docker":
        return "docker"
    if executable in {"cat", "head", "tail", "wc", "rg", "sed", "find", "ls", "date"}:
        return "read"
    if executable in {"python", "python3"} or executable.endswith("python"):
        return "test_or_build"
    if executable in {"pytest", "ruff", "mypy"}:
        return "test_or_build"
    if executable in {"node", "npx"}:
        return "test_or_build"
    if executable == "npm" and len(command) > 1 and command[1] == "run":
        return "test_or_build"
    return "unknown"


def _normalize_command(value: Any) -> list[str]:
    if isinstance(value, str):
        value = shlex_split(value)
    if not isinstance(value, list) or not value:
        raise SecurityPolicyError("Command must be a non-empty string or list")
    normalized: list[str] = []
    for index, part in enumerate(value):
        if not isinstance(part, str) or not part:
            raise SecurityPolicyError(f"Command part {index} must be a non-empty string")
        if "\x00" in part:
            raise SecurityPolicyError("Command parts must not contain NUL bytes")
        normalized.append(part)
    return normalized


def _normalize_categories(values: Any) -> list[str]:
    if not isinstance(values, list) or not values:
        raise SecurityPolicyError("approved categories must be a non-empty list")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise SecurityPolicyError("approved categories must be non-empty strings")
        normalized.append(value.strip())
    return sorted(set(normalized))


def _match_prefix(command: list[str], prefixes: list[list[str]]) -> list[str] | None:
    for prefix in prefixes:
        if len(command) >= len(prefix) and command[: len(prefix)] == prefix:
            return prefix
    return None


def _expect_choice(value: Any, choices: frozenset[str], label: str) -> None:
    if value not in choices:
        raise SecurityPolicyError(f"{label} must be one of: {', '.join(sorted(choices))}")


def _validate_password_hash(value: Any) -> None:
    if not isinstance(value, dict):
        raise SecurityPolicyError("OperatorApproval.password_hash must be an object")
    if value.get("algorithm") != "pbkdf2_sha256":
        raise SecurityPolicyError("OperatorApproval.password_hash.algorithm must be pbkdf2_sha256")
    iterations = value.get("iterations")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 100000:
        raise SecurityPolicyError("OperatorApproval.password_hash.iterations must be >= 100000")
    if not isinstance(value.get("salt"), str) or not value["salt"]:
        raise SecurityPolicyError("OperatorApproval.password_hash.salt must be a non-empty string")
    if not isinstance(value.get("hash"), str) or not value["hash"]:
        raise SecurityPolicyError("OperatorApproval.password_hash.hash must be a non-empty string")


def _hash_password(password: str, salt_hex: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    ).hex()


def _password_matches(password: str, password_hash: dict[str, Any]) -> bool:
    candidate = _hash_password(password, password_hash["salt"], password_hash["iterations"])
    return hmac.compare_digest(candidate, password_hash["hash"])


def _expect_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise SecurityPolicyError(f"{label} must be a SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise SecurityPolicyError(f"{label} must be a SHA-256 hex string") from exc


def _parse_utc_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SecurityPolicyError(f"{label} must be a non-empty datetime string")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise SecurityPolicyError(f"{label} must be ISO 8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)


def _format_command(command: list[str]) -> str:
    return " ".join(command)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
