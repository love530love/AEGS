"""Optional local ledger-head anchors for rollback visibility.

An anchor is deliberately only a locally auditable file.  It is not signed,
not remotely witnessed, and not proof that a privileged writer did not replace
both the ledger and the anchor.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import AEGSError, canonical_json, document_hash, governance_dir, now_utc, project_dir, read_json, verify_ledger, write_json


SCHEMA = "aegs-local-ledger-anchor-v1"
STATE_KEY = "external_ledger_anchor_path"


def _path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _anchor_payload(anchor: dict[str, Any]) -> dict[str, Any]:
    return {key: anchor.get(key) for key in ("schema", "repo_root", "previous_anchor_head", "current_head", "observed_at")}


def _anchor_summary(anchor: dict[str, Any]) -> str:
    return document_hash(_anchor_payload(anchor))


def _read_anchor(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AEGSError(f"External ledger anchor is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise AEGSError(f"External ledger anchor is invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise AEGSError(f"External ledger anchor is not an object: {path}")
    return value


def _ledger_hashes(root: Path) -> list[str]:
    ledger = governance_dir(root) / "ledger.jsonl"
    return [json.loads(line)["event_hash"] for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


def _parse_timestamp(value: Any) -> bool:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def verify_external_anchor(root_value: str | Path, anchor_path: str | Path | None = None) -> dict[str, Any]:
    """Verify the configured (or explicit) local anchor without writing it."""
    root = project_dir(root_value)
    if anchor_path is None:
        try:
            state = read_json(governance_dir(root) / "state.json")
            configured = state.get(STATE_KEY)
        except AEGSError as error:
            return {"status": "HOLD", "reasons": [str(error)]}
        if not configured:
            return {"status": "SKIP", "reasons": ["No optional external ledger anchor is configured."]}
        anchor_path = configured
    path = _path(anchor_path)
    ledger_ok, message, count = verify_ledger(root)
    if not ledger_ok:
        return {"status": "HOLD", "path": str(path), "reasons": [f"Authoritative ledger is invalid: {message}"], "ledger_events": count}
    try:
        anchor = _read_anchor(path)
    except AEGSError as error:
        return {"status": "HOLD", "path": str(path), "reasons": [str(error)]}
    if anchor.get("schema") != SCHEMA:
        return {"status": "HOLD", "path": str(path), "reasons": ["External ledger anchor schema is invalid."]}
    if anchor.get("repo_root") != root.as_posix():
        return {"status": "HOLD", "path": str(path), "reasons": ["External ledger anchor belongs to a different repository root."]}
    if not _parse_timestamp(anchor.get("observed_at")):
        return {"status": "HOLD", "path": str(path), "reasons": ["External ledger anchor observed_at lacks a valid timezone."]}
    if anchor.get("summary") != _anchor_summary(anchor):
        return {"status": "HOLD", "path": str(path), "reasons": ["External ledger anchor summary does not match its recorded fields."]}
    hashes = _ledger_hashes(root)
    anchored_head = anchor.get("current_head")
    previous_head = anchor.get("previous_anchor_head")
    if not isinstance(anchored_head, str) or not anchored_head:
        return {"status": "HOLD", "path": str(path), "reasons": ["External ledger anchor has no current_head."]}
    if anchored_head not in hashes:
        return {"status": "HOLD", "path": str(path), "reasons": ["Anchored current_head is absent from the authoritative ledger; rollback or replacement is suspected."], "anchor_head": anchored_head, "ledger_head": hashes[-1] if hashes else None}
    if previous_head is not None:
        if not isinstance(previous_head, str) or previous_head not in hashes:
            return {"status": "HOLD", "path": str(path), "reasons": ["Anchor previous_anchor_head is absent from the authoritative ledger; anchor chain is broken."], "anchor_head": anchored_head}
        if hashes.index(previous_head) >= hashes.index(anchored_head):
            return {"status": "HOLD", "path": str(path), "reasons": ["Anchor previous_anchor_head does not precede current_head; anchor chain is broken."], "anchor_head": anchored_head}
    current_head = hashes[-1] if hashes else None
    if anchored_head != current_head:
        return {"status": "STALE", "path": str(path), "reasons": ["External ledger anchor is older than the authoritative ledger."], "previous_anchor_head": previous_head, "anchor_head": anchored_head, "ledger_head": current_head, "summary": anchor["summary"]}
    return {"status": "PASS", "path": str(path), "reasons": [], "previous_anchor_head": previous_head, "anchor_head": anchored_head, "ledger_head": current_head, "summary": anchor["summary"], "observed_at": anchor["observed_at"]}


def _write_anchor_atomic(path: Path, anchor: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(anchor, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_external_anchor(root_value: str | Path, anchor_path: str | Path) -> dict[str, Any]:
    """Explicitly create or advance a local anchor after validating its predecessor."""
    root = project_dir(root_value)
    path = _path(anchor_path)
    if path == governance_dir(root) or governance_dir(root) in path.parents:
        raise AEGSError("External ledger anchor must not be stored inside .aegs.")
    ledger_ok, message, _ = verify_ledger(root)
    if not ledger_ok:
        raise AEGSError(f"Cannot anchor an invalid ledger: {message}")
    hashes = _ledger_hashes(root)
    if not hashes:
        raise AEGSError("Cannot anchor an empty ledger.")
    previous_head: str | None = None
    if path.exists():
        prior = verify_external_anchor(root, path)
        if prior["status"] == "HOLD":
            raise AEGSError("Existing external ledger anchor is HOLD; investigate before replacing it.")
        previous_head = prior.get("anchor_head")
        if previous_head == hashes[-1]:
            return _read_anchor(path)
    anchor = {
        "schema": SCHEMA,
        "repo_root": root.as_posix(),
        "previous_anchor_head": previous_head,
        "current_head": hashes[-1],
        "observed_at": now_utc(),
    }
    anchor["summary"] = _anchor_summary(anchor)
    _write_anchor_atomic(path, anchor)
    state_path = governance_dir(root) / "state.json"
    state = read_json(state_path)
    state[STATE_KEY] = path.as_posix()
    write_json(state_path, state)
    return anchor
