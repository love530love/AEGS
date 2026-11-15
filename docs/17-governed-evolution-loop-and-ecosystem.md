# 受治理的自进化闭环与开放生态

## 全链路闭环

AEGS 不把“发现新工具”或“模型自己修改流程”称作进化。一次可治理的进化至少经过以下闭环：

```text
Observe -> Trace -> Diagnose -> Hypothesis -> Proposal -> Shadow Experiment
   -> Evaluation -> Human/Policy Decision -> Versioned Action -> Outcome Monitoring
   -> Experience Compilation -> Capability Registry -> Transfer/Revalidation -> Observe
```

| 阶段 | 主要产物 | 不可省略的控制 |
|---|---|---|
| Observe/Trace | 事件、输入输出、环境、外部反馈 | 事实与总结分离；敏感数据最小化 |
| Diagnose/Hypothesis | 缺口、可证伪假设、反例 | 不把单次失败当作能力缺口 |
| Proposal | 范围、替代方案、影响、反方证据、验收标准 | YELLOW/RED 结构化门控 |
| Shadow Experiment | 冻结基线、任务集、种子、工件 | 不触及生产状态 |
| Evaluation | 效果、回归、迁移、安全、成本 | 不以单一分数晋级 |
| Decision/Action | 批准、版本、回滚、责任 | 人类最终治理与可执行回滚 |
| Outcome/Experience | 真实结果、意外影响、经验与反例 | Evaluation 不等于 Outcome |
| Registry/Revalidation | 已批准 Skill/Capability、适用范围、淘汰记录 | 候选不等于可部署能力 |

当前 AEGS 已落地 Trace/账本原型、Proposal、Decision、Discovery、Handoff、Takeover、Doctor 和架构快照。Shadow Lab、Outcome、Experience Compiler、Capability Registry、Transfer/Revalidation 仍是待开发阶段，不能被描述为已实现。

## 从 AEP 借鉴的边界

指定的 AEP 生态评估文档提供了四项可直接吸收的原则：

1. **能力状态分级**：核心实现、本机探测、会话验收、生产闭环、参考候选必须区分。
2. **动作与事实分离**：工具调用成功只代表动作尝试；读回、目标 ACK 或结果工件才可成为事实。
3. **连接器先于全家桶**：外部系统以窄 Adapter/Profile 接入，AEGS 仍保存项目状态、证据、权限与交接。
4. **真实闭环验收**：一个外部能力必须具备输入、可观察动作、目标确认和结果读回，而非只完成安装或工具枚举。

AEGS 不应直接继承 AEP 的桌面派工、窗口会话证明或积分机制作为核心；这些属于执行/协作系统的可选 Connector，必须按 AEGS Charter 和风险门控评估。

## 生态引入策略

| 方向 | 借鉴/候选 | AEGS 位置 | 采纳状态 |
|---|---|---|---|
| 工具与数据互操作 | [MCP Tools](https://modelcontextprotocol.io/specification/draft/server/tools) | Tool Adapter，最小权限和人类确认 | 标准边界，未内置运行时 |
| Agent 间互操作 | [A2A](https://a2a-protocol.org/latest/) | Agent/Expert Connector 与任务工件交换 | 候选；协议不等于授权 |
| 耐久工作流 | [Temporal Python SDK](https://docs.temporal.io/develop/python) | 长实验/评估 Runner 的可选后端 | 研究试点，非默认依赖 |
| Trace 语义 | [OpenTelemetry GenAI](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Trace 导出映射层 | 候选；语义约定仍应隔离 |
| 本地全文检索 | [SQLite FTS5](https://www.sqlite.org/fts5.html) | 经验/证据索引 | 候选；不作为权威事实源 |

任何候选都必须登记来源、revision、许可证、维护状态、权限要求、供应链风险、评估计划、退出方案和证据等级。`Observe -> Evaluate -> Adopt -> Retire` 由 Capability Radar 管理；只有 `Adopt` 后且经过相应 Project Charter 批准的能力才进入 Registry。

## SQLite 事件镜像试点

本阶段实现了可选 SQLite 镜像，用于事务性导入、链校验和 drift 检测：

```powershell
python -m aegs.cli journal init .
python -m aegs.cli journal status .
python -m aegs.cli journal sync .
```

JSONL 在试点阶段仍是权威事件账本。SQLite 镜像与 JSONL 发生差异时状态为 `STALE`；链校验失败时为 `HOLD`。这不是跨存储原子提交、签名账本或不可篡改存储，后续 M2 必须在并发/崩溃恢复基准后决定是否迁移为事务权威源。非 Git 文件指纹排除治理目录以及按**文件名/后缀**识别的敏感文件；当前不按父目录名称排除，以避免静默遗漏普通源码。
