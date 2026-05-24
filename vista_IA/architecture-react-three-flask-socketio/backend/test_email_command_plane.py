import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from orchestrator.email_command_plane import EmailCommandConfig, EmailCommandPlane


class EmailCommandPlaneTest(unittest.TestCase):
    def test_accepts_authorized_habla_email(self):
        with TemporaryDirectory() as tmpdir:
            plane = EmailCommandPlane(
                Path(tmpdir),
                EmailCommandConfig(
                    allowed_senders=("owner@example.com",),
                    subject_prefix="[HABLA]",
                    command_token="secret",
                ),
            )

            result = plane.ingest_email(
                sender="Owner <owner@example.com>",
                subject="[HABLA] Plataforma Operativa",
                body=(
                    "Token: secret\n"
                    "Proyecto: Plataforma Operativa\n"
                    "Modo: long-run\n"
                    "Prompt:\n"
                    "Construye una plataforma con frontend, backend y pruebas."
                ),
                message_id="mail-1",
            )

            self.assertTrue(result["ok"])
            command = result["command"]
            self.assertEqual(command["projectName"], "Plataforma Operativa")
            self.assertEqual(command["projectSlug"], "plataforma-operativa")
            self.assertEqual(command["runtimeMode"], "long-run")
            self.assertIn("frontend", command["requirement"])
            self.assertEqual(plane.next_pending()["id"], command["id"])

    def test_rejects_sender_outside_allowlist(self):
        with TemporaryDirectory() as tmpdir:
            plane = EmailCommandPlane(
                Path(tmpdir),
                EmailCommandConfig(allowed_senders=("owner@example.com",), subject_prefix="[HABLA]"),
            )

            result = plane.ingest_email(
                sender="intruso@example.com",
                subject="[HABLA] Proyecto",
                body="Prompt:\nHaz algo",
                message_id="mail-2",
            )

            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "sender_not_allowed")
            self.assertIsNone(plane.next_pending())

    def test_deduplicates_message_id(self):
        with TemporaryDirectory() as tmpdir:
            plane = EmailCommandPlane(Path(tmpdir), EmailCommandConfig(subject_prefix="[HABLA]"))
            first = plane.ingest_email(
                sender="owner@example.com",
                subject="[HABLA] Proyecto",
                body="Prompt:\nHaz algo verificable",
                message_id="same-mail",
            )
            second = plane.ingest_email(
                sender="owner@example.com",
                subject="[HABLA] Proyecto",
                body="Prompt:\nHaz algo verificable",
                message_id="same-mail",
            )

            self.assertTrue(first["ok"])
            self.assertTrue(second["duplicate"])
            self.assertEqual(len(plane.load_commands()), 1)

    def test_mark_command_updates_persisted_status(self):
        with TemporaryDirectory() as tmpdir:
            plane = EmailCommandPlane(Path(tmpdir), EmailCommandConfig(subject_prefix="[HABLA]"))
            result = plane.ingest_email(
                sender="owner@example.com",
                subject="[HABLA] Proyecto",
                body="Prompt:\nHaz algo verificable",
                message_id="mail-3",
            )

            updated = plane.mark_command(result["command"]["id"], "started", sessionId="agent-1")

            self.assertEqual(updated["status"], "started")
            self.assertEqual(updated["sessionId"], "agent-1")
            self.assertIsNone(plane.next_pending())

    def test_imap_poll_is_disabled_without_config(self):
        with TemporaryDirectory() as tmpdir:
            plane = EmailCommandPlane(Path(tmpdir), EmailCommandConfig(enabled=False))

            result = plane.poll_imap_once()

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "disabled")


if __name__ == "__main__":
    unittest.main()
