# 评估框架

候选进化不是以单项指标上升即成功。最低评估矩阵：

| 维度 | 要回答的问题 |
|---|---|
| Outcome | 任务结果是否改善？ |
| Process | 过程是否更可靠、可复现？ |
| Transfer | 是否在未见任务上仍有效？ |
| Robustness | 输入、环境变化时是否稳定？ |
| Safety | 风险是否增加？ |
| Cost | 时间、工具、计算和人工成本是否可接受？ |
| Regression | 既有能力是否退化？ |

定义：`Evolution Success = Improvement AND Non-Regression AND Transfer AND Safety AND Acceptable Cost`。

实验应先冻结基线、目标、数据切分和判定阈值；结果后不得追溯性修改成功标准。对可能泄漏的经验/测试集实行隔离与审计。

## 反自欺门槛

- 评估任务按时间、来源或因果可用性分割；禁止候选从未来 Trace 或被评任务学习。
- 同时呈现有利与不利指标、失败案例、置信区间和与基线的差异。
- 多候选、多提示词、多窗口探索必须记录次数；探索发现和预注册结论分开标记。
- 只有独立重放仍成立的改善才可进入 Promotion；否则保持实验或 challenger 身份。
