"""Executable contracts for critical documentation claims.

These tests intentionally bind exact public claims to observable behavior.  A
wording change needs a deliberate test update; an implementation change needs
an equally deliberate documentation decision.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aegs.core import AEGSError, create_handoff, create_proposal, initialise, takeover
from aegs.discovery import _is_sensitive
from aegs.journal import init_journal, verify_journal


REPOSITORY = Path(__file__).resolve().parents[1]


class DocumentationImplementationContracts(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        initialise(self.root, "owner@example.test")

    def tearDown(self):
        self.directory.cleanup()

    def assert_document_claim(self, relative_path: str, claim: str) -> None:
        text = (REPOSITORY / relative_path).read_text(encoding="utf-8")
        self.assertIn(claim, text, f"Document contract drift in {relative_path}: missing claim {claim!r}")

    def test_sensitive_filter_document_and_behavior_are_filename_suffix_only(self):
        claim = "敏感路径过滤只按文件名和后缀，不按父目录名过滤"
        self.assert_document_claim("docs/18-aep-sidecar-boundary-and-remediation.md", claim)
        self.assertFalse(_is_sensitive(Path("secrets/application.py")), "Implementation drift: parent directory name must not make code sensitive")
        self.assertTrue(_is_sensitive(Path("source/.env.production")), "Implementation drift: .env filename must remain sensitive")
        self.assertTrue(_is_sensitive(Path("source/private.key")), "Implementation drift: sensitive suffix must remain filtered")

    def test_journal_document_and_behavior_keep_jsonl_authoritative(self):
        self.assert_document_claim("docs/21-journal-mirror-verification.md", "`ledger.jsonl` remains the authoritative event ledger. SQLite is only a local")
        self.assert_document_claim("docs/21-journal-mirror-verification.md", "query mirror and never supplies missing evidence to the JSONL chain.")
        init_journal(self.root)
        report = verify_journal(self.root)
        self.assertEqual(report["status"], "PASS", "Implementation drift: fresh journal mirror must verify against JSONL")
        self.assertEqual(report["authority"], "ledger.jsonl", "Implementation drift: SQLite must not become the authority")

    def test_handoff_document_and_behavior_keep_self_binding(self):
        self.assert_document_claim("decisions/ADR-0007-handoff-integrity-and-fail-closed-writes.md", "Implementation rejects a tampered handoff self-binding during takeover.")
        create_handoff(self.root)
        current_path = self.root / ".aegs" / "current_handoff.json"
        handoff = json.loads(current_path.read_text(encoding="utf-8"))
        handoff["current_goal"] = "tampered"
        current_path.write_text(json.dumps(handoff), encoding="utf-8")
        result = takeover(self.root)
        self.assertEqual(result["status"], "STALE", "Implementation drift: a tampered handoff self-binding must fail takeover")
        self.assertTrue(any("self-hash" in reason for reason in result["reasons"]), "Implementation drift: takeover must diagnose the handoff self-hash")

    def test_high_risk_creation_expiry_document_and_behavior_match(self):
        claim = "YELLOW/RED Proposal 在创建期必须包含有时区且尚未过期的 `expires_at`"
        self.assert_document_claim("docs/18-aep-sidecar-boundary-and-remediation.md", claim)
        for risk in ("YELLOW", "RED"):
            with self.subTest(risk=risk, case="missing"):
                with self.assertRaisesRegex(AEGSError, "creation requires expires_at"):
                    create_proposal(self.root, "Missing expiry", risk, "agent")
            with self.subTest(risk=risk, case="naive"):
                with self.assertRaisesRegex(AEGSError, "include a timezone"):
                    create_proposal(self.root, "Naive expiry", risk, "agent", expires_at="2099-01-01T00:00:00")
            with self.subTest(risk=risk, case="expired"):
                with self.assertRaisesRegex(AEGSError, "must be in the future"):
                    create_proposal(self.root, "Expired expiry", risk, "agent", expires_at="2000-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
