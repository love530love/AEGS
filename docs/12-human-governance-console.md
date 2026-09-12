# 人类治理控制台与反馈设计

控制台是政策执行入口，不是普通聊天框或“最后确认”按钮。它应帮助人抵抗遗忘、注意力分散、疲劳、表达歧义、框架效应和前后矛盾，同时保留人类对目标与价值取舍的最终权力。

## 五个界面

1. **Decision Inbox**：按风险、截止时间和影响范围展示待决事项；支持 Approve、Reject、Defer、Need Evidence、Freeze、Rollback、Override。
2. **Decision Card**：显示改动 Diff、基线与候选、收益、成本、最坏后果、反方证据、未知项、适用范围、到期时间和回滚方案。
3. **Project Cockpit**：显示当前版本、目标、健康度、未决项、事故、下一安全动作与权限状态。
4. **Evolution Timeline / Evidence Graph**：从版本回放到决定、实验、Trace 和外部证据。
5. **Feedback Studio**：结构化提交偏好、约束、事实更正、假设和长期价值排序。

## 反馈必须结构化

所有自然语言反馈先被解析为候选 `HumanDirective`，并要求人确认其类型、范围和有效期。它在确认前不改变政策。

```yaml
directive_id: HD-<id>
kind: preference | constraint | fact_correction | decision | hypothesis
scope: task | project | project_group | global_candidate
duration: once | task_end | expires_at | persistent
confidence: certain | preference | exploratory
source_text: "原始反馈"
normalized_effect: "机器可执行的受限解释"
requires_review: true
```

## 人因护栏

- **上下文胶囊**：每项高风险决定显示“上次相似决定、此次差异、不可逆后果和替代方案”。
- **对称呈现**：支持与反对证据、成功与失败指标同屏；提案者不得独占摘要叙事。
- **注意力预算**：低风险可批量处理；YELLOW/RED 限量、允许稍后处理，连续快速批准触发复核提示。
- **冲突识别**：新指令与已批准约束冲突时，只能选择“本次例外”“修改规则”或“保持原规则”。
- **冷静期与撤销**：高风险批准可设延迟生效窗口；生效后仍保留回滚而非删除历史。
- **反诱导**：默认选项不得被 Agent 隐藏；Override 必须说明理由、权限依据和承担者。

人类代表可以由角色化视角模拟以发现遗漏，但其输出始终标记为 `simulated_stakeholder_input`，不能代替真实用户访谈、所有者批准或法律/安全专业意见。
