import tempfile
import unittest
from pathlib import Path

from aegs.core import AEGSError, create_handoff, create_proposal, decide, initialise, verify, verify_ledger


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


if __name__ == "__main__":
    unittest.main()
