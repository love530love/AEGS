# AEGS v0.1 架构

```text
Human Governance / Stakeholders
              |
Goals + Constitution + Policy Gate
              |
Orchestrator ---- Cognitive Engine (planning, tools, skills, councils)
              |
        Event + Trace Fact Layer
              |
Experience / Evidence / Evolution Knowledge Graph
              |
Capability Gap -> Proposal -> Shadow Lab -> Evaluation -> Promotion/Rollback
```

## 核心组件

- **Orchestrator**：按任务风险、复杂度和能力缺口选择工作流与最小 Council。
- **Cognitive Engine**：调度 Prompt、Tool、Skill、检索和角色协议。
- **Fact Layer**：不可变或追加式 Trace/Event，记录输入、工具调用、观察、决策与产出。
- **Experience System**：从事实层整理结构化经验，而不把未经验证的总结当事实。
- **Evolution Knowledge Graph**：关联任务、假设、实验、证据、Skill、版本、失败与政策。
- **Shadow Lab**：候选变更的隔离实验环境。
- **Evaluation & Governance Gate**：计算评估矩阵、执行权限政策，并要求相应批准。

## 初期数据实体

`Task, Trace, Event, Experience, Evidence, Hypothesis, Proposal, Experiment, Evaluation, Skill, Capability, Role, Decision, Policy, Version, Failure`。

每个可晋级对象应有稳定 ID、时间、输入版本、责任角色、证据引用和可复现实验配置。

## 运行产物分层

借鉴成熟数据工程的隔离原则，v0.1 的每层仅读取已版本化的上游产物：

```text
01_raw_trace      原始工具响应、输入和环境快照；只追加
02_validate       完整性、哈希、权限与数据契约检查
03_normalize      可检索的规范化 Event/Trace；保留转换审计
04_experience     结构化经验和假设，明确不等同原始事实
05_capabilities   Skill/Role/Workflow 候选与已批准注册表
06_experiments    冻结输入、基线、候选和运行清单的影子实验
07_evaluations    指标、反例、回归和独立审查
08_versions       已批准的能力包、政策版本和回滚指针
09_monitoring     晋级后的漂移、事故和复盘记录
```

候选能力禁止直接读取不受控外部状态后覆盖历史产物；原始 Trace 和评估产物均不可被“修复性重写”。
