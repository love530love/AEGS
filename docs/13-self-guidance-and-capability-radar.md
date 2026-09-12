# 自指导与受控能力雷达

AEGS 的“自驱动升级”是受约束的发现与验证能力，不是自动采纳最新技术。系统可以提出下一步、发现能力缺口、检索候选技术并设计实验；是否接入、安装或晋级仍由证据、政策和人类决定。

## 自指导循环

```text
Project State + Charter + Trace
  -> Gap Detection
  -> Research Question
  -> Source Retrieval and Provenance Check
  -> Candidate Capability Proposal
  -> Shadow Evaluation
  -> Human/Policy Decision
  -> Approved Registry or Rejected Lesson
```

## Capability Radar

雷达应维护候选项的来源、发布日期、许可证、维护状态、兼容性、权限需求、供应链风险、适用边界、预期收益、基线和退出方案。它只能从可信源提出候选：官方规范、原始论文、官方 SDK/注册表、已批准内部能力库；网页摘要、论坛或单一 Agent 判断仅可作为线索。

候选分级：

- **Observe**：仅记录趋势和研究问题，不改变系统。
- **Evaluate**：在隔离环境复现或做小型对照试验。
- **Adopt**：通过评估、许可证/安全审查和指定批准后进入受限注册表。
- **Retire**：保留淘汰原因、依赖版本和回滚说明。

## 技术互操作性原则

- 工具/资源接入可借鉴 [MCP Tools](https://modelcontextprotocol.io/specification/draft/server/tools)，但每项工具仍应有最小权限、输入输出契约和批准范围。
- 独立 Agent 协作可评估 [A2A](https://google-a2a.github.io/A2A/specification/)，但不得把协议互通误认为信任或授权互通。
- Trace 可映射到 [OpenTelemetry GenAI 语义约定](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)；映射层应隔离，以应对仍在演进的约定。
- 特定运行时可利用 [OpenAI Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/)，同时将 AEGS 的决策、批准与证据保留为厂商中立层。

## 禁止自动化的动作

禁止 Capability Radar 自动执行 `install`、授予凭据、启用写入工具、修改 Charter、替换生产工作流、扩大数据访问或升级到 RED 权限。每一项都必须生成提案和可审计决定。
