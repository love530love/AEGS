# Agent Handoff

```yaml
handoff_id: HO-<id>
project_id: <id>
charter_version: <version>
created_at: <iso-8601>
verified_facts: []
unverified_claims: []
current_goal: <goal>
current_version: <git/version reference>
open_decisions: []
open_risks: []
evidence_refs: []
environment_checks:
  git: <pass/fail/unknown>
  tests: <pass/fail/not-run>
  ledger: <pass/fail/unknown>
safe_next_actions: []
forbidden_actions: []
rollback_reference: <version/procedure>
```

交接文件是状态摘要，不替代 Event Ledger、实验产物或审批记录；每个结论均应可追溯至证据引用。
