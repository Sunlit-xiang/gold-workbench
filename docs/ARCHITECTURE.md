# Macro Evidence & Pricing Workbench · MEP-1.0

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
