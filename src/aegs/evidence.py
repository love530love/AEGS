"""Read-only advisory evidence for external project coordinators."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import AEGSError, document_hash, git_head, governance_dir, project_dir, read_json, takeover


SCHEMA = "aep-project-evidence-v1"
SOURCE = "AEGS"


def _observed_at(moment: datetime | None) -> str:
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise AEGSError("Evidence observation time must be timezone-aware.")
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def export_evidence(root_value: str | Path, observed_at: datetime | None = None) -> dict[str, Any]:
    """Export AEP source facts without writing or granting takeover permission.

    The current takeover verdict is reported exactly as recomputed.  In
    particular, a stale or held project cannot be exported as a PASS claim.
    """
    root = project_dir(root_value)
    handoff = read_json(governance_dir(root) / "current_handoff.json")
    handoff_id = str(handoff.get("handoff_id", "")).strip()
    handoff_hash = str(handoff.get("handoff_hash", "")).strip()
    if not handoff_id or not handoff_hash:
        raise AEGSError("Cannot export AEP evidence without a current handoff ID and hash.")
    binding = handoff.get("evidence_binding")
    if not isinstance(binding, dict):
        raise AEGSError("Cannot export AEP evidence without a handoff evidence binding.")
    verdict = takeover(root)
    takeover_status = str(verdict.get("status", "HOLD")).upper()
    if takeover_status not in {"PASS", "STALE", "HOLD"}:
        raise AEGSError("Takeover returned an unrecognized status; refusing external evidence export.")
    source_facts = {
        "source": SOURCE,
        "repo_root": root.as_posix(),
        "git_head": git_head(root) or "",
        "handoff_id": handoff_id,
        "handoff_hash": handoff_hash,
        "takeover_status": takeover_status,
        "code_fingerprint": binding.get("code_fingerprint"),
        "architecture_snapshot_hash": str(binding.get("architecture_snapshot_hash") or ""),
    }
    stable_summary = document_hash(source_facts)
    return {
        "schema": SCHEMA,
        **source_facts,
        "observed_at": _observed_at(observed_at),
        "advisory_only": True,
        "authority": "advisory",
        "automatic_takeover_allowed": False,
        "evidence_summary": stable_summary,
        "note": "Read-only source observation. It grants no permission, lease, or automatic takeover right.",
    }
