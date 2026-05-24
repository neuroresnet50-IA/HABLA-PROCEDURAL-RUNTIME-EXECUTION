"""Email command plane for HABLA runtime.

This module turns trusted inbound emails into persisted project commands. It is
intentionally separate from the control plane: email is only another ingress
channel, and execution still goes through the existing runtime session API.
"""

from __future__ import annotations

import hashlib
import email
import imaplib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from typing import Any


VALID_RUNTIME_MODES = {"smoke", "build", "medium", "long-run"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    return re.sub(r"(^-+|-+$)", "", re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-"))


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _normalize_sender(sender: str) -> str:
    value = str(sender or "").strip().lower()
    match = re.search(r"<([^>]+)>", value)
    if match:
        value = match.group(1).strip()
    return value


def _extract_field(lines: list[str], names: set[str]) -> str:
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower()
        if normalized_key in names:
            return value.strip()
    return ""


def _extract_prompt(body: str) -> str:
    lines = str(body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    prompt_markers = {
        "prompt",
        "requerimiento",
        "requirement",
        "orden",
        "instruccion",
        "instruccion habla",
    }
    for index, line in enumerate(lines):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() in prompt_markers:
            tail = "\n".join(lines[index + 1 :]).strip()
            return "\n".join(part for part in [value.strip(), tail] if part).strip()

    filtered: list[str] = []
    for line in lines:
        key = line.split(":", 1)[0].strip().lower() if ":" in line else ""
        if key in {"proyecto", "project", "nombre", "modo", "mode", "accion", "action", "token"}:
            continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def _message_text(message: Message) -> str:
    if message.is_multipart():
        chunks: list[str] = []
        for part in message.walk():
            content_type = str(part.get_content_type() or "").lower()
            disposition = str(part.get("Content-Disposition") or "").lower()
            if content_type != "text/plain" or "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            chunks.append(payload.decode(charset, errors="replace"))
        return "\n".join(chunks).strip()

    payload = message.get_payload(decode=True)
    if payload is None:
        return str(message.get_payload() or "")
    return payload.decode(message.get_content_charset() or "utf-8", errors="replace")


@dataclass(frozen=True)
class EmailCommandConfig:
    enabled: bool = False
    subject_prefix: str = "[HABLA]"
    allowed_senders: tuple[str, ...] = field(default_factory=tuple)
    command_token: str = ""
    default_runtime_mode: str = "long-run"
    max_body_chars: int = 20000
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_mailbox: str = "INBOX"
    imap_ssl: bool = True


class EmailCommandPlane:
    """Persist and dispatch email-originated project commands."""

    def __init__(self, root: str | Path, config: EmailCommandConfig | None = None) -> None:
        self.root = Path(root)
        self.config = config or EmailCommandConfig()
        self.commands_path = self.root / "commands.json"
        self.events_path = self.root / "events.jsonl"
        self.state_path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def update_config(self, config: EmailCommandConfig) -> None:
        self.config = config

    def status(self) -> dict[str, Any]:
        commands = self.load_commands()
        counts: dict[str, int] = {}
        for command in commands:
            status = str(command.get("status") or "unknown")
            counts[status] = counts.get(status, 0) + 1
        return {
            "enabled": self.config.enabled,
            "subjectPrefix": self.config.subject_prefix,
            "allowedSenderCount": len(self.config.allowed_senders),
            "tokenRequired": bool(self.config.command_token),
            "imapConfigured": bool(self.config.imap_host and self.config.imap_username and self.config.imap_password),
            "runtimePath": str(self.root),
            "counts": counts,
            "latest": commands[-5:],
        }

    def public_config(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "subjectPrefix": self.config.subject_prefix,
            "allowedSenders": list(self.config.allowed_senders),
            "commandToken": self.config.command_token,
            "defaultRuntimeMode": self.config.default_runtime_mode,
            "maxBodyChars": self.config.max_body_chars,
            "imapHost": self.config.imap_host,
            "imapPort": self.config.imap_port,
            "imapUsername": self.config.imap_username,
            "imapMailbox": self.config.imap_mailbox,
            "imapSsl": self.config.imap_ssl,
            "hasImapPassword": bool(self.config.imap_password),
        }

    def poll_imap_once(self) -> dict[str, Any]:
        if not self.config.enabled:
            return {"ok": True, "status": "disabled", "imported": 0}
        if not (self.config.imap_host and self.config.imap_username and self.config.imap_password):
            return {"ok": True, "status": "imap_not_configured", "imported": 0}

        imported = 0
        rejected = 0
        duplicates = 0
        try:
            client_cls = imaplib.IMAP4_SSL if self.config.imap_ssl else imaplib.IMAP4
            client = client_cls(self.config.imap_host, int(self.config.imap_port or 993))
            try:
                client.login(self.config.imap_username, self.config.imap_password)
                client.select(self.config.imap_mailbox or "INBOX")
                _status, data = client.search(None, "UNSEEN")
                message_ids = data[0].split() if data and data[0] else []
                for raw_id in message_ids:
                    fetch_status, fetched = client.fetch(raw_id, "(RFC822)")
                    if fetch_status != "OK" or not fetched:
                        continue
                    raw_message = next((item[1] for item in fetched if isinstance(item, tuple) and len(item) > 1), None)
                    if not raw_message:
                        continue
                    message = email.message_from_bytes(raw_message)
                    result = self.ingest_email(
                        sender=str(message.get("From") or ""),
                        subject=str(message.get("Subject") or ""),
                        body=_message_text(message),
                        message_id=str(message.get("Message-ID") or raw_id.decode("ascii", errors="ignore")),
                        source="imap",
                        received_at=str(message.get("Date") or utc_now()),
                    )
                    if result.get("duplicate"):
                        duplicates += 1
                    elif result.get("ok"):
                        imported += 1
                    else:
                        rejected += 1
                    client.store(raw_id, "+FLAGS", "\\Seen")
            finally:
                try:
                    client.logout()
                except Exception:
                    pass
        except Exception as error:
            self._record_event({"type": "email_imap_poll_failed", "error": str(error)})
            return {"ok": False, "status": "imap_failed", "error": str(error), "imported": imported}

        if imported or rejected or duplicates:
            self._record_event(
                {
                    "type": "email_imap_poll_completed",
                    "imported": imported,
                    "rejected": rejected,
                    "duplicates": duplicates,
                }
            )
        return {"ok": True, "status": "imap_polled", "imported": imported, "rejected": rejected, "duplicates": duplicates}

    def load_commands(self) -> list[dict[str, Any]]:
        payload = read_json(self.commands_path, [])
        return payload if isinstance(payload, list) else []

    def save_commands(self, commands: list[dict[str, Any]]) -> None:
        write_json(self.commands_path, commands)

    def _state(self) -> dict[str, Any]:
        payload = read_json(self.state_path, {"processed_message_ids": []})
        return payload if isinstance(payload, dict) else {"processed_message_ids": []}

    def _save_state(self, state: dict[str, Any]) -> None:
        write_json(self.state_path, state)

    def _record_event(self, payload: dict[str, Any]) -> None:
        append_jsonl(self.events_path, {"timestamp": utc_now(), **payload})

    def ingest_email(
        self,
        *,
        sender: str,
        subject: str,
        body: str,
        message_id: str | None = None,
        source: str = "api",
        received_at: str | None = None,
    ) -> dict[str, Any]:
        message_id = str(message_id or "").strip() or self._fingerprint(sender, subject, body)
        state = self._state()
        processed = {str(item) for item in state.get("processed_message_ids", []) if item}
        if message_id in processed:
            return {"ok": True, "duplicate": True, "messageId": message_id, "status": "duplicate"}

        parsed = self.parse_email(sender=sender, subject=subject, body=body)
        if parsed.get("ok") is False:
            processed.add(message_id)
            state["processed_message_ids"] = sorted(processed)
            self._save_state(state)
            rejected = {
                "status": "rejected",
                "messageId": message_id,
                "sender": _normalize_sender(sender),
                "subject": str(subject or ""),
                "reason": parsed.get("error"),
                "source": source,
                "receivedAt": received_at or utc_now(),
            }
            self._record_event({"type": "email_command_rejected", **rejected})
            return {"ok": False, "error": parsed.get("error"), "command": rejected}

        command = {
            **parsed["command"],
            "id": self._fingerprint(message_id, parsed["command"]["projectName"], parsed["command"]["requirement"]),
            "messageId": message_id,
            "sender": _normalize_sender(sender),
            "source": source,
            "receivedAt": received_at or utc_now(),
            "status": "pending",
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
        }
        commands = self.load_commands()
        commands.append(command)
        self.save_commands(commands)
        processed.add(message_id)
        state["processed_message_ids"] = sorted(processed)
        self._save_state(state)
        self._record_event({"type": "email_command_received", "command": command})
        return {"ok": True, "command": command}

    def parse_email(self, *, sender: str, subject: str, body: str) -> dict[str, Any]:
        normalized_sender = _normalize_sender(sender)
        allowed = {_normalize_sender(value) for value in self.config.allowed_senders if str(value).strip()}
        if allowed and normalized_sender not in allowed:
            return {"ok": False, "error": "sender_not_allowed"}

        clean_subject = str(subject or "").strip()
        prefix = str(self.config.subject_prefix or "").strip()
        if prefix and not clean_subject.lower().startswith(prefix.lower()) and not clean_subject.lower().startswith("habla:"):
            return {"ok": False, "error": "missing_subject_prefix"}

        limited_body = str(body or "")[: max(100, int(self.config.max_body_chars or 20000))]
        if self.config.command_token:
            token = str(self.config.command_token)
            haystack = f"{clean_subject}\n{limited_body}"
            if f"HABLA-TOKEN:{token}" not in haystack and f"Token: {token}" not in haystack:
                return {"ok": False, "error": "missing_or_invalid_token"}

        lines = limited_body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        subject_tail = re.sub(r"^(\[habla\]|habla:)\s*", "", clean_subject, flags=re.IGNORECASE).strip(" -:")
        project_name = (
            _extract_field(lines, {"proyecto", "project", "nombre", "project name"})
            or subject_tail
            or f"correo-habla-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        runtime_mode = (_extract_field(lines, {"modo", "mode", "runtime mode"}) or self.config.default_runtime_mode).strip().lower()
        if runtime_mode not in VALID_RUNTIME_MODES:
            runtime_mode = self.config.default_runtime_mode if self.config.default_runtime_mode in VALID_RUNTIME_MODES else "long-run"

        action = (_extract_field(lines, {"accion", "action"}) or "new_project").strip().lower().replace("-", "_")
        if action not in {"new_project", "nuevo_proyecto", "iniciar_proyecto"}:
            return {"ok": False, "error": "unsupported_action"}

        requirement = _extract_prompt(limited_body)
        if not requirement:
            return {"ok": False, "error": "missing_requirement"}

        return {
            "ok": True,
            "command": {
                "action": "new_project",
                "projectName": project_name.strip(),
                "projectSlug": slugify(project_name),
                "requirement": requirement.strip(),
                "runtimeMode": runtime_mode,
                "ensureNewProject": True,
                "bootstrapProject": False,
            },
        }

    def next_pending(self) -> dict[str, Any] | None:
        for command in self.load_commands():
            if command.get("status") == "pending":
                return command
        return None

    def mark_command(self, command_id: str, status: str, **updates: Any) -> dict[str, Any] | None:
        commands = self.load_commands()
        updated: dict[str, Any] | None = None
        for command in commands:
            if command.get("id") != command_id:
                continue
            command.update({key: value for key, value in updates.items() if value is not None})
            command["status"] = status
            command["updatedAt"] = utc_now()
            updated = command
            break
        if updated is not None:
            self.save_commands(commands)
            self._record_event({"type": f"email_command_{status}", "command": updated})
        return updated

    @staticmethod
    def _fingerprint(*parts: str) -> str:
        digest = hashlib.sha256()
        for part in parts:
            digest.update(str(part or "").encode("utf-8", errors="replace"))
            digest.update(b"\0")
        return digest.hexdigest()[:24]
