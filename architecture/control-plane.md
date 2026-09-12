# AEGS Control Plane

```text
                Human Governance Console
          directives / approvals / freeze / rollback
                           |
Project Adapter -- Policy Decision Point -- Capability Registry
 Git, CI, DB,   |          |                 Skills, roles, tools
 deploy, docs   |          |                         |
                v          v                         v
             Event and Evidence Ledger <--- Agent Runtime / Shadow Lab
                           |
         State Builder / Handoff Pack / Replay / Evaluation
```

## 控制平面与数据平面分离

- **数据平面**执行项目任务、工具调用、构建和受限实验。
- **控制平面**解释 Charter、核验授权、保存事件、生成待决事项、维护版本和回滚。

Agent 不直接拥有“可做任何事”的权限；每次高影响操作由 Policy Decision Point 根据主体、项目、动作、资源、环境、风险等级、有效期和批准事件判定。拒绝同样必须成为审计事件。

## 接管协议

1. 只读读取 Project Charter、最近 Handoff、状态、未决决定和能力清单。
2. 验证 Git、环境、事件账本和关键快照；把验证结果写为新的 Trace。
3. 将信息分为已验证事实、未验证主张、开放问题和受限动作。
4. 仅在授权范围内提出或执行下一安全动作；状态不可信时进入 `HOLD`。
