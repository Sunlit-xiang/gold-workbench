# Macro War Room · Vercel / WR-P3

入口：[Macro War Room](https://macro-war-room-pi.vercel.app/)。项目：[Vercel macro-war-room](https://vercel.com/sunlit-xiangs-projects/macro-war-room)。
部署保护保持启用；如出现登录页，用项目所属的 Vercel 账号访问。

## 产品边界

打开网站 → 选择 Gold（GC Proxy）或 AUDNZD → 开始研究 → 显示真实团队阶段 → Chief Researcher Brief。
AI 全部按需；GitHub 的定时任务只采集基础数据、冻结/评价确定性 Gold 判断、更新只读公开资料，不调用研究团队或自动 AI 解读。

Research Pack → Director 派题 → Liquidity / Rates / Cross Asset / Asset Specialist（可选 Events）→ Skeptic → Director 审阅及最多两次定向补证 → Chief Researcher。

## 服务端与持久化

- `app.py`：FastAPI，同域页面与 API；没有浏览器密钥输入框。
- `warroom_cloud/pack.py`：先读取 GitHub 公开归档，再通过已有 Provider 刷新登记的数据源；失败保留明确缺口/陈旧标记。
- `warroom_cloud/workflows.py`：Vercel Python Workflow SDK **beta**，版本固定为 0.11.0。每个研究员是独立有界 step，返回队列后自动继续；不依赖浏览器维持运行，也不依赖 Codex。
- `warroom_cloud/store.py`：独立 PostgreSQL schema `oracle_war_room`。原始资料包、请求、报告、会话、官方资料及最终结果 append-only，数据库 trigger 拒绝 UPDATE/DELETE。可变 jobs 表仅用于运行状态与索引，不是事实账本。
- 每个 run 有独立 ID；角色会话绑定 run / snapshot / language / prompt version。step checkpoint 避免已完成单元重复收费；不自动重试不确定的付费调用，已受理但未完成的单元明确保留。
- 默认同时只接受一个研究任务、每天最多八次完整研究、每角色/每 run 最多十二次追问。重复 request ID 复用任务，契约不一致则拒绝。
- Gold SQLite、预测与 Outcome 不部署成可写云端数据库；工作台只代理读取其 GitHub 公开冻结文件，绝不写回。

## Research Pack 契约

保存组装时间、原始 snapshot ID、每个叶节点数值/变换/来源/观察日/available_at、刷新成功及失败列表、历史证据 ID 与缺口。
PIT 历史只来自原先归档的 first-seen 记录。今天下载的 FRED / Yahoo 历史是 latest-vintage，不冒充当时已知的数据；数据修订问题不会因为上传到 Vercel 而消失。
行情目前是已完成日频参考数据，Gold 仍为 GC Proxy；不是实时可成交 XAUUSD，也不能用于事件后分钟反应。
AI 首先读取资料包中的证据。只有读过证据并明确写出待填补 gap，才可调用可信官方源工具。HTTPS、域名、端口及重定向逐一限制；没有自由全市场联网搜索。

## 最后统一配置（Vercel 项目 macro-war-room）

在 Settings → Environment Variables 配置到 **Production 和 Preview**，然后重新部署：

| 必需项 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | 新的 DeepSeek Secret。GitHub Secrets 不会自动同步到 Vercel，也不可从 GitHub 回读。 |
| `DATABASE_URL` | Storage 中连接 Neon PostgreSQL，可先选免费档；服务端连接串，不公开到浏览器。 |
| `WAR_ROOM_PASSWORD` | 至少二十字符的随机访问密码，保护收费 API。它不是模型密钥；在网页 AI 配置窗口登录后使用 HttpOnly / SameSite / Secure cookie。 |

可选 `MOONSHOT_API_KEY` 支持 Kimi 国际/中国，`OPENAI_API_KEY` 或 `OPENAI_COMPATIBLE_API_KEY` + 服务端 `ORACLE_AI_BASE_URL`；页面只选择 provider/model，不选择任意请求网址。
未完成配置时，网站保持可读且清楚列出缺项；不能把测试 fixture 或 DEMO 当成成功研究。
Vercel 默认部署保护可能要求先登录同一 Vercel 账号；不要为测试绕开或关闭账号级保护。

## 验证与剩余验收

2026-10-06：生产部署 `09115ff` 已 READY，授权 HTTP 读回首页 HTML、JS、CSS 均为 200；Gold / AUDNZD API 与 Gold 只读归档接口为 200。修复了 Vercel bytecode 路径导致的静态文件 503，并显式打包 `web/public/**`。
本机同一 FastAPI 应用已验证首屏、点击开始研究进入配置提示、无模型密钥输入框。Codex 浏览器对 Vercel 域名导航返回 client block，不能据此宣称线上浏览器端到端验收完成。
六个新增云端契约测试、既有 Python 与前端测试分别验收；模拟模型只出现在测试中。用户决定最后统一配置，当前生产未设置上述三项，不存在真实 AI 团队结果。

自动测试覆盖无 Secret 状态、同源/访问保护、浏览器密钥参数拒绝、资料刷新失败、禁止 Gold 写表、真实 schema 的团队调用/工具引用、Chief 交接及已完成 checkpoint 重用。
测试中的模型和存储替身只证明代码契约，不代表真实 DeepSeek 或云端 PostgreSQL 已验证。
统一配置后还须实际运行一次：观察阶段 → 关闭/刷新页面 → 重连 run → 完成 Brief → 追问 → 查看数据库 immutable trigger → 检查收费与错误日志。这是上线交互闭环的最后验收，不可用“测试通过”替代。

参考：[Vercel Python Functions](https://vercel.com/docs/functions/runtimes/python)、[Python Workflow SDK](https://workflow-sdk.dev/docs/getting-started/python)、[Environment Variables](https://vercel.com/docs/environment-variables)。
