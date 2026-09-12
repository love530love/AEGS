from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AEGSError(RuntimeError):
    """Raised when a governance invariant is not satisfied."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


def append_event(root: Path, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    ledger = governance_dir(root) / "ledger.jsonl"
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
    event["event_hash"] = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
    with ledger.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(event) + "\n")
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
        calculated_hash = hashlib.sha256(canonical_json(event).encode("utf-8")).hexdigest()
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


def create_proposal(root_value: str | Path, title: str, risk: str, proposer: str) -> dict[str, Any]:
    root = project_dir(root_value)
    check = verify(root)
    if not check["ok"]:
        raise AEGSError("Cannot create proposal while governance verification fails: " + "; ".join(check["errors"]))
    risk = risk.upper()
    if risk not in {"GREEN", "YELLOW", "RED"}:
        raise AEGSError("risk must be GREEN, YELLOW, or RED")
    proposal_id = f"PR-{uuid.uuid4().hex[:12]}"
    proposal = {
        "proposal_id": proposal_id,
        "status": "DRAFT",
        "title": title,
        "risk": risk,
        "proposer": proposer,
        "created_at": now_utc(),
        "baseline_git_head": git_head(root),
        "evidence_refs": [],
        "rollback_reference": None,
        "decision": None,
    }
    write_json(governance_dir(root) / "proposals" / f"{proposal_id}.json", proposal)
    append_event(root, "proposal.created", {"proposal_id": proposal_id, "risk": risk, "proposer": proposer})
    return proposal


def decide(root_value: str | Path, proposal_id: str, action: str, approver: str, evidence: str | None, rollback: str | None) -> dict[str, Any]:
    root = project_dir(root_value)
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
    if action == "APPROVE" and proposal["risk"] in {"YELLOW", "RED"} and (not evidence or not rollback):
        raise AEGSError("YELLOW/RED approval requires both evidence and rollback references")
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
        "created_at": now_utc(),
    }
    write_json(governance_dir(root) / "directives" / f"{directive_id}.json", directive)
    proposal["status"] = "APPROVED" if action == "APPROVE" else action
    proposal["evidence_refs"] = [evidence] if evidence else []
    proposal["rollback_reference"] = rollback
    proposal["decision"] = directive_id
    write_json(proposal_path, proposal)
    append_event(root, "human.decision.recorded", {"proposal_id": proposal_id, "directive_id": directive_id, "action": action, "approver": approver})
    return directive


def create_handoff(root_value: str | Path) -> dict[str, Any]:
    root = project_dir(root_value)
    check = verify(root)
    if not check["ok"]:
        raise AEGSError("Cannot create handoff while verification fails: " + "; ".join(check["errors"]))
    state = read_json(governance_dir(root) / "state.json")
    handoff_id = f"HO-{uuid.uuid4().hex[:12]}"
    handoff = {
        "handoff_id": handoff_id,
        "created_at": now_utc(),
        "project_id": state["project_id"],
        "charter_version": state["charter_version"],
        "verified_facts": state.get("verified_facts", []),
        "unverified_claims": state.get("unverified_claims", []),
        "current_goal": state.get("current_goal"),
        "open_risks": state.get("open_risks", []),
        "safe_next_actions": state.get("safe_next_actions", []),
        "verification": check,
    }
    write_json(governance_dir(root) / "handoffs" / f"{handoff_id}.json", handoff)
    write_json(governance_dir(root) / "current_handoff.json", handoff)
    append_event(root, "handoff.created", {"handoff_id": handoff_id})
    return handoff
