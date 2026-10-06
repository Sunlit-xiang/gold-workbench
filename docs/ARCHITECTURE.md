# Macro Evidence & Pricing Workbench · MEP-1.0

## Macro War Room 增量设计（2026-10-06，实施中）

产品校准：默认首页是 **Macro War Room**，按 Situation → Interpretation → Evidence 阅读；行情与原始指标下移。真实研究未执行显示 **NOT YET ANALYZED**；单独的 **DEMO / MOCK** 只验证交互，不写账本。研究桌包括问题、可读解释、已读资料、支持/反对证据、团队关系与持续追问。

WR-P2 流程：Director 派题 → Liquidity / Inflation-Rates / Cross Asset / 资产 Specialist → Skeptic → Director 审阅 → 最多两个补证 → Director 晨会。报告、补证和新解释均追加，旧报告不覆盖。Confidence 是未校准的自评，不是 Accuracy。来源核对与取舍见 [External Prior-Art Review](WAR_ROOM_PRIOR_ART_REVIEW.md)。真实 Provider 端到端仍待有效凭据验证，不把模拟通过称为真实分析完成。

DSH真实运行/源码结论见 [Prompt / Agent Architecture Review](PROMPT_AGENT_ARCHITECTURE_REVIEW.md)。金融底座继续保留，新增独立研究应用层；可选DSH独立profile，不修改安装包或通用应用，不成为云端依赖。当前 War Room 使用独立 app-layer Python Session；DSH 交互适配器尚未实现。

外部源码持续学习升级为 [Agent Architecture Watch](AGENT_ARCHITECTURE_WATCH.md)：周度调度 → 版本/许可证与路径diff → 追加架构Review Case → 源码审查/隔离原型/验证/人工批准。只观察不自动采用，新增DSH安装身份和公开观测锚点分离。

2026-10-06。目标是主动研究事实、预期、定价与反应，而不是为用户已有立场找证据。运行无需 Codex；没有 AI 密钥时继续采集、计算、归档与展示。

## 一张架构图

```text
既有 Gold Providers ─────────────┐
官方 FX / 央行 / OECD / 日历 ─────┼→ Source Registry / 原始载荷 / 时间与单位契约
                                │          ↓
                                │   Macro Core：事实 → 冻结预期 → surprise
                                │          ↓
                                │   pricing / reaction 契约（无数据就 MISSING）
                                │          ↓
                                │   Gold 驱动图 / Country A vs B 相对宏观图
                                │          ↓
                                │   支持 / 反对 / 窗口冲突 / 去重簇 / 风险与缺口
                                │          ↓
                                │   不可改写 Macro Snapshot + 有时点边界的记忆
                                │          ├→ 可选 AI：选证据 / 查记忆 → 引用式研究摘要
                                │          └→ Gold / FX 共用网页与证据河流
                                │
既有 Gold G001 量化链路 ──────────┴→ 原模型 → Prediction → 到期 Outcome → 原 OOS/表现
                                              （不重训、不回写、不合并宏观票数）

固定外部研究基线 → 每周 GitHub HEAD / release / license / public advisory
                → append-only observation → 持久 PENDING 审查案例
                → 隔离再读源码 → 预登记实验 → OOS → 人工批准新版本
                     （不自动安装、不改研究基线、不改模型）
```

## 模块边界

| 文件 | 职责 |
| --- | --- |
| `macro_core.py` | 资产/国家档案、Evidence、时间、单位、确定性差分/标准化/surprise/真实事件窗口、检索衰减 |
| `macro_sources.py` | 固定 URL、解析器、请求界限、六小时缓存、来源健康和失败降级 |
| `macro_store.py` | 在既有 SQLite 内新增独立 append-only 命名空间 |
| `macro_pipeline.py` | 共享输入组装 Gold / 相对 FX、同窗冲突、冻结、只读投影 |
| `macro_ai.py` | 服务端凭据、有限工具轮次、证据选择、引用和格式校验 |
| `upstream.py` | 只读 GitHub 跟踪、失败 UNKNOWN、持久审查队列 |
| `scripts/macro_workbench.py` | 无 Codex CLI、静态导出、历史快照读取 |
| `web/server.mjs` | 本地只读 API、受同源限制的研究请求，不接收密钥/URL |
| `macro.html/js/css` | 双语研究简报、证据河流、原始字段、档案、上游检查 |

