# AEP Advisory Evidence Export

`aegs evidence export [path]` is read-only. It prints source facts compatible
with AEP's `aep-project-evidence-v1` envelope: `source`, absolute `repo_root`,
`handoff_id`, `handoff_hash`, the recomputed `takeover_status`, and a
timezone-qualified `observed_at`.

Every export is explicitly advisory: `advisory_only: true` and
`automatic_takeover_allowed: false`. It grants no cross-project permission.
The `evidence_summary` is a deterministic hash of the handoff-bound source
facts, excluding observation time, so consumers can compare repeated reads.

The command never writes AEGS or AEP. It reports the real current takeover
verdict: a stale or held handoff is exported as `STALE` or `HOLD`, never
misrepresented as `PASS`.
