from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # Windows uses the CRT byte-range locking API.
    import msvcrt
except ImportError:  # pragma: no cover - exercised on non-Windows platforms.
    msvcrt = None

try:  # POSIX fallback for contributors running the same repository elsewhere.
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows.
    fcntl = None


class AEGSError(RuntimeError):
    """Raised when a governance invariant is not satisfied."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def document_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AEGSError(f"Required governance file is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise AEGSError(f"Invalid JSON in governance file: {path}") from error


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_dir(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def governance_dir(root: Path) -> Path:
    return root / ".aegs"


def git_head(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _safe_filesystem_fingerprint(root: Path) -> str:
    """Content fingerprint for non-Git projects, excluding governance and likely secrets."""
    excluded_directories = {".git", ".aegs", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
    sensitive_suffixes = {".pem", ".key", ".p12", ".pfx"}
    entries: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in excluded_directories for part in path.relative_to(root).parts):
            continue
        name = path.name.lower()
        if name.startswith(".env") or name in {"secrets", "credentials", "id_rsa", "id_ed25519"} or path.suffix.lower() in sensitive_suffixes:
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append(f"{path.relative_to(root).as_posix()}:{digest}")
        except OSError:
            entries.append(f"{path.relative_to(root).as_posix()}:unreadable")
    return hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()


def code_fingerprint(root: Path) -> dict[str, Any]:
    """Hash Git-indexed project content while excluding AEGS's own runtime records."""
    tracked = subprocess.run(["git", "ls-files", "-s"], cwd=root, text=True, capture_output=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=False)
    if tracked.returncode != 0 or status.returncode != 0:
        return {"git_available": False, "head": None, "tracked_content_hash": _safe_filesystem_fingerprint(root), "dirty_non_governance": False, "source": "filesystem_safe_hash"}
    tracked_lines = [line for line in tracked.stdout.splitlines() if "\t.aegs/" not in line]
    dirty_lines = [line for line in status.stdout.splitlines() if ".aegs/" not in line.replace("\\", "/")]
    return {
        "git_available": True,
        "head": git_head(root),
        "tracked_content_hash": hashlib.sha256("\n".join(tracked_lines).encode("utf-8")).hexdigest(),
        "dirty_non_governance": bool(dirty_lines),
        "source": "git_index",
    }