资产接入通过 `ASSETS + COUNTRIES + 资产证据组装`，不复制网站。Gold 和 AUDNZD 已有真实数据；EURUSD/USDJPY 的参考价格与国家档案可运行，但完整双边宏观数据仍待接入。六模块数值实验室继续保留。

## 日常运行与持久化

GitHub Actions 工作日 UTC 06:17：恢复认证加密 SQLite → 检查批准模型代码 hash → Gold 采集/评价/冻结 → 宏观采集/冻结 → 可选中英文研究摘要 → 加密备份 → 公开不可变预测账本 → Pages。周日 UTC 05:23 独立走上游跟踪，不新冻 Gold 方向判断。Actions 可能延迟，不承诺准点盘前。可以手动 dispatch。

同一个 `gold-production` 并发组，不取消正在写状态的任务。`gold-state` Release 保存加密状态；`ledger` 分支只追加预测/结果。恢复或模型 hash 失败则停止，不空库重置。即使采集/AI失败，已恢复的状态仍尝试备份；失败不发布一份伪造“最新”的页面。当前结构每次发布也备份，因此须监控 Release 容量、执行时间与保留策略；本轮不删历史。

本地研究副本不自动合并云端正式账本。新宏观表沿用备份与内容 hash 验证，避免引入第二个状态系统。

## 持续跟踪：架构中的正式模块

`docs/upstream-watchlist.json` 固定七个已读 commit、研究路径和许可，研究基线与“上一次观察到的 HEAD”分开。每次检查的 meta、HEAD、release 摘要、HEAD 上的 LICENSE blob、比较文件路径和公开安全公告追加保存。新发布即使 HEAD 不变也可触发审查；检查失败不能等同无更新。compare 至多返回 300 文件，公开公告仅前 30 条，均不能声称完整审计。

变更生成 `upstream_reviews` PENDING 案例；随后无更新的检查不自动关闭案例。当前网页展示观察结果与待审数量，批准/驳回工作由维护者在研究文档与新版本流程完成，尚未开发自动审批器。上游源码、公告、新闻和 release body 一律是不可信数据，不作为执行指令。

三类优先复查：数据/PIT/时间语义；API/依赖/许可/安全；真正有独立验证的新研究方法。后续实验必须记录为何改变、比较基线、锁定 OOS 和失败条件，满足 [Universal Contract](UNIVERSAL_ASSET_RESEARCH_CONTRACT.md)。不因为 star、发布频繁或论文宣传收益自动采用。

## 完成边界

已实现事实、描述性变换、双边假设、冲突、缺口、冻结、有限工具研究员和可部署网站。pricing/OIS、真正事件报价、可靠修订历史、相似事件的条件 OOS 模型仍未取得。`NO CLEAR EDGE` 是验证门槛未通过，不是预测黄金会横盘。更完整的证据图推断与历史类比训练不是本轮已完成能力。
## 当前交付：Vercel 按需 Macro War Room（WR-P3）

此增量优先于下方历史 GitHub Pages/每日 AI 流程说明。GitHub 只负责代码版本与定时基础数据；Vercel FastAPI 提供研究交互，Vercel Workflow 分步调度团队，独立 PostgreSQL schema 保存研究事实与运行索引。模型 Secret 只属于服务端环境变量；浏览器只提交资产、provider/model 和研究请求 ID。

研究前先由程序组装并冻结 Research Pack。Director 派题、Specialists 调查、Skeptic 反证、Director 有限补证，最后由 Chief Researcher 汇总；不是五个独立聊天机器人。Gold 判断/Outcome 账本继续只读，不受研究员改观点影响。每日定时任务中的所有 AI 调用已取消。[完整部署配置与剩余验收](VERCEL_WAR_ROOM.md)。

