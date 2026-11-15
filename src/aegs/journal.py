from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .core import AEGSError, canonical_json, document_hash, governance_dir, ledger_head, project_dir, verify_ledger


def journal_path(root: Path) -> Path:
    return governance_dir(root) / "events.sqlite3"


def _ledger_events(root: Path) -> list[dict[str, Any]]:
    ledger = governance_dir(root) / "ledger.jsonl"
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS journal_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS journal_events (
            sequence INTEGER PRIMARY KEY,
            event_id TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            event_hash TEXT NOT NULL UNIQUE
        );
    """)


def _insert_events(connection: sqlite3.Connection, events: list[dict[str, Any]], start_sequence: int) -> None:
    for offset, event in enumerate(events):
        connection.execute(
            """INSERT INTO journal_events (sequence, event_id, event_type, occurred_at, previous_hash, payload_json, event_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                start_sequence + offset,
                event["event_id"],
                event["event_type"],
                event["occurred_at"],
                event["previous_hash"],
                canonical_json(event["payload"]),
                event["event_hash"],
            ),
        )


def _hold(path: Path, reasons: list[str], ledger_events: int | None = None, journal_events: int | None = None, ledger_head_value: str | None = None, journal_head: str | None = None, syncable_missing_tail: bool = False) -> dict[str, Any]:
    """Return a fail-closed mirror result; JSONL stays the authority."""
    result: dict[str, Any] = {
        "status": "HOLD",
        "authority": "ledger.jsonl",
        "path": str(path),
        "reasons": reasons,
        "syncable_missing_tail": syncable_missing_tail,
    }
    if ledger_events is not None:
        result["ledger_events"] = ledger_events
    if journal_events is not None:
        result["journal_events"] = journal_events
    if ledger_head_value is not None:
        result["ledger_head"] = ledger_head_value
    if journal_head is not None:
        result["journal_head"] = journal_head
    return result


def init_journal(root_value: str | Path) -> dict[str, Any]:
    root = project_dir(root_value)
    ledger_ok, message, _ = verify_ledger(root)
    if not ledger_ok:
        raise AEGSError(f"Cannot initialize journal from invalid ledger: {message}")
    path = journal_path(root)
    if path.exists():
        raise AEGSError(f"Journal already exists: {path}. Use 'aegs journal sync' or 'status'.")
    events = _ledger_events(root)
    connection = _connect(path)
    try:
        with connection:
            _create_schema(connection)
            _insert_events(connection, events, 1)
            connection.executemany(
                "INSERT INTO journal_meta (key, value) VALUES (?, ?)",
                [
                    ("schema_version", "0.1"),
                    ("source", "ledger.jsonl mirror"),
                    ("ledger_head", ledger_head(root) or ""),
                ],
            )
    finally:
        connection.close()
    return {"status": "PASS", "path": str(path), "imported_events": len(events), "ledger_head": ledger_head(root)}