def same_code_fingerprint(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    """Compare project content, not Git commits that changed only `.aegs` evidence artifacts."""
    if not left or not right:
        return False
    keys = ("git_available", "tracked_content_hash", "dirty_non_governance")
    return all(left.get(key) == right.get(key) for key in keys)


def ledger_head(root: Path) -> str | None:
    ledger = governance_dir(root) / "ledger.jsonl"
    if not ledger.exists():
        return None
    lines = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    return json.loads(lines[-1]).get("event_hash") if lines else None


@contextmanager
def ledger_write_lock(root: Path, timeout_seconds: float = 2.0, poll_interval_seconds: float = 0.02):
    """Acquire the cooperative, process-wide lock for a JSONL ledger append.

    The lock file is intentionally separate from the ledger so that the ledger
    remains an ordinary JSONL hash chain.  Callers either own the lock before
    deriving ``previous_hash`` and writing, or receive an error without an
    append.  It is a local-host safety boundary, not distributed consensus.
    """
    if timeout_seconds < 0 or poll_interval_seconds <= 0:
        raise AEGSError("Ledger lock timeout must be non-negative and polling interval positive.")
    lock_path = governance_dir(root) / "ledger.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        acquired = False
        while not acquired:
            try:
                handle.seek(0)
                if msvcrt is not None:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                elif fcntl is not None:  # pragma: no cover - non-Windows fallback.
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:  # pragma: no cover - unsupported Python platform.
                    raise AEGSError("No supported process-level file-locking backend is available.")
                acquired = True
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise AEGSError(f"Timed out waiting for ledger writer lock after {timeout_seconds:.2f} seconds.") from error
                time.sleep(poll_interval_seconds)
        try:
            yield
        finally:
            handle.seek(0)
            if msvcrt is not None:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            elif fcntl is not None:  # pragma: no cover - non-Windows fallback.
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_event(root: Path, event_type: str, payload: dict[str, Any], lock_timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Append one durable event while preserving the JSONL hash chain."""
    ledger = governance_dir(root) / "ledger.jsonl"
    with ledger_write_lock(root, timeout_seconds=lock_timeout_seconds):
        previous_hash = "GENESIS"
        if ledger.exists():
            lines = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                previous_hash = json.loads(lines[-1])["event_hash"]
        event = {
            "event_id": f"EV-{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "occurred_at": now_utc(),
            "previous_hash": previous_hash,
            "payload": payload,
        }
        event["event_hash"] = document_hash(event)
        with ledger.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event


def verify_ledger(root: Path) -> tuple[bool, str, int]:
    ledger = governance_dir(root) / "ledger.jsonl"
    if not ledger.exists():
        return False, "ledger is missing", 0
    expected_previous = "GENESIS"
    count = 0
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            recorded_hash = event.pop("event_hash")
        except (json.JSONDecodeError, KeyError):
            return False, f"malformed event at line {number}", count
        calculated_hash = document_hash(event)
        if event.get("previous_hash") != expected_previous:
            return False, f"broken previous_hash at line {number}", count
        if recorded_hash != calculated_hash:
            return False, f"invalid event_hash at line {number}", count
        expected_previous = recorded_hash
        count += 1
    return True, "ok", count


def initialise(root_value: str | Path, owner: str) -> dict[str, Any]:
    root = project_dir(root_value)
    if not root.exists() or not root.is_dir():
        raise AEGSError(f"Project directory does not exist: {root}")
    aegs = governance_dir(root)
    if aegs.exists():
        raise AEGSError(f"Governance package already exists: {aegs}")
    for name in ("proposals", "directives", "handoffs", "experiments", "evaluations"):
        (aegs / name).mkdir(parents=True, exist_ok=True)
    charter = {
        "schema_version": "0.1",
        "project_id": root.name,
        "charter_version": "0.1.0",
        "owners": [owner],
        "purpose": "Define before enabling autonomous actions.",
        "allowed_actions": ["read", "propose", "sandbox_experiment"],
        "forbidden_actions": ["credential_access", "production_write", "charter_self_modification"],
        "approval_policy": {
            "GREEN": "owner may approve; sandbox only",
            "YELLOW": "owner plus evidence and rollback reference required",
            "RED": "manual owner approval and independent review required",
        },
    }
    state = {
        "schema_version": "0.1",
        "project_id": root.name,
        "charter_version": charter["charter_version"],
        "current_goal": "Set the project purpose and create the first governed proposal.",
        "verified_facts": [],
        "unverified_claims": [],
        "open_risks": [],
        "safe_next_actions": ["Run 'aegs verify .'", "Create a GREEN proposal for a sandbox experiment."],
        "current_git_head": git_head(root),
        "architecture_snapshot": None,
        "unresolved_questions": [],
    }
    write_json(aegs / "charter.json", charter)
    write_json(aegs / "state.json", state)
    event = append_event(root, "governance.initialised", {"owner": owner, "charter_version": "0.1.0"})
    return {"root": str(root), "event_id": event["event_id"]}


def verify(root_value: str | Path) -> dict[str, Any]:
    root = project_dir(root_value)
    charter = read_json(governance_dir(root) / "charter.json")
    state = read_json(governance_dir(root) / "state.json")
    ledger_ok, ledger_message, event_count = verify_ledger(root)
    errors: list[str] = []
    if not charter.get("owners"):
        errors.append("charter must name at least one owner")
    if state.get("charter_version") != charter.get("charter_version"):
        errors.append("state charter_version does not match charter")
    if not ledger_ok:
        errors.append(ledger_message)
    return {
        "ok": not errors,
        "root": str(root),
        "git_head": git_head(root),
        "ledger_events": event_count,
        "ledger_status": ledger_message,
        "errors": errors,
    }


def require_valid_governance(root: Path) -> None:
    check = verify(root)
    if not check["ok"]:
        raise AEGSError("Governance verification failed; write operation blocked: " + "; ".join(check["errors"]))


def _parse_expiry(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise AEGSError("expires_at must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise AEGSError("expires_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def create_proposal(
    root_value: str | Path,
    title: str,
    risk: str,
    proposer: str,
    scope: str = "",
    alternatives: str = "",
    impact: str = "",
    counter_evidence: str = "",
    acceptance_criteria: str = "",
    expires_at: str | None = None,
) -> dict[str, Any]:
    root = project_dir(root_value)
    check = verify(root)
    if not check["ok"]:
        raise AEGSError("Cannot create proposal while governance verification fails: " + "; ".join(check["errors"]))
    risk = risk.upper()
    if risk not in {"GREEN", "YELLOW", "RED"}:
        raise AEGSError("risk must be GREEN, YELLOW, or RED")
    parsed_expiry = _parse_expiry(expires_at) if expires_at else None
    if risk in {"YELLOW", "RED"}:
        if not parsed_expiry:
            raise AEGSError("YELLOW/RED proposal creation requires expires_at with a timezone")
        if parsed_expiry <= datetime.now(timezone.utc):
            raise AEGSError("YELLOW/RED proposal expires_at must be in the future")
    proposal_id = f"PR-{uuid.uuid4().hex[:12]}"
    proposal = {
        "proposal_id": proposal_id,
        "status": "DRAFT",
        "title": title,
        "risk": risk,
        "proposer": proposer,
        "created_at": now_utc(),
        "baseline_git_head": git_head(root),
        "scope": scope,
        "alternatives": alternatives,
        "impact": impact,
        "counter_evidence": counter_evidence,
        "acceptance_criteria": acceptance_criteria,
        "expires_at": expires_at,
        "evidence_refs": [],
        "rollback_reference": None,
        "decision": None,
    }
    write_json(governance_dir(root) / "proposals" / f"{proposal_id}.json", proposal)
    append_event(root, "proposal.created", {"proposal_id": proposal_id, "risk": risk, "proposer": proposer, "scope": scope})
    return proposal


def decide(
    root_value: str | Path,
    proposal_id: str,
    action: str,
    approver: str,
    evidence: str | None,
    rollback: str | None,
    reason: str | None = None,
) -> dict[str, Any]:
    root = project_dir(root_value)
    require_valid_governance(root)
    charter = read_json(governance_dir(root) / "charter.json")
    if approver not in charter.get("owners", []):
        raise AEGSError("Only a named project owner may record a human decision in this prototype")
    proposal_path = governance_dir(root) / "proposals" / f"{proposal_id}.json"
    proposal = read_json(proposal_path)
    action = action.upper()
    if action not in {"APPROVE", "REJECT", "DEFER", "HOLD"}:
        raise AEGSError("action must be APPROVE, REJECT, DEFER, or HOLD")
    if proposal["status"] != "DRAFT":
        raise AEGSError("Only DRAFT proposals may receive an initial decision")
    if action == "APPROVE" and proposal["risk"] in {"YELLOW", "RED"}:
        required_fields = ("scope", "alternatives", "impact", "counter_evidence", "acceptance_criteria", "expires_at")
        missing_fields = [field for field in required_fields if not proposal.get(field)]
        if missing_fields:
            raise AEGSError("YELLOW/RED approval requires structured proposal fields: " + ", ".join(missing_fields))
        if not evidence or not rollback or not reason:
            raise AEGSError("YELLOW/RED approval requires evidence, rollback, and decision reason")
        if _parse_expiry(proposal["expires_at"]) <= datetime.now(timezone.utc):
            raise AEGSError("YELLOW/RED proposal has expired and cannot be approved")
    directive_id = f"HD-{uuid.uuid4().hex[:12]}"
    directive = {
        "directive_id": directive_id,
        "kind": "decision",
        "scope": "project",
        "proposal_id": proposal_id,
        "action": action,
        "approver": approver,
        "evidence": evidence,
        "rollback_reference": rollback,
        "reason": reason,
        "created_at": now_utc(),
    }
    write_json(governance_dir(root) / "directives" / f"{directive_id}.json", directive)
    proposal["status"] = "APPROVED" if action == "APPROVE" else action
    proposal["evidence_refs"] = [evidence] if evidence else []
    proposal["rollback_reference"] = rollback
    proposal["decision"] = directive_id
    write_json(proposal_path, proposal)
    append_event(root, "human.decision.recorded", {"proposal_id": proposal_id, "directive_id": directive_id, "action": action, "approver": approver, "reason": reason})
    return directive


def create_handoff(root_value: str | Path) -> dict[str, Any]:
    root = project_dir(root_value)
    check = verify(root)
    if not check["ok"]:
        raise AEGSError("Cannot create handoff while verification fails: " + "; ".join(check["errors"]))
    state = read_json(governance_dir(root) / "state.json")
    handoff_id = f"HO-{uuid.uuid4().hex[:12]}"
    snapshot_id = state.get("architecture_snapshot")
    snapshot = None
    if snapshot_id:
        snapshot = read_json(governance_dir(root) / "architecture" / f"{snapshot_id}.json")
    current_fingerprint = code_fingerprint(root)
    state["current_git_head"] = current_fingerprint.get("head")
    state["current_code_fingerprint"] = current_fingerprint
    write_json(governance_dir(root) / "state.json", state)
    handoff = {
        "handoff_id": handoff_id,
        "created_at": now_utc(),
        "project_id": state["project_id"],
        "charter_version": state["charter_version"],
        "verified_facts": state.get("verified_facts", []),
        "unverified_claims": state.get("unverified_claims", []),
        "current_goal": state.get("current_goal"),
        "open_risks": state.get("open_risks", []),
        "architecture_snapshot": snapshot_id,
        "unresolved_questions": state.get("unresolved_questions", []),
        "safe_next_actions": state.get("safe_next_actions", []),
        "verification": check,
        "state_binding": {
            "current_git_head": state["current_git_head"],
            "current_code_fingerprint": state["current_code_fingerprint"],
        },
    }
    handoff["evidence_binding"] = {
        "code_fingerprint": code_fingerprint(root),
        "ledger_head_before_handoff": ledger_head(root),
        "architecture_snapshot_hash": document_hash(snapshot) if snapshot else None,
        "generated_at": now_utc(),
    }
    handoff["handoff_hash"] = document_hash(_handoff_hash_payload(handoff))
    handoff_event = append_event(root, "handoff.created", {"handoff_id": handoff_id, "handoff_hash": handoff["handoff_hash"], "architecture_snapshot": snapshot_id})
    handoff["evidence_binding"]["handoff_event_hash"] = handoff_event["event_hash"]
    write_json(governance_dir(root) / "handoffs" / f"{handoff_id}.json", handoff)
    write_json(governance_dir(root) / "current_handoff.json", handoff)
    markdown = "\n".join([
        "# AEGS Agent Handoff",
        "",
        f"- Handoff ID: `{handoff_id}`",
        f"- Project: `{handoff['project_id']}`",
        f"- Charter version: `{handoff['charter_version']}`",
        f"- Architecture snapshot: `{handoff['architecture_snapshot'] or 'not yet discovered'}`",
        "",
        "## Current goal",
        str(handoff["current_goal"] or "Not recorded."),
        "",
        "## Verified facts",
        *([f"- {fact}" for fact in handoff["verified_facts"]] or ["- None recorded."]),
        "",
        "## Unresolved questions",
        *([f"- {question}" for question in handoff["unresolved_questions"]] or ["- None recorded."]),
        "",
        "## Open risks",
        *([f"- {risk}" for risk in handoff["open_risks"]] or ["- None recorded."]),
        "",
        "## Safe next actions",
        *([f"- {action}" for action in handoff["safe_next_actions"]] or ["- Run `aegs verify .` before taking action."]),
        "",
        "This file is an entry point only. Verify the JSON handoff, Charter, Event Ledger and current Git state before acting.",
        "",
    ])
    (governance_dir(root) / "HANDOFF.md").write_text(markdown, encoding="utf-8", newline="\n")
    return handoff


def _handoff_hash_payload(handoff: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(canonical_json(handoff))
    payload.pop("handoff_hash", None)
    payload.get("evidence_binding", {}).pop("handoff_event_hash", None)
    return payload


def _find_handoff_event(root: Path, handoff_id: str, handoff_hash: str) -> dict[str, Any] | None:
    ledger = governance_dir(root) / "ledger.jsonl"
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        payload = event.get("payload", {})
        if event.get("event_type") == "handoff.created" and payload.get("handoff_id") == handoff_id and payload.get("handoff_hash") == handoff_hash:
            return event
    return None


def _state_handoff_drift(state: dict[str, Any], handoff: dict[str, Any]) -> list[str]:
    binding = handoff.get("state_binding")
    if not binding:
        return ["Handoff has no state binding; regenerate it."]
    reasons: list[str] = []
    if state.get("current_git_head") != binding.get("current_git_head"):
        reasons.append("State current_git_head differs from the handoff state binding.")
    if canonical_json(state.get("current_code_fingerprint")) != canonical_json(binding.get("current_code_fingerprint")):
        reasons.append("State current_code_fingerprint differs from the handoff state binding.")
    return reasons


def takeover(root_value: str | Path) -> dict[str, Any]:
    """Determine whether an Agent may safely proceed beyond read-only orientation."""
    root = project_dir(root_value)
    check = verify(root)
    if not check["ok"]:
        return {"status": "HOLD", "may_act": False, "reasons": check["errors"], "safe_next_actions": ["Repair or investigate governance verification before taking action."]}
    handoff_path = governance_dir(root) / "current_handoff.json"
    try:
        handoff = read_json(handoff_path)
    except AEGSError:
        return {"status": "STALE", "may_act": False, "reasons": ["No current handoff exists."], "safe_next_actions": ["Run 'aegs handoff <project>' after discovery and verification."]}
    binding = handoff.get("evidence_binding")
    if not binding:
        return {"status": "STALE", "may_act": False, "reasons": ["Handoff has no evidence binding; regenerate it."], "safe_next_actions": ["Run 'aegs handoff <project>'."]}
    reasons: list[str] = []
    state = read_json(governance_dir(root) / "state.json")
    reasons.extend(_state_handoff_drift(state, handoff))
    stored_path = governance_dir(root) / "handoffs" / f"{handoff.get('handoff_id')}.json"
    try:
        stored_handoff = read_json(stored_path)
        if canonical_json(stored_handoff) != canonical_json(handoff):
            reasons.append("Current handoff differs from its immutable handoff record.")
    except AEGSError:
        reasons.append("Referenced immutable handoff record is missing.")
    expected_handoff_hash = document_hash(_handoff_hash_payload(handoff))
    if handoff.get("handoff_hash") != expected_handoff_hash:
        reasons.append("Handoff self-hash is invalid.")
    handoff_event = _find_handoff_event(root, str(handoff.get("handoff_id")), str(handoff.get("handoff_hash")))
    if not handoff_event:
        reasons.append("No ledger event attests to this handoff hash.")
    else:
        if handoff_event.get("previous_hash") != binding.get("ledger_head_before_handoff"):
            reasons.append("Handoff ledger predecessor does not match its evidence binding.")
        if binding.get("handoff_event_hash") != handoff_event.get("event_hash") or ledger_head(root) != handoff_event.get("event_hash"):
            reasons.append("Event ledger changed after the handoff was generated.")
    if not binding.get("handoff_event_hash"):
        reasons.append("Event ledger changed after the handoff was generated.")
    if not same_code_fingerprint(binding.get("code_fingerprint"), code_fingerprint(root)):
        reasons.append("Project code fingerprint changed after the handoff was generated.")
    snapshot_id = handoff.get("architecture_snapshot")
    if snapshot_id:
        try:
            snapshot = read_json(governance_dir(root) / "architecture" / f"{snapshot_id}.json")
            if binding.get("architecture_snapshot_hash") != document_hash(snapshot):
                reasons.append("Architecture snapshot content changed after the handoff was generated.")
        except AEGSError:
            reasons.append("Referenced architecture snapshot is missing.")
    elif binding.get("architecture_snapshot_hash") is not None:
        reasons.append("Handoff snapshot binding is inconsistent.")
    if code_fingerprint(root).get("dirty_non_governance"):
        reasons.append("Project has uncommitted non-governance changes.")
    if reasons:
        return {
            "status": "STALE",
            "may_act": False,
            "reasons": reasons,
            "safe_next_actions": ["Run 'aegs discover <project>' if architecture-relevant content changed.", "Run 'aegs handoff <project>' after verification; obtain human direction before non-read-only work."],
        }
    return {
        "status": "PASS",
        "may_act": True,
        "reasons": [],
        "safe_next_actions": ["Proceed only within Charter permissions and create a governed proposal before changing project behavior."],
        "handoff_id": handoff.get("handoff_id"),
    }


def doctor(root_value: str | Path) -> dict[str, Any]:
    """Run non-mutating readiness checks before an Agent is allowed to take over."""
    root = project_dir(root_value)
    verification = verify(root)
    checks = [{"name": "governance_verification", "status": "PASS" if verification["ok"] else "HOLD", "detail": verification["ledger_status"] if verification["ok"] else "; ".join(verification["errors"])}]
    if verification["ok"]:
        gate = takeover(root)
        checks.append({"name": "takeover_gate", "status": gate["status"], "detail": "; ".join(gate["reasons"]) or "Fresh evidence binding."})
    else:
        gate = {"status": "HOLD", "safe_next_actions": ["Repair governance verification first."]}
    state = read_json(governance_dir(root) / "state.json") if verification["ok"] else {}
    snapshot_id = state.get("architecture_snapshot")
    snapshot_path = governance_dir(root) / "architecture" / f"{snapshot_id}.json" if snapshot_id else None
    snapshot_status = "PASS" if snapshot_path and snapshot_path.exists() else "STALE"
    checks.append({"name": "architecture_snapshot", "status": snapshot_status, "detail": snapshot_id or "No current architecture snapshot."})
    if verification["ok"]:
        try:
            handoff = read_json(governance_dir(root) / "current_handoff.json")
            state_reasons = _state_handoff_drift(state, handoff)
            checks.append({"name": "state_handoff_alignment", "status": "PASS" if not state_reasons else "STALE", "detail": "; ".join(state_reasons) or "State and handoff bindings align."})
        except AEGSError as error:
            checks.append({"name": "state_handoff_alignment", "status": "STALE", "detail": str(error)})
    overall = "HOLD" if any(check["status"] == "HOLD" for check in checks) else ("STALE" if any(check["status"] == "STALE" for check in checks) else "PASS")
    return {"status": overall, "project": str(root), "checks": checks, "safe_next_actions": gate["safe_next_actions"]}


def list_proposals(root_value: str | Path) -> list[dict[str, Any]]:
    root = project_dir(root_value)
    directory = governance_dir(root) / "proposals"
    if not directory.exists():
        return []
    proposals = [read_json(path) for path in directory.glob("PR-*.json")]
    return sorted(proposals, key=lambda item: item.get("created_at", ""), reverse=True)


def record_feedback(
    root_value: str | Path,
    author: str,
    kind: str,
    scope: str,
    duration: str,
    confidence: str,
    source_text: str,
    confirmed: bool,
) -> dict[str, Any]:
    root = project_dir(root_value)
    require_valid_governance(root)
    charter = read_json(governance_dir(root) / "charter.json")
    allowed_kinds = {"preference", "constraint", "fact_correction", "hypothesis"}
    allowed_scopes = {"task", "project", "project_group", "global_candidate"}
    allowed_durations = {"once", "task_end", "expires_at", "persistent"}
    allowed_confidence = {"certain", "preference", "exploratory"}
    if kind not in allowed_kinds or scope not in allowed_scopes or duration not in allowed_durations or confidence not in allowed_confidence:
        raise AEGSError("Feedback contains an unsupported governance classification")
    if not confirmed:
        raise AEGSError("Feedback must be explicitly confirmed before it becomes a governance directive")
    if kind == "constraint" and author not in charter.get("owners", []):
        raise AEGSError("Only a named owner may create a project constraint")
    directive_id = f"HD-{uuid.uuid4().hex[:12]}"
    directive = {
        "directive_id": directive_id,
        "kind": kind,
        "scope": scope,
        "duration": duration,
        "confidence": confidence,
        "author": author,
        "source_text": source_text,
        "normalized_effect": None,
        "confirmed": True,
        "created_at": now_utc(),
    }
    write_json(governance_dir(root) / "directives" / f"{directive_id}.json", directive)
    append_event(root, "human.feedback.recorded", {"directive_id": directive_id, "kind": kind, "scope": scope, "author": author})
    return directive
