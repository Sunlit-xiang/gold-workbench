# Agent Architecture Watch

已研究GitHub项目是长期研究来源，不是一次性参考书。固定观测锚点、许可证、源码路径与采用状态在 `upstream-watchlist.json`。

## 运行架构

现有 `.github/workflows/gold-daily.yml` 周日UTC05:23执行 `scripts/gold_cloud.py --upstream`，共享production concurrency及认证加密SQLite恢复/备份。旧版云端已部署该调度；**新增DSH/architecture分类尚须发布才能进入云端**。GitHub任务可能延迟，不能保证准点。

本机：`python scripts/macro_workbench.py upstream --db research_data/oracle.sqlite`。每次追加upstream_observations；失败是UNKNOWN、不覆盖上次成功HEAD。后续无更新不自动清除PENDING。

观察HEAD、release、license blob、archived/rename、前30条公开security advisories。归类prompt、agent-loop、routing/team、memory/session、tools/permissions、provider、UI和schema；重命名同时检查旧路径，目录按边界匹配。GitHub compare达到300文件或diverged/behind时标记INCOMPLETE，必须隔离checkout补齐，不将未列出路径当成没变化。没有advisory不是安全证明。

DSH安装版本/build/hash与公开HEAD分开。安装commit在GitHub不可查询；公开baseline只是监控锚点，不是已批准runtime。外部标题/release body是数据，绝不执行其指令。

## 待审架构事件

upstream_reviews追加稳定case ID、observation ID、kind、affected areas、changed paths、diff coverage和PENDING。门槛固定为：**源码审查 → 独立原型 → 验证 → 人工批准**。

审查需说明：变化解决什么问题；是否改变prompt/context/tools；恢复与权限是否改变；本项目是否需要；最小复现实验；失败条件与恢复路径。普通logo/README变更不伪装成架构突破。没有自动updater、安装、prompt变更、基线晋级或权重调整。

每周优先审破坏性权限/schema/session变化，再审能带来独立研究能力的变化。每月回顾pending；仅人工追加审查事件可关闭，不能覆盖旧历史。新增项目必须记录实际已读源文件、commit、许可证与采用/拒绝理由。参数修改仍走Universal Asset Research Contract。当前没有自动或UI人工审批能力。
