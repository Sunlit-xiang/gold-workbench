# Incremental migration / operational verification

## KEEP / REFACTOR / REPLACE / DELETE

KEEP：现有 Provider/Agent、Gold批准模型、原始数据与冻结 ledger、既有历史验证/消融/Calibration、GC Proxy标识、加密恢复、Pages与六模块数值实验室。没有修改任何 `asset_*.py` 或 `providers/research_history.py` 的批准计算字节，没有自动晋级模型。

REFACTOR：新增 Macro Core / source registry / independent namespace / Country profiles / hypothesis graph；新首页先看变化、预期、定价、反应、冲突和数据健康，河流支持展开来源与公式。Gold旧入口 `asset.html` 仍可访问，不清除旧功能或历史。

REPLACE：前端密钥输入与直接请求服务商改为服务端环境/GitHub Secrets；新宏观层不合成Evidence Score或强制Current Thesis，旧数值模型仅作为独立实验室。

DELETE（行为）：新闻情绪=预测、当前政策利率=期货概率、日线=事件分钟反应、缺失=0/中性、访问次数=更强因子、上游更新自动改模型。没有执行历史记录或源文件的破坏性删除。

## 本地运行

```powershell
python -m pip install -r requirements-delivery.txt
# 要求已有研究DB；CLI拒绝静默新建空账本。
python scripts/macro_workbench.py collect
python scripts/macro_workbench.py dashboard --asset audnzd
python scripts/macro_workbench.py upstream
$env:PORT = '3013'
node web/server.mjs
```

默认数据库 `research_data/oracle.sqlite`，可 `--db` 或Node的 `ORACLE_DB`。Gold全量刷新仍用既有 `scripts/asset_pipeline.py collect`；宏观 collect 不重训、不冻结新的Gold方向。不要把本地分叉预测覆盖云端。

发布 `scripts/prepare_gold_release.py --output .delivery/repository` 复制白名单并扫描凭据；不复制 SQLite、研究clone、原始归档、.env 或node_modules。独立交付仓库 push 后 Actions 恢复云端正式状态、初始化宏观层、导出Pages。新的 `.env.example` 只有空字段。

## 真实验收记录（不等于研究收益证明）

本轮执行全部Python与Node回归，新增覆盖PIT偏移、单位与共识冻结、未来/非有限值、source失败、去重、命名空间隔离、append-only、加密往返、AI有限工具/引用/无key降级、上游license/release变化与待审保留、API同源/凭据拒收。已执行真实12源Gold collect、ECB FX/官方feeds/澳新隔夜、七仓GitHub检查。TradingAgents隔离最小provider映射smoke通过，未复现完整第三方回测。

本地浏览器实际检查Gold简报、河流实际利率公式/时间/原始数据展开，继续检查FX、历史链接、双语、配置和public发布。最终云端部署结论以 Actions 状态与public HTTP核验为准，不把文件导出称已上线。

## 仍待解决

可靠spot/分钟事件、预期与vintage、OIS、真实流量、语义抽取与类比统计；多用户后端与审批器。原模型和新宏观层分别标示验证地位，不混算成功率。

框架遵守 Universal Asset Research Contract；本轮quant-research约束阻止了在有吸引力的叙事下重新搜索参数。新假设只能进入研究队列，不能通过改页面变成生产Edge。
