# Project Charter

```yaml
project_id: <stable-id>
owners: []
purpose: <what success means>
scope_in: []
scope_out: []
assets_and_sensitivity: []
environments:
  sandbox: <location>
  production: <location-or-none>
allowed_actions: []
forbidden_actions: []
approval_policy:
  green: <automatic experiment boundary>
  yellow: <required reviewers>
  red: <named human approvers>
rollback_policy: <required version and procedure>
evidence_retention: <policy>
handoff_slo: <time and required checks>
charter_version: 0.1.0
```

Charter 的修改是 RED 变更，必须由不依赖提案者的审批链生效。
