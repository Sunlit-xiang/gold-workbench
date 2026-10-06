# FX：Relative Macro，不复制 Gold 系数

共享研究流程和网页，领域关系必须是 Country A vs Country B。配置已登记 US/Fed/BLS/BEA、AU/RBA/ABS、NZ/RBNZ/StatsNZ、EA/ECB/Eurostat、JP/BoJ/统计局。

## AUDNZD 首个相对宏观例子

```text
AUDNZD（NZD per AUD）
├─ 相对政策：RBA vs RBNZ、OIS forward path、名义/实际利差与可成交 carry
├─ 相对基本面：通胀、就业、增长、住房/信用
├─ 相对出口：澳洲铁矿石/中国需求 vs 新西兰乳制品、两国贸易条件
├─ 全球风险与资金：风险偏好、拥挤/衍生品、不同国家敞口
└─ 事件：两国 surprise → 已定价程度 → 同步 FX/rates reaction → 条件验证
```

ECB 两种报价均为每EUR单位，故 `AUDNZD = NZD_per_EUR / AUD_per_EUR`。展示90日参考价格，非外汇券商成交行情。趋势以5原生观察 log return 描述，不设置未来方向。

AU现金目标与NZOCR先分开显示；仅日期精确匹配才作 `AU_target − NZ_OCR`。两国月度隔夜代理仅同月比较。`Δspread_bp = 100 × (spread_percent_t − spread_percent_previous)`。政策利差水平不等于未预期路径或可执行套息，故仅 context、不设固定正方向。目前 AU/NZ官方在线请求在本机失败，NZ隔夜月度源停在2024-12；旧同月差必须显示 STALE，不能与更新的澳洲值拼成“现在的利差”。

## EURUSD / USDJPY

EURUSD：比较EA与US的增长/通胀/政策路径与利差、能源冲击和融资条件，不是“DXY反向”。当前有ECB价格与Fed/ECB官方事件标题，双边数字宏观尚缺。

USDJPY：比较US与JP政策、工资通胀、套息/风险及干预事件；`USDJPY = JPY_per_EUR / USD_per_EUR`。当前有参考价格、国家档案、Fed标题，BoJ预期路径与双边数字待接入。

四资产共用 Evidence/Snapshot、文档、AI工具与网页，但各自展示真实缺口，不为了数据完整度一致而捏造变量。本轮不发布 FX 方向预测、不产生假 Accuracy。只有相对因素在基线之外通过独立 PIT/OOS 才注册预测模型。

## 下一步优先顺序

先稳定有发布时间与维护能力的AU/NZ官方政策源；再接相同期限 OIS/forward 和 pre-release consensus/FX事件报价；随后统一ABS与StatsNZ通胀、就业定义及vintage；最后研究相对出口、住房与信用是否提供独立信息。品种差异和单位转换是研究的一部分，不能依赖LLM看名称自动换算。
