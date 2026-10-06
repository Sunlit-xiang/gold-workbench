# Evidence-bound AI researcher

## 当前 War Room：WR-P2（2026-10-06）

新增 `research_team.py`；保留以下旧单研究员接口，不混同两个报告版本。团队机制见 [External Prior-Art Review](WAR_ROOM_PRIOR_ART_REVIEW.md)。独立 research_sessions / requests / turns / materials / runs，所有研究追加。每个研究员可恢复其当日研究和私人追问历史；私人问答不导出 Pages。研究者可以读官方白名单网页/feeds、冻结证据、PIT历史和同行报告，不能执行 shell 或修改金融模型。

本地：`python scripts/war_room.py team --asset gold --language zh`，Provider/Model 可经 stdin JSON 设置；网站同源 API 调用同一路径。模型调用未配置时不创建虚构研究。默认有限工具轮次；主管补证最多两个，审阅失败不绕过生成共识。所有数字仍由代码展示。

云端：Actions Variable `ORACLE_TEAM_ENABLED=1` 启用团队，配合 `ORACLE_AI_PROVIDER` 和相应 Secret；默认 `0` 保持原流程、避免无意增加调用成本。既有日常调度继续独立于 Codex。中英文各一个团队流程；不保证任务准点，也不宣称未配置时有晨会结果。网页 Provider 窗口不接收密钥。

**当前验收边界**：页面真实打开、DEMO 交互和模拟 Provider 协作测试不是金融研究实调用。缺少有效凭据时，真实晨会与真实连续追问仍未验收。GitHub Pages 是静态归档；持续追问只在本地研究服务可用，不假装 Pages 自带交互后端。

AI 不是唯一大脑，也不只是复述程序的纯文本解释器：它先看到证据目录，自行选择具体证据并可检索历史记忆，检查反证、时点、重复与缺口，然后给出有引用的跨市场假设。所有金融数字仍来自代码。

## 运行边界

工具只有 `select_evidence(ids)`、`query_memory(topic)`；最多3轮模型调用、每轮最多4个工具。首次必须请求 evidence selection；没有读取实际证据就不能保存成功研究。模型/工具输入中外部标题、release body、记忆均标记为不可信数据。

摘要保存 snapshot ID、证据 hash、provider/model/language、生成时间、每个 claim 的 evidence IDs、stance、uncertainties 与 tool audit。未知 ID、数字型 claim 文本、BUY stance、伪造 Edge 被拒绝。数字由网页从证据渲染，不让 LLM 计算。语义是否真的成立仍需研究者质疑，格式校验不能证明因果。AI 失败不修改预测，不把它变成空头/中性意见。

目前正文事实抽取、联网通用搜索、专业事件标签、人类审批与历史条件回报类比尚未实现；已具备有限选证据和 topic memory 的真实工具路径。未用现有公开过的密钥做付费实调用；工具路径已用模拟 provider 测试，真实服务商兼容性须配置新密钥后验收。

## 配置（密钥只在服务端）

| provider | 默认 HTTPS 地址 | Secret |
| --- | --- | --- |
| deepseek | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` |
| kimi | `https://api.moonshot.ai/v1` | `MOONSHOT_API_KEY` |
| kimi-cn | `https://api.moonshot.cn/v1` | `MOONSHOT_API_KEY` |
| openai | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| openai-compatible | 服务端 `ORACLE_AI_BASE_URL` | `OPENAI_COMPATIBLE_API_KEY` |

设置 `ORACLE_AI_PROVIDER`，可选 `ORACLE_AI_MODEL`。默认 off，数据系统仍运行。DeepSeek 默认 deepseek-chat；Kimi 默认模型与服务商账户可用模型需核对，可通过 MODEL 覆盖。自定义地址只能由可信维护者配置 HTTPS，不接受浏览器传来的 URL。

云端：仓库 Settings → Secrets and variables → Actions。Secret 配 key，Variables 配 provider/model/base URL，随后 dispatch 工作日 pipeline；Gold/AUDNZD 按中英文各生成一份。Pages 是静态网站，只展示这些归档摘要，**不能点击直接调用后台 AI 或安全保存 Secret**；配置窗口提供安全设置链接。

本地：在运行 Node/Python 的进程环境中配置 key/provider/model，再启动服务；`.env.example` 只是字段模板，不自动读取 `.env`。本地页面可选择 provider/model/language 发起研究请求，不接受 key。API 做 loopback host、同源与字段白名单检查，一次一个研究请求。不要对公网暴露这个开发服务，若需要多用户实时研究应另建带身份验证、限流和密钥管理的后端。

```powershell
# 在可信本地终端设置环境变量，不把密钥写入 Git 或网页。
$env:ORACLE_AI_PROVIDER = 'deepseek'
$env:ORACLE_AI_MODEL = 'deepseek-chat'
python scripts/macro_workbench.py research --asset gold --language zh
```

曾经在聊天中公开的 key 应撤销换新，不沿用。旧 Gold 页面已移除 BYOK 表单与浏览器直连；现有 Provider/Agent 框架保留，日常生产不依赖 Codex SDK。
