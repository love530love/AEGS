# 进化闭环

```text
Observe -> Diagnose -> Propose -> Experiment -> Evaluate -> Decide -> Promote/Reject -> Verify -> Observe
```

1. **Observe**：从 Trace、任务结果、用户反馈和运行指标捕获信号。
2. **Diagnose**：区分偶发失败、实现错误、流程缺陷和真实能力缺口。
3. **Propose**：形成可测试的 Skill、工作流、角色或评估变更提案；声明预期收益、风险和回滚方式。
4. **Experiment**：在 Shadow Lab 中运行基线与候选版本，保持输入、工具和环境可比较。
5. **Evaluate**：依据评估矩阵验证改善与非回归。
6. **Decide**：由政策门控和所需 Council/人类批准作出 Promote、Reject、Hold 或 Rollback 决定。
7. **Verify**：晋级后持续监测；异常时冻结并可回滚。

Reject 需要沉淀失败原因、反例、实验数据和可检索 Lesson。禁止把“没有提升”表述成能力成功。

## 冻结与基线纪律

- Proposal 创建时冻结基线版本、目标、测试任务集、评价指标、阈值、随机种子和环境清单。
- 每个候选必须与至少一个简单、长期保留的基线比较；复杂候选不能因“更新”而取代基线。
- 实验完成后只能追加结果、补充审计或创建新提案，不能回写原 Proposal 的成功标准或历史结果。
- 若证据链校验失败、发生权限越界或可复现性丢失，自动停止晋级，状态为 `HOLD`，由人工审查恢复。