def verify_journal(root_value: str | Path) -> dict[str, Any]:
    """Recompute whether the SQLite cache exactly mirrors the JSONL authority.

    A mismatch is never repaired here.  A caller may explicitly run ``sync``
    only when the journal is an otherwise-valid prefix missing a tail of the
    authoritative ledger; a fork or malformed mirror remains HOLD.
    """
    root = project_dir(root_value)
    path = journal_path(root)
    ledger_ok, ledger_message, ledger_count = verify_ledger(root)
    if not ledger_ok:
        return _hold(path, [f"Authoritative JSONL ledger is invalid: {ledger_message}"], ledger_events=ledger_count)
    events = _ledger_events(root)
    source_head = events[-1]["event_hash"] if events else None
    if not path.exists():
        return _hold(path, ["SQLite journal mirror is missing; initialize it explicitly from the JSONL authority."], ledger_events=len(events), ledger_head_value=source_head)
    try:
        connection = _connect(path)
    except sqlite3.DatabaseError as error:
        return _hold(path, [f"SQLite journal cannot be opened: {error}"], ledger_events=len(events), ledger_head_value=source_head)
    try:
        rows = connection.execute("SELECT * FROM journal_events ORDER BY sequence").fetchall()
        try:
            metadata = dict(connection.execute("SELECT key, value FROM journal_meta").fetchall())
        except sqlite3.DatabaseError as error:
            return _hold(path, [f"Journal schema is unreadable: {error}"], len(events), len(rows), source_head)
        expected_previous = "GENESIS"
        journal_events: list[dict[str, Any]] = []
        for expected_sequence, row in enumerate(rows, start=1):
            if row["sequence"] != expected_sequence:
                return _hold(path, [f"Journal sequence is non-contiguous at stored sequence {row['sequence']}."], len(events), len(rows), source_head, expected_previous)
            try:
                event = {
                    "event_id": row["event_id"], "event_type": row["event_type"], "occurred_at": row["occurred_at"],
                    "previous_hash": row["previous_hash"], "payload": json.loads(row["payload_json"]), "event_hash": row["event_hash"],
                }
            except (json.JSONDecodeError, TypeError) as error:
                return _hold(path, [f"Journal payload is malformed at sequence {row['sequence']}: {error}"], len(events), len(rows), source_head, expected_previous)
            hashed = {key: value for key, value in event.items() if key != "event_hash"}
            if event["previous_hash"] != expected_previous or document_hash(hashed) != event["event_hash"]:
                return _hold(path, [f"Journal hash-chain validation failed at sequence {row['sequence']}."], len(events), len(rows), source_head, expected_previous)
            journal_events.append(event)
            expected_previous = event["event_hash"]
        journal_head = expected_previous if rows else None
        common = min(len(events), len(journal_events))
        for index in range(common):
            if journal_events[index] != events[index]:
                return _hold(path, [f"Journal event differs from JSONL authority at sequence {index + 1}."], len(events), len(rows), source_head, journal_head)
        if len(journal_events) > len(events):
            return _hold(path, ["Journal has more events than the JSONL authority."], len(events), len(rows), source_head, journal_head)
        if len(journal_events) < len(events):
            return _hold(path, ["Journal is missing a tail of the JSONL authority."], len(events), len(rows), source_head, journal_head, syncable_missing_tail=True)
        if metadata.get("source") != "ledger.jsonl mirror":
            return _hold(path, ["Journal metadata does not identify JSONL as the authority."], len(events), len(rows), source_head, journal_head)
        if metadata.get("ledger_head") != (source_head or ""):
            return _hold(path, ["Journal metadata ledger_head differs from the JSONL authority."], len(events), len(rows), source_head, journal_head)
        return {"status": "PASS", "authority": "ledger.jsonl", "path": str(path), "reasons": [], "ledger_events": len(events), "journal_events": len(rows), "ledger_head": source_head, "journal_head": journal_head}
    except sqlite3.DatabaseError as error:
        return _hold(path, [f"Journal schema validation failed: {error}"], len(events), ledger_head_value=source_head)
    finally:
        connection.close()


def journal_status(root_value: str | Path) -> dict[str, Any]:
    """Backward-compatible name for strict journal verification."""
    return verify_journal(root_value)


def sync_journal(root_value: str | Path) -> dict[str, Any]:
    root = project_dir(root_value)
    current = verify_journal(root)
    if current["status"] == "PASS":
        return {"status": "PASS", "authority": "ledger.jsonl", "synced_events": 0, "journal_events": current["journal_events"], "ledger_head": current["ledger_head"]}
    if not current.get("syncable_missing_tail"):
        raise AEGSError("Journal verification is HOLD; do not sync until the mismatch has been investigated.")
    path = journal_path(root)
    events = _ledger_events(root)
    connection = _connect(path)
    try:
        existing = connection.execute("SELECT sequence, event_hash FROM journal_events ORDER BY sequence").fetchall()
        pending = events[len(existing):]
        with connection:
            _insert_events(connection, pending, len(existing) + 1)
            connection.execute("INSERT OR REPLACE INTO journal_meta (key, value) VALUES (?, ?)", ("ledger_head", ledger_head(root) or ""))
        verified = verify_journal(root)
        if verified["status"] != "PASS":
            raise AEGSError("Journal sync did not produce a verified mirror; manual investigation required.")
        return {"status": "PASS", "authority": "ledger.jsonl", "synced_events": len(pending), "journal_events": len(events), "ledger_head": ledger_head(root)}
    finally:
        connection.close()
