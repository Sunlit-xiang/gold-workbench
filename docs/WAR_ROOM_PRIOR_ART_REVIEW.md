# Macro War Room — External Prior-Art Review

核对日期：2026-10-06。只复用机制，不引入新框架依赖，不把外部交易演示视为预测效果证明。

| 一手方案 | 已有标准机制 | 本项目吸收 / 不吸收 |
| --- | --- | --- |
| [OpenAI orchestration](https://developers.openai.com/api/docs/guides/agents/orchestration) | Manager / agents-as-tools 保持最终答复所有权；handoff 则交出会话所有权 | 主管拥有综合报告，成员是有预算的研究单元；用户可以单独追问研究员，不让日报变成无主群聊。没有采用 SDK 的特定实现。 |
| [Anthropic effective agents](https://www.anthropic.com/engineering/building-effective-agents) | Orchestrator-workers；evaluator-optimizer；简单可组合流程与迭代上限 | 派问题、回报、反证、有限补证。其文档提示复杂性、延迟、成本与错误累积；不采用无限“自主辩论”。该文章是模式先验，不是金融效果证据。 |
| [LangGraph supervisor](https://github.com/langchain-ai/langgraph-supervisor-py) | Supervisor、工具调用、显式上下文工程 | 官方仓库已建议多数新用途直接用 tools 实现 supervisor，而非一定安装该库。保持现有 Python / Provider / SQLite，以结构化报告传递上下文。 |
| [AutoGen SelectorGroupChat](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html) | Planner、动态发言人、终止条件、消息上限 | 吸收终止条件与有明确职责的参与者；不把每次发言都交给另一个模型选择，不无限轮换发言。 |
| [CrewAI hierarchical process](https://docs.crewai.com/en/learn/hierarchical-process) | Manager、任务委派、结果审阅 | 任务必须是具体可调查问题；结果必须真正读取。角色的 backstory 不是研究完成或专业水平证明。 |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | 专业分析、结构化讨论、管理者综合；项目自称研究框架 | 吸收可见报告和反证审查。拒绝强制 bull/bear 表演、自动下单和把代理多数意见当 Edge。上游架构更新进入已有 watchlist + 人工审批流程。 |
| [Bloomberg Research Management Solutions](https://professional.bloomberg.com/products/bloomberg-terminal/research/research-management-solutions/) | 统一研究创作、消费、协作和管理工作流 | 首页面向研究阅读；研究桌保留资料、论点和时间。公开页面不披露完整内部架构，不能据此声称复刻 Bloomberg 的 Agent 系统。 |

## 采用的工作流与边界

`Director assignment → Specialists inspect/report → Skeptic inspects reports → Director review → up to two supplements → Director morning brief`

- WR-P2 是新提示/报告契约版本；旧 WR-P1 报告不改写，不伪装成完成新流程。
- Specialist：Liquidity、Inflation/Rates、Cross Asset、Gold/FX；可选 Events。Skeptic 不负责机械唱空。
- 每次报告保留实际读过的 evidence/source IDs、工具工作记录、peer report IDs、自评 Confidence、支持/反对证据、明确指向报告的分歧与补证。
- Peer report 是假设，不是事实来源；引用其底层材料前必须自己读取。自评 Confidence 不等于历史 Accuracy。
- 主管审阅失败，不用固定文字绕过失败生成“共识”。补证最多两个；工具轮次有上限。仍未解决的分歧必须保留。
- 没有真实模型调用时为 **NOT YET ANALYZED**。UI 合成场景只在 **DEMO / MOCK** 模式，浏览器不向研究 API 提交，不写 SQLite。
- 所有新研究只追加；MacroStore 没有 Gold prediction 写入能力。没有改变原 DSH 安装、配置、账户或会话。

## 仍需实际观察的失败模式

这些机制的存在不证明它们能提高金融判断质量。需要实测：同一底层数据是否被反复当作独立证据；反证是否只有客套警告；主管是否掩盖分歧；调用成本是否大于信息增量；事实/推论是否仍被读者混淆。以阅读验收和长期事实账本评价，而非对话轮数或代理人数评价。
