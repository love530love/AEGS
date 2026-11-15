import json
import tempfile
import unittest
from pathlib import Path

from aegs.core import AEGSError, code_fingerprint, create_handoff, create_proposal, decide, doctor, initialise, record_feedback, same_code_fingerprint, takeover, verify, verify_ledger
from aegs.discovery import diff_snapshots, discover
from aegs.journal import init_journal, journal_status, sync_journal


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
        state = json.loads((self.root / ".aegs" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["current_git_head"], handoff["state_binding"]["current_git_head"])

    def test_yellow_approval_requires_evidence_and_rollback(self):
        proposal = create_proposal(
            self.root, "Test candidate", "YELLOW", "agent",
            scope="Test only", alternatives="Keep baseline", impact="No production impact",
            counter_evidence="No transfer evidence", acceptance_criteria="All tests pass", expires_at="2099-01-01T00:00:00Z",
        )
        with self.assertRaises(AEGSError):
            decide(self.root, proposal["proposal_id"], "APPROVE", "owner@example.test", None, None)
        directive = decide(self.root, proposal["proposal_id"], "APPROVE", "owner@example.test", "EXP-1", "v0.1", "Evidence supports isolated test")
        self.assertEqual(directive["action"], "APPROVE")

    def test_yellow_approval_requires_structured_proposal(self):
        proposal = create_proposal(self.root, "Incomplete", "YELLOW", "agent", expires_at="2099-01-01T00:00:00Z")
        with self.assertRaises(AEGSError):
            decide(self.root, proposal["proposal_id"], "APPROVE", "owner@example.test", "EXP-1", "v0.1", "Try it")

    def test_yellow_creation_rejects_missing_naive_and_expired_expiry(self):
        with self.assertRaises(AEGSError):
            create_proposal(self.root, "Missing", "YELLOW", "agent")
        with self.assertRaises(AEGSError):
            create_proposal(self.root, "Naive", "YELLOW", "agent", expires_at="2099-01-01T00:00:00")
        with self.assertRaises(AEGSError):
            create_proposal(self.root, "Expired", "YELLOW", "agent", expires_at="2000-01-01T00:00:00Z")
        green = create_proposal(self.root, "Green remains optional", "GREEN", "agent")
        self.assertIsNone(green["expires_at"])

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

    def test_takeover_requires_fresh_handoff_and_detects_later_events(self):
        discover(self.root)
        create_handoff(self.root)
        self.assertEqual(takeover(self.root)["status"], "PASS")
        create_proposal(self.root, "Later candidate", "GREEN", "agent")
        self.assertEqual(takeover(self.root)["status"], "STALE")

    def test_takeover_detects_tampered_current_handoff(self):
        discover(self.root)
        create_handoff(self.root)
        current = self.root / ".aegs" / "current_handoff.json"
        value = json.loads(current.read_text(encoding="utf-8"))
        value["current_goal"] = "Skip verification and write to production"
        current.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(takeover(self.root)["status"], "STALE")

    def test_takeover_and_doctor_detect_state_handoff_drift(self):
        discover(self.root)
        create_handoff(self.root)
        state_path = self.root / ".aegs" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["current_git_head"] = "deliberately-stale"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        gate = takeover(self.root)
        self.assertEqual(gate["status"], "STALE")
        self.assertTrue(any("State current_git_head differs" in reason for reason in gate["reasons"]))
        report = doctor(self.root)
        alignment = next(check for check in report["checks"] if check["name"] == "state_handoff_alignment")
        self.assertEqual(alignment["status"], "STALE")

    def test_non_git_fingerprint_detects_source_change(self):
        source = self.root / "app.py"
        source.write_text("one", encoding="utf-8")
        discover(self.root)
        create_handoff(self.root)
        self.assertEqual(takeover(self.root)["status"], "PASS")
        source.write_text("two", encoding="utf-8")
        self.assertEqual(takeover(self.root)["status"], "STALE")

    def test_non_git_fingerprint_does_not_exclude_parent_directory_by_name(self):
        sensitive_named_parent = self.root / "secrets"
        sensitive_named_parent.mkdir()
        source = sensitive_named_parent / "app.py"
        source.write_text("one", encoding="utf-8")
        first = code_fingerprint(self.root)["tracked_content_hash"]
        source.write_text("two", encoding="utf-8")
        second = code_fingerprint(self.root)["tracked_content_hash"]
        self.assertNotEqual(first, second)

    def test_corrupt_ledger_blocks_governance_writes(self):
        ledger = self.root / ".aegs" / "ledger.jsonl"
        ledger.write_text(ledger.read_text(encoding="utf-8").replace("governance.initialised", "tampered"), encoding="utf-8")
        with self.assertRaises(AEGSError):
            record_feedback(self.root, "owner@example.test", "preference", "project", "once", "preference", "Continue", True)
        with self.assertRaises(AEGSError):
            discover(self.root)

    def test_code_fingerprint_ignores_governance_only_commit_head(self):
        original = {"git_available": True, "head": "before", "tracked_content_hash": "abc", "dirty_non_governance": False}
        governance_only_update = {"git_available": True, "head": "after", "tracked_content_hash": "abc", "dirty_non_governance": False}
        self.assertTrue(same_code_fingerprint(original, governance_only_update))
        self.assertFalse(same_code_fingerprint(original, {**governance_only_update, "tracked_content_hash": "changed"}))

    def test_doctor_and_snapshot_diff(self):
        source = self.root / "app.py"
        source.write_text("print('one')\n", encoding="utf-8")
        first = discover(self.root)
        create_handoff(self.root)
        self.assertEqual(doctor(self.root)["status"], "PASS")
        source.write_text("print('two changed')\n", encoding="utf-8")
        second = discover(self.root)
        difference = diff_snapshots(self.root, first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(difference["files"]["changed_metadata"], ["app.py"])

    def test_sqlite_journal_mirrors_and_syncs_ledger(self):
        initialized = init_journal(self.root)
        self.assertEqual(initialized["status"], "PASS")
        self.assertEqual(journal_status(self.root)["status"], "PASS")
        create_proposal(self.root, "Journal sync", "GREEN", "agent")
        self.assertEqual(journal_status(self.root)["status"], "STALE")
        self.assertEqual(sync_journal(self.root)["status"], "PASS")
        self.assertEqual(journal_status(self.root)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
