# Gold Workbench 操作手册

项目：`F:\Codex_project\trader\background_engine\digital-oracle`。Python ≥3.10，依赖见requirements-gold.txt，Node ≥18。不需要Codex登录或DeepSeek密钥来运行Gold量化链。

## 首次初始化

在项目目录执行：

```powershell
python -m pip install -r requirements-gold.txt
python scripts/asset_pipeline.py collect
python -m unittest discover -s tests -p test_asset_research.py -v
# 开封不可逆；先阅读实验预注册。不要每天重新跑研究挑参数。
python scripts/asset_pipeline.py research --open-holdout
python scripts/asset_pipeline.py publish-shadow
python scripts/asset_pipeline.py freeze
python scripts/asset_pipeline.py evaluate
python scripts/asset_pipeline.py calibrate
powershell -NoProfile -File scripts/start_gold_workbench.ps1
```

已有初始化结果时不要重复publish-shadow来制造“新模型”。同一天同model/horizon的freeze幂等；原数据、报告、模型、prediction和outcome拒绝UPDATE/DELETE。代码数值模块改变后，旧model hash不匹配将拒绝新预测，须明确发布新版本；这不是自动校准。

## 日常独立运行

```powershell
python scripts/asset_pipeline.py daily
powershell -NoProfile -File scripts/install_gold_task.ps1
powershell -NoProfile -File scripts/install_gold_workbench_task.ps1
```

daily执行采集、到期评价、冻结、追加描述统计；不会重新训练或切换模型。Windows任务每天北京时间14:10（UTC06:10）运行，错过后允许补执行，禁止并发重入。任务需要Windows用户已登录，**不要求打开Codex**。电脑关机、断网或退出Windows会影响任务；若要无人登录仍全天候运行，另行设置服务身份/常开主机，不能宣称当前本机永不离线。

日志在research_data/logs。Task Scheduler查看DigitalOracle-Gold-Daily的LastTaskResult。安装器若权限不足会明确失败，不暗中添加其他自启动机制。新预测以实际issued_at为准，不把错过日期伪造补成live历史。

本机已注册`DigitalOracle-Gold-Daily`，手动触发的独立任务烟测LastTaskResult=0；另注册`DigitalOracle-Gold-Workbench`，在Windows登录时启动3012本地网页服务。网页自启动与每日采集分开，均不依赖打开Codex。退出Windows后停止或不能运行的限制仍然存在。

## 数据与复现

- 数据库：research_data/oracle.sqlite（git忽略，含较大原始载荷）。SQLite WAL保护并发，证据表append-only且读时核验hash。
- 每次collect新建dataset版本、保留原始来源URL/请求参数、first_seen和payload；不覆盖旧历史数据。
- `python scripts/asset_pipeline.py dashboard`输出页面同源JSON。
- `python scripts/asset_pipeline.py export-research --output research_data/exports/G001.2`导出各horizon完整历史forecast CSV、统计和月度系数JSON；拒绝覆盖既有目录。它是历史研究导出，不是live预测账本。
- `python scripts/asset_pipeline.py backup --output research_data/backups/oracle-YYYYMMDD.sqlite`使用SQLite一致性备份，拒绝覆盖已有目标。
- 实验报告保存每期forecast、标签、回归训练边界和系数；历史实验不插入live账本。H4明确不可评价。
- 当前观测日不是盘前即时价格；baseline来自发出UTC日期之后的首个有效日收盘，D1/3/5再数对应观测日。缺少交易所精确日历，超过4日行情间隙或16日等待上限会拒绝评价；短缺口识别仍是限制，不能认证严格交易日PIT。
- Outcome当前只追加首次评价；供应商事后修订不会改旧Outcome。发现错误应保留原记录、另立supersedes修正研究版本；尚未提供人工修正CLI，禁止直接SQL UPDATE。

## 运行边界

本地站点只监听127.0.0.1，未发布公网。公开网站不能直接复制含授权行情的数据库，需要另外审查数据再分发许可、认证与服务部署。

数据库所有者可以绕过触发器；hash与备份提供可检测性，不是不可破解的防篡改。当前不是下单策略、未计算交易费用或成交质量，不报告Sharpe和可交易净利润。
