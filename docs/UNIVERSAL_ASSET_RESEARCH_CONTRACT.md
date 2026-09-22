# Universal Asset Research Contract · 通用资产研究协议

版本1.0，2026-09-18。所有资产与后续模型版本必须遵循；由项目AGENTS.md引用为底层研究规则。

**定义标的 → 外部先验 → 驱动图 → 通用因子映射 → 资产专属因子 → 去重 → PIT数据 → 简单基线 → 增量实验 → OOS → 冻结 → 网站工作台。**

1. **标的**：锁定instrument、venue、币种、报价字段、现货/期货/代理、日界与horizon。代理不继承原资产的验证资格。
2. **外部先验**：阅读论文/机构方法和canonical implementation；标明解释/预测、原研究期限、OOS证据、失败情形。不得把别人的年频结论当成本项目日频证明。
3. **驱动图**：按经济机制分族；复用收益/利差/波动等数学模板，但经济方向与期限必须资产特异。
4. **叶节点**：每个有数值的叶必须保存源、值、单位、真实或保守可用时点、变换窗口、尺度、Score、系数/权重、贡献、验证等级。Context / Predictive / Risk分离。
5. **去重**：共同原始源、nominal=real+breakeven、动量/均线、同一事件市场反应按经济簇处理；不能按名称数独立票。
6. **PIT**：发布时间不同于观察日期；保存原始载荷hash与first_seen。修订历史、连续合约未审计历史必须标reconstructed/exploratory；不能用人为延迟声称彻底修复vintage问题。
7. **实验前登记**：假设、证伪条件、基线、有限候选、训练/holdout边界、信号与结果时刻、缺失排除、主指标、停止条件。不是订单策略就不报告净P&L。
8. **基线与增量**：至少Neutral、固定方向、简单趋势；逐族添加与移除，比较相同样本和相同coverage。新增复杂性必须证明增量，而非只展示漂亮拟合。
9. **OOS**：时序训练、成熟标签、purge/gap；重叠D3/D5报告非重叠计数和时间块区间。末段封存，开封留痕；失败与NONE保留。没有证据不调参重跑寻找60%。
10. **冻结**：模型manifest包含代码、参数、输入契约和训练截止；prediction保存完整证据、issued_at、baseline规则。live / reconstructed research严格分账。历史不UPDATE/DELETE。
11. **结果与校准**：代码到期追加Outcome；同时报Accuracy、Coverage、缺失、Flat与弃权。每日采集，周/月报告；参数修改新版本，人工明确晋级，不自动覆盖。
12. **工作台与交付**：注册资产配置与Factor Tree，复用同一API/页面；显示真实数据能力、模型状态、账本与来源。无AI可完成采集、计算、冻结、回看。研究员报告必须解释哪些方法无效、最大弱点与下一项最有价值的实验。

## 准入等级

`disabled → context / research_candidate → research_oos → forward_validated`不是自动晋级阶梯。Context可永久保留而无需成为预测因子；OOS不保证live有效；统计与数据质量任一不合格都不能认证Edge。

## Gold首例

研究登记：[Gold实验协议](GOLD_EXPERIMENT_PROTOCOL.md)。方法说明：[Gold研究员手册](GOLD_RESEARCH_HANDBOOK.md)。可执行入口：`python scripts/asset_pipeline.py --help`。其他资产必须注册自己的AssetSpec，不复制一套网站或偷偷沿用Gold系数。
