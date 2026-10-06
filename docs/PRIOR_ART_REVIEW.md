# External prior-art review · 2026-10-06

本轮先审查外部源码，再设计，再实施。研究检出隔离于 `research_data/prior_art`，不发布、不安装进生产。以下是实际检出的 HEAD，不是声称复现论文收益。

| 项目 / 固定研究基线 | 已阅读的核心代码 | 采用与拒绝 |
| --- | --- | --- |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) `1394a3f72aa4393e1a98f51b382434c4b4c2d972` Apache-2.0 | `agents/analysts/news_analyst.py`, `researchers/bull_researcher.py`, `graph/trading_graph.py`, `dataflows/vendors/fred.py`, `memory/settlement.py`, `llm_clients/factory.py`, `api_key_env.py` | 借鉴角色分离、双边证据、按 as-of 查询 FRED、到期结算和惰性 provider。新版已具有宏观/预测市场工具，不能误称完全没有宏观或 PIT。拒绝将鼓动式 bull/bear 辩论、公司增长竞争优势、组合经理迁入 Gold/FX。反方必须寻找事实，不是扮演立场。日期限制和 vintage 查询不能解决新闻历史污染或证明 OOS。 |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) `2717499b8e30f242640af08c4ad9afd1113c2d45` Apache-2.0 | `finrobot_autogen/finrobot/agents/workflow.py`, `finrobot_equity/core/src/modules/financial_data_processor.py` | 借鉴 models reason / software computes / agents orchestrate / systems verify。实际目录已重组，旧 `finrobot/` 路径失效；不引入 AutoGen/股票财报和估值依赖。 |
| [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) `fdb04c9a273d1ccc3764b09b8e3ed1e708e57566` MIT | `fingpt/FinGPT_RAG/multisource_retrieval/utils/sentiment_classification_by_external_LLMs.py` | 借鉴抽取/检索与来源，拒绝把三分类情绪变成方向票。检查到的脚本含交互 GUI，不适合无人值守运行。未复现训练/GPU benchmark。 |
| [FinMem](https://github.com/xt2201/finmem) `a6fb1fe9d2947023397ba3c6d5746049c4e432e2` MIT | `puppy/memorydb.py`, `memory_functions/decay.py` | 借鉴时间衰减与分层检索，不借鉴由访问次数放大重要性。事实永不删除；衰减仅用于检索相关性，不改变历史或预测分数。 |
| [Qlib](https://github.com/microsoft/qlib) `be725493eb1a6bbb42bf11b37aa7669f59610ff1` MIT | `qlib/data/pit.py`, PIT 测试结构 | 借鉴 period time / observation time 区分和未来引用拒绝，不引入股票表达式引擎。PIT 是数据契约，不是一个 shift 就完成。 |
| [RD-Agent](https://github.com/microsoft/RD-Agent) `484776c211e4fbbeef03e0ec00d6bbee7362a4f4` MIT | `rdagent/core/proposal.py`, workflow 模块布局 | 借鉴 Hypothesis / ExperimentFeedback，拒绝生产时自动生成、搜索、晋级策略。研究建议必须预登记、单独 OOS、人工版本晋级。 |
| [OpenBB（已迁移）](https://github.com/openbq-org/OpenBB) `ae0268771f761b036996d81bd21522ce79d95415` LICENSE 声明 Apache-2.0 | `cli/openbb_cli/codegen/fetcher_gen.py`, LICENSE, extension 模板 | 借鉴 Query / Data / Fetcher 边界和凭据隔离。旧 owner OpenBB-finance 重定向到 openbq-org，跟踪保留 canonical identity。GitHub license 分类为 Other，不把 API 分类当律师审核。暂不引入全平台或自动 codegen。 |

代码复用：本轮不复制上述实现、不加入运行依赖；采用架构原则并独立实现。隔离 smoke 执行 TradingAgents provider 环境映射（2 个断言），对 FRED / FinMem / Qlib PIT 源码 compileall 成功。这只是最小模块检查，不是完整 agent 测试、更不是论文 OOS 复现；完整运行需要模型密钥、更多依赖或 GPU，未在生产安装。

## 金融方法核查

- [WGC GRAM](https://www.gold.org/goldhub/tools/gold-return-attribution-model)：周/月黄金回报**同期归因**、机会成本/风险/扩张/动量、关系变化与残差。采用驱动图和未解释部分，**不声称 GRAM 提供本项目 D5 预测 Edge**。
- [NBER Golden Dilemma](https://www.nber.org/papers/w18706)：长期购买力/估值与结构变化争议。作为结构先验，不映射成今日 CPI 到未来五天的固定方向。
- [AQR Carry](https://www.aqr.com/Insights/Research/Journal-Article/Carry)：carry 是条件不变时的可事前测量回报，跨资产存在研究证据但衰退期共同亏损。官方政策利差不是可交易 FX forward carry；不把长期/跨截面证据迁移为 AUDNZD 日频 OOS。
- [Man GOLD](https://www.man.com/insights/road-ahead-gold)、[2026 structural view](https://www.man.com/insights/views-from-the-floor-2026-6-Jan)：实际利率机会成本与央行需求可冲突；机构观点也不是独立预测验证。
- [Bridgewater Gold Rally](https://www.bridgewater.com/research-and-insights/taking-stock-of-the-gold-rally)：储备资产/结构需求用于长期情景；不强制短期看多。
- [RBA forward-looking AUD](https://www.rba.gov.au/publications/bulletin/2018/dec/a-forward-looking-model-of-the-australian-dollar.html)：贸易条件和相对实际利率、收益率曲线预期是关键；当期水平不足以知道定价。AUDNZD 必须有 NZ 一侧，不能简单使用 AUDUSD 因子。
- [Fed high-frequency announcements](https://www.federalreserve.gov/pubs/ifdp/2004/823/ifdp823.htm)、[BIS monetary spillovers](https://www.bis.org/publications/working-paper-757-explaining-monetary-spillovers-matrix-reloaded)：以调查预期识别 surprise，高频同步窗口识别反应； target/path/风险溢价不能混为一谈。采用 `(actual-consensus)/past surprise std`，严格锁定同一量纲与发布前预期。
- [ALFRED realtime](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)：观察期不是可知时点。公开 CSV 是 latest vintage，当前描述可用，历史 event OOS 不合格。
- Research Affiliates / Quantpedia 搜索入口本轮未取得可核验原文，不以二手摘录填引用，不从搜索摘要推导阈值。后续纳入待研究队列。

## 对已有系统的审计决定

KEEP：Provider、六模块事实、GC Proxy 身份、确定性 Gold 模型、加密 SQLite、冻结 ledger、outcome、原 OOS/消融和河流图。

REFACTOR：首页先回答变化/预期/定价/反应；新增共享 Macro Core 和 Country Profile；扩展时间/来源/证据图；AI 只使用冻结证据与有限工具。

REPLACE：浏览器直接调用 AI/BYOK 改为服务端环境变量/GitHub Secrets；不把统一 Evidence Score 当作宏观因果解释。

DELETE（仅行为，不删除历史）：自动把缺失当中性、新闻正面=买入、政策水平=市场未来路径、由上游版本自动修改模型的可能路径。

## 持续跟踪不是自动采用

研究基线固定于 `docs/upstream-watchlist.json`。独立周度任务检查 HEAD / release / LICENSE hash / public security advisories / compare 文件变化，追加保存快照与影响候选报告。接口、数据、时间语义、许可变化优先；star/commit 数不是研究质量。变更经历 triage → 隔离源码再读 → 预登记实验 → OOS → 新版本人工批准。检查失败保留 UNKNOWN，不当作无更新；检查不自动安装代码、不轮换基线、不调权重。见 [架构](ARCHITECTURE.md)。
