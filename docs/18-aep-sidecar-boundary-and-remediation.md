# AEP 只读评审反馈与 Sidecar 边界

## 建议反馈给 AEP 评审者

感谢对 AEGS 的只读对比评审。AEGS 接受以下优先级判断：项目治理证据不能替代 AEP 的 claim/lease、原会话 ACK、结果回读或任务完成判定；两仓库应保持独立，后续只通过窄的只读证据契约衔接。

已在 AEGS 中修复/收敛的事项：

1. Handoff 现在具备自摘要、不可变历史副本比对和账本事件 attestation；篡改 `current_handoff.json` 会使 `takeover` 返回 `STALE`。
2. 非 Git 项目使用排除治理目录和可能敏感文件后的文件内容指纹；源文件变化会使接管失效。
3. YELLOW/RED Proposal 必须包含有时区的 `expires_at`，过期后无法批准。
4. `decide`、`record_feedback`、`discover` 会先验证治理账本；验证失败时拒绝写入。

尚未解决且不应被误称为已完成：身份认证、签名/外部不可变锚点、并发单写入者、完整 Policy Decision Point、生产执行适配器及 AEP 集成。

## 两仓库的契约边界

AEGS 只可向 AEP 提供 `project_evidence`，并且应被 AEP 记录为辅助证据而非授权：

```json
{
  "source": "aegs-compatible",
  "handoff_id": "HO-...",
  "handoff_hash": "sha256:...",
  "takeover_status": "PASS | STALE | HOLD",
  "code_fingerprint": {"tracked_content_hash": "..."},
  "ledger_head": "...",
  "architecture_snapshot_hash": "...",
  "observed_at": "..."
}
```

即使 `takeover_status` 为 `PASS`，AEP 仍必须独立验证 Workspace、Agent capability、claim/lease、会话锚点、ACK 与结果读回。AEGS 不派工、不持有 AEP 任务状态，也不确认 AEP 执行完成。

## 需要 AEP 后续确认的事项

- 若 AEP 接受 `project_evidence`，应定义其 schema、摘要校验、过期策略与展示位置。
- AEP 的 handoff verify/accept 可将其作为 `evidence`，但不得把它转换为 `automatic_takeover_allowed=true`。
- 代码级依赖或复制前必须确认 AEGS 的许可证；目前概念/协议互鉴不需要引入源码。
