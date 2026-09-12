import tempfile
import unittest
from pathlib import Path

from aegs.core import AEGSError, create_handoff, create_proposal, decide, initialise, record_feedback, verify, verify_ledger
from aegs.discovery import discover


class GovernanceCoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        initialise(self.root, "owner@example.test")

    def tearDown(self):
        self.directory.cleanup()

    def test_initialisation_verifies_and_creates_handoff(self):
        self.assertTrue(verify(self.root)["ok"])
        handoff = create_handoff(self.root)
        self.assertTrue(handoff["verification"]["ok"])
        self.assertTrue((self.root / ".aegs" / "current_handoff.json").exists())

    def test_yellow_approval_requires_evidence_and_rollback(self):
        proposal = create_proposal(self.root, "Test candidate", "YELLOW", "agent")
        with self.assertRaises(AEGSError):
            decide(self.root, proposal["proposal_id"], "APPROVE", "owner@example.test", None, None)
        directive = decide(self.root, proposal["proposal_id"], "APPROVE", "owner@example.test", "EXP-1", "v0.1")
        self.assertEqual(directive["action"], "APPROVE")

    def test_ledger_tampering_is_detected(self):
        ledger = self.root / ".aegs" / "ledger.jsonl"
        ledger.write_text(ledger.read_text(encoding="utf-8").replace("governance.initialised", "tampered"), encoding="utf-8")
        ok, _, _ = verify_ledger(self.root)
        self.assertFalse(ok)

    def test_constraint_feedback_requires_confirmation_and_owner(self):
        with self.assertRaises(AEGSError):
            record_feedback(self.root, "owner@example.test", "constraint", "project", "persistent", "certain", "Require review", False)
        with self.assertRaises(AEGSError):
            record_feedback(self.root, "visitor", "constraint", "project", "persistent", "certain", "Require review", True)
        directive = record_feedback(self.root, "owner@example.test", "constraint", "project", "persistent", "certain", "Require review", True)
        self.assertEqual(directive["kind"], "constraint")

    def test_discovery_creates_architecture_snapshot_and_handoff(self):
        (self.root / "app.py").write_text("from services.api import client\n", encoding="utf-8")
        (self.root / "requirements.txt").write_text("example==1\n", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=do-not-read\n", encoding="utf-8")
        snapshot = discover(self.root)
        self.assertEqual(snapshot["discovery_mode"], "read_only")
        self.assertIsNone(snapshot["working_tree_dirty"])
        self.assertEqual(snapshot["category_counts"]["dependency_manifest"], 1)
        self.assertEqual(snapshot["excluded_sensitive_file_count"], 1)
        self.assertEqual(snapshot["relationships"][0]["confidence"], "inferred")
        handoff = create_handoff(self.root)
        self.assertEqual(handoff["architecture_snapshot"], snapshot["snapshot_id"])
        self.assertIn(snapshot["snapshot_id"], handoff["verified_facts"][0])
        self.assertTrue((self.root / ".aegs" / "HANDOFF.md").exists())


if __name__ == "__main__":
    unittest.main()
