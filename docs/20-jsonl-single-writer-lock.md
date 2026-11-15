# JSONL Ledger Single-Writer Lock

The JSONL event ledger remains AEGS's authoritative, append-only hash chain.
Each `append_event` now obtains a local, process-level exclusive lock at
`.aegs/ledger.lock` before it reads the preceding event, derives the next
`previous_hash`, and appends a new line. The line is flushed and `fsync`'d
before a successful append is reported.

If another local process holds the lock, a writer retries only until its
bounded timeout and then raises `AEGSError` without claiming success or
writing an event. The lock is released when the owning append exits, including
on exceptions. The lock file is a runtime artifact and does not change the
ledger's JSONL event schema or the SQLite journal mirror behavior.

This is deliberately a cooperative, single-host protection boundary. It is
not a distributed lock, consensus protocol, or a substitute for the ledger's
hash-chain verification and human governance decisions.
