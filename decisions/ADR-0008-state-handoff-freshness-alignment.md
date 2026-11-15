# ADR-0008: State 与 Handoff 新鲜度绑定

- 状态：Accepted
- 日期：2026-11-15

## 决策

`create_handoff` 在同一受控操作内写入 State 的 `current_git_head` 和 `current_code_fingerprint`，并将其复制到 Handoff 的 `state_binding`。`takeover` 和 `doctor` 都比较 State 与 Handoff 的绑定；任一不一致返回/报告 `STALE`。

## 后果

旧 Handoff 缺失 `state_binding` 时不会获得 PASS，必须重新生成。此机制检测 State 指针漂移，但不是跨文件事务、签名状态或对抗本地完全写入者的安全边界；这些仍由后续事务化事件存储与认证工作处理。
