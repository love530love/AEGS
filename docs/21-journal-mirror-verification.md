# SQLite Journal Mirror Verification

`ledger.jsonl` remains the authoritative event ledger. SQLite is only a local
query mirror and never supplies missing evidence to the JSONL chain.

`aegs journal verify` recomputes the mirror relationship from the JSONL
authority: it validates the authoritative chain first, then checks SQLite
sequence continuity, the journal hash chain, event count, chain head, metadata
head, and the exact critical event fields (`event_id`, `event_type`,
`occurred_at`, `previous_hash`, `payload`, and `event_hash`). Any mismatch is
reported as `HOLD` with a reason; verification never rewrites either store.

`aegs journal sync` is an explicit operation. It may append only a verified
missing tail when every existing SQLite event is an exact JSONL prefix. It
refuses a malformed, divergent, overlong, or metadata-inconsistent journal;
operators must investigate such evidence rather than silently rebuilding it.
