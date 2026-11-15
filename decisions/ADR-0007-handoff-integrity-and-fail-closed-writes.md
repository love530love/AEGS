# ADR-0007: Handoff 完整性、非 Git 新鲜度与 Fail-Closed 写入

- 状态：Accepted
- 日期：2026-11-15

## 决策

Handoff 使用 `handoff_hash` 覆盖正文（排除自身和账本事件哈希字段），并与不可变副本和 `handoff.created` 账本事件交叉校验。Implementation rejects a tampered handoff self-binding during takeover. 非 Git 项目采用排除敏感/治理路径的文件内容指纹。YELLOW/RED Proposal 在批准时必须未过期。所有治理写入口先验证账本，验证失败则拒绝写入。

## 后果

旧 Handoff 会成为 `STALE`，须重新生成；高风险旧草案若无过期时间不能被新规则批准。此举提升接管可信度，但仍不能抵御拥有本地写入权者整体重写所有本地工件，也不替代认证、签名或外部不可变存储。
