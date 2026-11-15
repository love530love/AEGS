# Optional Local Ledger Anchors

`aegs anchor write --file <path>` writes an atomically replaced local anchor
outside `.aegs`. The anchor records `previous_anchor_head`, `current_head`, a
deterministic `summary`, and a timezone-qualified `observed_at`. Its path is
then recorded in AEGS state so `aegs doctor` can verify it.

The doctor check reports `PASS` when the anchor matches the authoritative
ledger, `STALE` when the ledger has safely advanced beyond the anchor, and
`HOLD` for a missing or malformed anchor, a summary mismatch, a head absent
from the ledger (possible rollback or replacement), or a broken anchor chain.

This is a local audit aid only. It is not a signature, remote witness,
consensus mechanism, or immutable proof: an actor able to replace both local
files can defeat it.
