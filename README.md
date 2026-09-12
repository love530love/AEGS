# AEGS — Auditable Evolutionary Governance System

AEGS 是一个用于研究和实现 **Governed Self-Evolution（受治理的自进化）** 的架构项目。它不把“自我修改”视为目标；目标是把运行中的结构化经验，在证据、实验、评估和治理约束下，编译为可验证、可回滚的新能力。

## 核心命题

`Experience -> Evidence -> Capability -> Verification -> Evolution`

系统的最小可信单位不是一次模型回答，而是可追溯的事件、证据和决策链。任何能力升级都必须可审计、可解释、可复现，并能在需要时回滚。

## v0.1 范围

- 定义事件、Trace、经验、证据、Skill、实验、评估和版本的领域模型。
- 实现“提案 -> 影子实验 -> 评估 -> 人工/策略批准 -> 晋级或拒绝”的进化闭环。
- 将 Prompt 视为认知引擎的一种策略，而非系统核心。
- 不直接修改基础模型；不允许绕过宪法与人工最终治理。

## 文档入口

- [项目愿景](docs/00-project-vision.md)
- [讨论沉淀](docs/01-architecture-discussion.md)
- [已采纳决策](docs/02-architecture-decisions.md)
- [v0.1 架构](docs/03-aegs-v0.1-architecture.md)
- [进化闭环](docs/04-evolution-loop.md)
- [专家组织](docs/05-expert-organization.md)
- [经验、证据与溯源](docs/06-experience-evidence-provenance.md)
- [评估框架](docs/07-evaluation-framework.md)
- [治理与宪法](docs/08-governance-and-constitution.md)
- [开放问题账本](docs/09-open-questions.md)
- [来自 3D 项目的可迁移模式](docs/10-reference-derived-patterns.md)
- [进化提案模板](docs/templates/EVOLUTION_PROPOSAL_TEMPLATE.md)
- [v0.2 产品需求](docs/11-v0.2-product-requirements.md)
- [人类治理控制台](docs/12-human-governance-console.md)
- [自指导与受控能力雷达](docs/13-self-guidance-and-capability-radar.md)
- [项目治理包模板](docs/templates/PROJECT_CHARTER_TEMPLATE.md)
- [Agent 交接模板](docs/templates/AGENT_HANDOFF_TEMPLATE.md)

## 状态

架构基线：v0.1（设计阶段）。本文档描述目标设计，不宣称已有可运行的自进化实现或已验证的安全保证。
