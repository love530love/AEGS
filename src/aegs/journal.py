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


def journal_status(root_value: str | Path) -> dict[str, Any]:
    root = project_dir(root_value)
    path = journal_path(root)
    if not path.exists():
        return {"status": "MISSING", "path": str(path), "reasons": ["SQLite journal mirror has not been initialized."]}
    connection = _connect(path)
    try:
        rows = connection.execute("SELECT * FROM journal_events ORDER BY sequence").fetchall()
        expected_previous = "GENESIS"
        for row in rows:
            event = {
                "event_id": row["event_id"], "event_type": row["event_type"], "occurred_at": row["occurred_at"],
                "previous_hash": row["previous_hash"], "payload": json.loads(row["payload_json"]),
            }
            if row["previous_hash"] != expected_previous or document_hash(event) != row["event_hash"]:
                return {"status": "HOLD", "path": str(path), "reasons": [f"Journal hash-chain validation failed at sequence {row['sequence']}."], "journal_events": len(rows)}
            expected_previous = row["event_hash"]
        source_head = ledger_head(root)
        if expected_previous != source_head:
            return {"status": "STALE", "path": str(path), "reasons": ["Journal mirror differs from current JSONL ledger."], "journal_events": len(rows), "journal_head": expected_previous, "ledger_head": source_head}
        return {"status": "PASS", "path": str(path), "reasons": [], "journal_events": len(rows), "journal_head": expected_previous}
    finally:
        connection.close()


def sync_journal(root_value: str | Path) -> dict[str, Any]:
    root = project_dir(root_value)
    current = journal_status(root)
    if current["status"] == "MISSING":
        return init_journal(root)
    if current["status"] == "HOLD":
        raise AEGSError("Journal validation failed; do not sync until it has been investigated.")
    path = journal_path(root)
    events = _ledger_events(root)
    connection = _connect(path)
    try:
        existing = connection.execute("SELECT sequence, event_hash FROM journal_events ORDER BY sequence").fetchall()
        if len(existing) > len(events):
            raise AEGSError("Journal has more events than the JSONL ledger; manual investigation required.")
        for row, event in zip(existing, events):
            if row["event_hash"] != event["event_hash"]:
                raise AEGSError(f"Journal and JSONL diverge at sequence {row['sequence']}; manual investigation required.")
        pending = events[len(existing):]
        if pending:
            with connection:
                _insert_events(connection, pending, len(existing) + 1)
                connection.execute("INSERT OR REPLACE INTO journal_meta (key, value) VALUES (?, ?)", ("ledger_head", ledger_head(root) or ""))
        return {"status": "PASS", "synced_events": len(pending), "journal_events": len(events), "ledger_head": ledger_head(root)}
    finally:
        connection.close()
