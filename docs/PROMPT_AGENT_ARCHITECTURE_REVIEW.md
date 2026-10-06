# Prompt / Agent Architecture Review — 2026-10-06

## 产品实测

实际打开本机 `http://127.0.0.1:3014/` 并等待加载：主页首先是原始值、原生观察期变动、NO CLEAR EDGE，随后是 pricing / reaction 缺口和 AI 未生成。没有研究任务、研究员工作记录或可恢复问答。WHAT CHANGED 中五个观测期的变化不能称为过去二十四小时新闻；利率与价格的最后观察日还不同。

修复目标是先讲事实、机制、反证和观察点，再允许钻到来源与公式。不能靠把 UNKNOWN 改成确定结论改善体验。线上浏览器绑定曾超时，本地等价页面已体验；不是新产品线上验收。

## 固定源码与已阅读范围

| 项目 | 版本 | 实际已读源码 |
| --- | --- | --- |
| 本机 DSH | 产品0.2.0-rc.2，build `04f392c9ddd144fa426da2045178797da6db6c11` | root/package.json、dsh-desktop-host/lib/cli.js；下述包的真实编译JS、README和部署patch |
| TradingAgents | `1394a3f72aa4393e1a98f51b382434c4b4c2d972` | analysts/news_analyst.py、analysts/turn.py、context.py、researchers/bull_researcher.py、managers/research_manager.py |
| FinRobot | `2717499b8e30f242640af08c4ad9afd1113c2d45` | finrobot_autogen/finrobot/agents/workflow.py、prompts.py、agent_library.py |

DSH安装包SHA256：`983ca71114e6dfd353fc79af5a1f9481a250ee64c2a3c757673029b811b23bc2`。隔离解包路径为忽略目录 `research_data/prior_art/dsh-installed-20261006`。安装build的GitHub API返回 **422 No commit found**；公开HEAD `5badb15009ae1756c3afe0ae0cef1faafc290ccc` 只是监控锚点，不能声称等同本机版本。clone网络失败不代表没有阅读真实安装源码。

## DSH Agent / Prompt / Session 机制

- `dsh-agent/lib/index.js`：Registry委托factory创建/恢复；agent scope与事件subject绑定；model selection把模型切换写入历史。
- `dsh-agent-loop/lib/index.js` createAgent/setupAndPublish/resume：准备Session、获得持久化写句柄、运行setup、发布agent。resume显式打开排他句柄、读日志、追加中断修复，再发布。每步组装prompt/context/tools，prepareCall解析真实provider能力，工具与失败结果进入日志。
- `dsh-system-prompt/lib/index.js`：有序named sections、动态context、变量和scoped tool schemas；同名agent section覆盖全局section；插值不二次扫描；assemble waterfall后仍执行complete / suppress规则。金融persona应为独立scope，不是用户文本里假扮角色。
- `dsh-tools/lib/index.js`：明确执行的JSON Schema子集、作用域注册、sandbox escalation、调度与输出校验。schema不是授权，不能给任意shell再只靠prompt限制写模型。
- `dsh-sdk-jsonrpc-server/lib/index.js` initialize/prompt/createSession：handshake等待composition并验证route；prompt只返回inbox messageId，结果走session.event/status。**createSession只调用agents.create；SDK wire没有cold resume、per-prompt cancel或close。**底层能恢复不等于SDK已提供。
- `dsh-sdk-protocol/lib/index.js`：逐行stdio JSON-RPC；stdout不能混入普通日志。
- `dsh-sdk-minimal/cordis.patch.yml`：完整独立组合，不继承base；默认可写shell、JSONL和DeepSeek adapter，不带managed credentials/web/compaction。不能原样作为金融生产默认权限。
- `dsh-sdk-app/cordis.patch.yml`、`dsh-base/cordis.patch.yml`：profile叠patch；config整行替换不是深合并。base加载更多产品工具，不能盲用。
- `dsh-llm-pi-ai`：多provider/OpenAI-compatible与按请求凭据解析。SDK仅自动fallback到DeepSeek，其他adapter须先注册。
- `dsh-experimental-agent-team`：durable roster/messages/CAS task board值得借鉴；实验接口、没有稳定承诺、不支持多进程团队或独立cwd，不能当成既定生产能力。
- `dsh-tool-web/lib/index.js`：搜索/抓取经ctx.web能力seam；外部材料是不可信数据。工具名称存在不等于search provider已配置。

实际运行 `python scripts/dsh_runtime_probe.py`：启动F:/DSH包内CLI、独立DSH_HOME、patch禁用shell；initialize返回deepseek-harness-sdk-runtime；shutdown成功、退出码零、无诊断、无LLM调用、安装hash不变。此验收证明composition/transport活着，**不证明模型、金融工具、恢复或桌面交互已验收**。

## 外部金融Agent：采用与拒绝

TradingAgents News Analyst的date/instrument/language注入、具名tools、MessagesPlaceholder与工具预算后的wrap-up值得借鉴。现代版本支持FRED/预测市场/非股票identity，不能笼统称为仅股票。

但Bull Researcher仍包含公司增长/竞争优势等股票先验，且预设为多头辩护；容易造成确认偏误。Research Manager的Buy/Overweight/Hold/Underweight/Sell是投资计划，不是本产品证据协议。采用职责、预算与结构化交接；拒绝固定多空辩手、投票、交易建议和强制方向。

FinRobot role/leader/profile拼装与toolkit分配清晰；leader每次发一个任务并检查反馈值得借鉴。但TERMINATE文字不是durable完成证明，SingleAssistant.chat结束reset历史不满足ASK THIS ANALYST，UserProxy默认use_docker=False可执行本机代码不符合只读边界。使用task/result/uncertainty/handoff数据结构，不复制stock profile或任意代码执行能力。

## ADR-WR-001：边界决策

金融底座留在Digital Oracle，War Room为独立应用层，不修改Gold G001。先建立与runtime无关的任务、金融只读工具、持久会话、报告校验、晨会协议，沿用服务端provider配置。Agent产物不写models/predictions/outcomes。

DSH作为可选本机runtime adapter与第二应用面，**不成为云端日常运行硬依赖**。实际SDK缺我们需要的恢复/取消契约，默认权限不合适，桌面安装不应成为GitHub Actions前提。DSH adapter须独立profile/home/tool scope，显式调用底层resume；不改asar、正常home或全局persona。实验失败只影响独立进程。

团队不是投票：Director提出待证问题 → Rates/Events取证 → 资产specialist连接机制 → Skeptic查时点错配/重复/更简单解释 → Chief保留分歧并综合。仅实际执行成功显示completed；无模型时只能标注“代码生成阅读指南”，不能冒充团队已工作。

数字由确定性renderer产生；AI引用ID。新增资料记录取回时点、source/hash/retrieval理由、first-seen，不回写旧snapshot。ASK继续snapshot identity、成员任务、已读证据、工具结果和历史对话，不是stateless chatbot。

## 尚待验收

真实provider取证、重启后追问、预算/取消/损坏日志、注入隔离；Chief facts→mechanism→expectations→pricing→reaction→conflict→judgment→watch；五分钟新手阅读；DSH桌面回归；云端无Codex依赖；Gold字节与冻结hash不变。测试数量不替代产品验收。
