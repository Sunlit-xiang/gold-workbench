# 实际验收记录 · 2026-10-06

此文件记录已执行行为，不把“实现接口”称作“取得合格数据”，不把网页部署称作预测Edge。

## 代码与测试

- 主工作区既有dirty改动保留；独立交付工作副本发布34个文件变化，155个白名单源文件经过凭据扫描。SQLite、研究clone、原始归档、.env不进入源码发布。
- 全部 `python -m unittest discover -s tests`：297通过。`node --test web/test/*.test.mjs`：11通过。macro.js语法检查通过。云端重复执行回归通过。
- 本地批准Gold模型的 `code_hash == code_hash()` 为true，交付diff没有任何 `asset_*.py` 或 `providers/research_history.py` 变化，云端同一批准hash检查通过。
- 加密SQLite备份/恢复测试覆盖新增macro表。真实云端恢复旧账本、增量新增macro表、再次加密上传均成功。

## 数据与上游

- 本地真实Gold全量collect：12条序列成功，未造模拟值；云端完整collect亦 `source_errors={}`。
- ECB参考交叉汇率、Fed/ECB官方feed、FRED/OECD AU/NZ隔夜代理请求成功；NZ代理最新仍在2024-12，网页展示STALE，不能与AU更新月份拼接。RBA/RBNZ请求失败，本地与本轮云端均保留UNKNOWN。
- 七个固定外部研究仓库实际检查并保存HEAD、release、license与公开advisory状态；全为available。本次没有HEAD变化。周度schedule已经提交，不能声称已经跨多周运行验证。
- consensus日历MISSING；分钟级reaction/OIS仍MISSING。AI工具路径模拟provider通过，但未配置新有效密钥、未付费请求DeepSeek/Kimi，线上 `ai_summary.status=not_generated`。

## 网站与发布

- 本地浏览器实际操作：Gold首页与河流、实际利率公式/原始值/时间展开、AUDNZD数据健康、宏观档案链接、七仓上游页、无key配置窗口、英文切换。最终本地浏览器error/warn日志为空；历史snapshot API实际JSON读取成功。
- 已上线：[工作台](https://sunlit-xiang.github.io/gold-workbench/)。新首页、Gold/AUDNZD/EURUSD/USDJPY JSON、macro-snapshots JSON均由HTTP实际读回确认。
- IAB打开公网页面两次加载超时，因此不声称公网浏览器像素验收通过；公网HTTP读取和GitHub Pages部署已确认，本地同代码UI已验证。
- 发布：[37433062259](https://github.com/Sunlit-xiang/gold-workbench/actions/runs/37433062259) success；完整采集/冻结/评价/发布：[37433582634](https://github.com/Sunlit-xiang/gold-workbench/actions/runs/37433582634) success。
- 发布commit `79ac0ef22aa4508e16f16acd50c29ee1acfd7299`；文件树 `b0ce740b2d0db251e86849380bb503593df70eb5` 与本地已审查树完全一致。Git HTTPS连接失败后通过官方Git数据库API创建相同tree并非强制推进main，旧commit与历史保留。
- 发布前56条Gold冻结预测的去除outcome字段后canonical列表SHA256为 `89f70cf14e89917a16805c8ef6a5a399c71e1502e2577d3b5580feed10468476`；完整pipeline后旧56条hash相同，新增4条至60条。只允许到期outcome追加，不能改预测。
- 最新Gold方向冻结 `2026-10-06T08:04:13.316358+00:00`；宏观快照 `2026-10-06T08:04:17.635548+00:00`。Gold24叶中12条当前available，AUDNZD13叶中2条available，两份宏观冻结归档已出现。

## 交付工作副本

源码目录 `F:\Codex_project\trader\background_engine\digital-oracle` 保留原user改动。独立 `.delivery/repository` 切到 `published-macro-v1`，其HEAD与已发布commit一致，原本地main commit保留。后续发布使用 `git push origin HEAD:main`，不要force、不要清除本地研究副本。API fallback脚本隔离在 `.delivery`，不成为每日生产依赖。

本文件和Snapshot的验收补充为本地维护记录，部署代码已通过上述云端验证；不因为追加验证说明再触发一次模型运行。长期准确率、定价识别和事件条件预测仍需独立研究证据。
