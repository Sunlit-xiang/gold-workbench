"""Novice-first reading layer; never turns explanatory context into a prediction."""
from __future__ import annotations

from datetime import timedelta

from .macro_ai import config
from .macro_core import instant
from .macro_pipeline import macro_dashboard
from .research_team import PROMPT_VERSION, ROLES

LABELS = {
    "gold": ("黄金连续期货代理", "Gold continuous futures proxy"),
    "dxy": ("美元指数", "Dollar index"), "real": ("美国十年实际收益率", "US ten-year real yield"),
    "us2": ("美国两年名义收益率", "US two-year nominal yield"),
    "us10": ("美国十年名义收益率", "US ten-year nominal yield"),
    "bei": ("十年盈亏平衡通胀", "Ten-year breakeven inflation"), "spx": ("标普指数", "S&P index"),
    "vix": ("美股隐含波动率", "Equity implied volatility"), "brent": ("布伦特原油", "Brent oil"),
    "cot": ("管理基金净持仓比例", "Managed-money net positioning"), "gld": ("GLD价格（不是资金流）", "GLD price, not flows"),
    "silver": ("白银价格", "Silver price"), "audnzd": ("澳元兑纽元参考汇率", "AUDNZD reference rate"),
}
MECHANISMS = {
    "gold": ("价格变化是已经发生的结果，不是下一阶段预测；这里使用GC代理，不是可成交的XAUUSD现货。", "Price is an observed result, not a forecast; this is a GC proxy, not executable XAUUSD spot."),
    "dxy": ("美元升值通常增加其他币种购买黄金的成本；这是理论渠道，不是每次都成立的预测。", "A stronger dollar usually raises foreign-currency gold costs; this mechanism is not a universally valid forecast."),
    "real": ("黄金不付息。实际收益率上升通常增加持有黄金的机会成本，但收益率也含风险和流动性溢价。", "Gold pays no interest. Rising real yields usually increase its opportunity cost; yields also contain risk and liquidity premia."),
    "us2": ("短端利率反映政策预期与风险溢价，不能直接换算成下次加息概率。", "Short yields reflect policy expectations and premia, not a direct next-meeting probability."),
    "us10": ("长端名义利率与实际利率、通胀补偿重叠，不能重复计为独立支持。", "Nominal yields overlap real yields and inflation compensation; do not count them as independent confirmations."),
    "bei": ("通胀保护需求与收紧政策预期可能相互抵消，不能机械指定黄金方向。", "Inflation protection and tightening expectations can offset; no fixed gold sign is assigned."),
    "cot": ("增仓可能是趋势跟随，也可能是拥挤风险；周度发布不能冒充今天的新消息。", "More positioning may follow trends or create crowding; weekly releases are not today's new information."),
    "gld": ("这里只知道ETF价格，不知道投资者净流入或黄金吨数变化。", "Only ETF price is known, not net inflows or changes in gold tonnes."),
}
ROLE_NAMES = {
    "director": ("研究主管", "Research Director"), "rates": ("通胀与利率研究员", "Inflation / Rates Analyst"),
    "liquidity": ("流动性研究员", "Liquidity Analyst"), "cross_asset": ("跨资产研究员", "Cross Asset Analyst"),
    "events": ("事件与新闻研究员", "Event / News Analyst"), "gold": ("黄金研究员", "Gold Specialist"),
    "fx": ("相对外汇研究员", "Relative FX Specialist"), "skeptic": ("反证审查员", "Skeptic"), "chief": ("首席研究员", "Chief Researcher"),
}


def pick(pair, language):
    return pair[0 if language == "zh" else 1]


def evidence_card(e, language):
    move = e.get("transformation", {})
    label = pick(LABELS.get(e["topic"], (e["topic"], e["topic"])), language)
    value = move.get("value")
    if e.get("display_health", e["status"]) == "available" and value is not None:
        direction = pick(("上升", "rose") if value > 0 else ("下降", "fell") if value < 0 else ("持平", "unchanged"), language)
        fact = (f"{label}在{move.get('from_date')}至{move.get('to_date')}期间{direction} {abs(value):.2f} {move.get('unit','')}。"
                if language == "zh" else f"{label} {direction} {abs(value):.2f} {move.get('unit','')} over {move.get('from_date')} to {move.get('to_date')}.")
    elif e.get("display_health", e["status"]) == "available" and e.get("publication_time"):
        fact = pick((f"官方于{e['publication_time']}发布标题：{label}。目前仅核实标题，正文与预期差仍需调查。",
                     f"Official headline published at {e['publication_time']}: {label}. Full text and surprise still need investigation."), language)
    elif e.get("display_health", e["status"]) == "available" and e.get("actual") is not None:
        fact = pick((f"{label}在{e.get('observation_date')}的观测值为{e['actual']} {e.get('units','')}；没有合格变动窗口。",
                     f"{label} observed at {e.get('observation_date')}: {e['actual']} {e.get('units','')}; no qualified change window."), language)
    else:
        fact = pick((f"{label}目前没有足够新鲜、合格的观测，不能当作中性。", f"No sufficiently fresh qualified observation for {label}; this is not neutral."), language)
    meaning = pick(MECHANISMS.get(e["topic"], (
        "用于描述市场环境；目前没有通过验证的固定方向关系，不能给预测增加一票。",
        "Describes context; no validated fixed directional relationship or extra predictive vote.")), language)
    return {"evidence_id": e["id"], "topic": e["topic"], "label": label, "fact": fact, "mechanism": meaning,
            "stance": e["stance"], "status": e.get("display_health", e["status"]), "family": e["family"],
            "observation_date": e.get("observation_date"), "available_at": e["available_at"],
            "publication_time": e.get("publication_time"), "source_url": e["url"], "source": e["source"],
            "actual": e.get("actual"), "previous": e.get("previous"), "units": e.get("units"),
            "transformation": move, "interpretation": e["interpretation"], "validation": e["validation"],
            "independence_cluster": e["independence_cluster"]}


def board(store, asset="gold", language="zh", now=None):
    if language not in ("zh", "en"):
        raise ValueError("invalid language")
    view = macro_dashboard(store, asset, now)
    if not view.get("id"):
        return {**view, "brief": pick(("先采集可核实数据，研究室不会凭空生成市场故事。", "Collect qualified data first; the room will not invent a market story."), language)}
    cards = [evidence_card(e, language) for e in view["evidence"]]
    available = [c for c in cards if c["status"] == "available"]
    key = [c for topic in (("gold", "dxy", "real") if asset == "gold" else (asset, "policy_spread", "money_spread"))
           for c in available if c["topic"] == topic]
    sentence = " ".join(c["fact"] for c in key[:3]) or pick(("当前可核实的市场资料不足，先看已知事实与待补证据。", "Qualified market evidence is limited; review known facts and gaps first."), language)
    sentence += pick((" 这些是已发生的背景，不等于下一阶段方向优势。", " These are observed conditions, not proof of a forward Edge."), language)
    if asset == "gold":
        drivers = {c['topic']: c for c in available if c['topic'] in ('dxy', 'real') and c['transformation'].get('value') is not None}
        if len(drivers) == 2:
            stances = {c['stance'] for c in drivers.values()}
            if stances == {'oppose'}:
                sentence = pick(("在目前可核实的各自观察窗口里，美元和实际利率都在上升，形成黄金的机会成本逆风；但它们并非同步的今日变化，不能直接证明下一阶段会下跌。",
                    "In their respective verified windows, USD and real yields rose, creating an opportunity-cost headwind for gold. These are not synchronized changes today or proof of a future decline."), language)
            elif stances == {'support'}:
                sentence = pick(("在目前可核实的各自观察窗口里，美元和实际利率都在下降，减轻黄金的机会成本压力；但背景顺风不等于尚未被定价的未来优势。",
                    "USD and real yields fell in their respective verified windows, easing gold's opportunity-cost pressure. A favorable backdrop is not proof of unpriced forward Edge."), language)
            else:
                sentence = pick(("美元与实际利率给出的机会成本背景并不一致，应先解释分歧；这不等于预测黄金会震荡，也不应靠数票强迫方向。",
                    "USD and real-yield opportunity-cost signals disagree. Investigate the conflict; it does not predict a range or justify a majority-vote direction."), language)
    cutoff = instant(view["as_of"]) - timedelta(hours=24)
    recent = [c for c in available if c["publication_time"] and cutoff <= instant(c["publication_time"]) <= instant(view["as_of"])]
    runs = [r for r in store.list("research_runs", 10000) if r["snapshot_id"] == view["id"] and r["language"] == language
            and r["prompt_version"] == PROMPT_VERSION]
    run = runs[0] if runs else None
    reports = {r["analyst"]: r for r in (run or {}).get("reports", [])}
    assignments = {a['analyst']:a['question'] for r in (run or {}).get('reports',[]) for a in r.get('assignments',[])}
    assignments.update({p['analyst']:p['question'] for p in (run or {}).get('process',[]) if p['stage'] in ('investigation','supplement')})
    team = []
    for role in ("director", "liquidity", "rates", "cross_asset", "gold" if asset == "gold" else "fx", "skeptic", "events"):
        report = reports.get(role)
        team.append({"analyst": role, "name": pick(ROLE_NAMES[role], language), "responsibility": ROLES[role],
                     "task": assignments.get(role), "report": report,
                     "status": report["status"] if report else "not_executed", "work_done": bool(report and report.get("work_done"))})
    chief = reports.get("director", {})
    analyzed = chief.get('status') == 'available' and chief.get('phase') == 'final'
    sections = chief.get('sections', []) if analyzed else []
    facts = [s for s in sections if s['kind'] == 'fact'][:3]
    # Do not turn old observations into today's news or synthesize a team opinion without a final report.
    if not analyzed:
        facts = [{'kind':'fact', 'text':c['fact'], 'evidence_ids':[c['evidence_id']]} for c in recent[:3]]
    relationships = [rel for r in (run or {}).get('reports', []) for rel in r.get('relationships', []) if rel.get('kind') == 'conflict']
    situation = {
        'status': 'ANALYZED' if analyzed else 'NOT YET ANALYZED',
        'top_stories': facts,
        'battlefield': next((s['text'] for s in sections if s['kind'] == 'judgment'), sentence),
        'battlefield_kind': 'team_view' if analyzed else 'code_generated_context',
        'debate': relationships[:3],
        'debate_empty': pick(('团队尚未完成讨论，没有可展示的真实分歧。' if not analyzed else '未记录合格分歧；这并不代表研究结论已被证明。',
                             'The team has not completed discussion; no genuine debate is available.' if not analyzed else 'No qualified disagreement recorded; this does not prove the conclusion.'), language),
        'watch': [s for s in sections if s['kind'] == 'watch'][:3],
        'global_coverage': pick(('当前是有限来源的黄金宏观研究，不是完整全球新闻扫描；没有归档事件不代表没有事件。',
                                'This is source-limited gold macro research, not comprehensive global news coverage; absence in the archive is not absence of events.'), language),
    }
    return {"asset": view["asset"], "asset_id": asset, "snapshot_id": view["id"], "snapshot_as_of": view["as_of"],
            "served_at": view["served_at"], "snapshot_health": view["snapshot_health"], "language": language,
            "headline": situation['battlefield'], "headline_kind": situation['battlefield_kind'], "situation": situation,
            "past_24h": {"official_releases": recent, "note": pick((
                "这里只按可核实的发布时间列出过去二十四小时官方标题；下方指标是各自日期区间的历史变化，不冒充今天的新消息。",
                "Only verified publication timestamps qualify for the last-day list; indicator windows below are not today's news."), language)},
            # Highlight primary drivers, not five overlapping votes or the observed outcome itself.
            "support": [c for c in available if c["stance"] == "support" and (asset != 'gold' or c['topic'] in ('dxy','real'))],
            "oppose": [c for c in available if c["stance"] == "oppose" and (asset != 'gold' or c['topic'] in ('dxy','real'))],
            "price_context": [c for c in cards if c['topic'] == ('gold' if asset == 'gold' else asset)],
            "prices": view.get('prices', []),
            "context": [c for c in available if c["stance"] == "context"], "all_cards": cards,
            "conflicts": view["conflicts"], "pricing": pick((
                "没有合格的OIS或期货政策路径，无法量化市场已经计入几次政策变化。仍可观察美元、实际利率及黄金各自的变化，但不能替代隐含定价。",
                "No qualified OIS/futures policy path: priced policy changes cannot be quantified. USD, real yields and gold remain observable, but are not substitutes."), language),
            "edge": "NO CLEAR EDGE", "edge_meaning": pick((
                "宏观证据尚未证明可利用优势；这不是预测黄金横盘。冻结量化模型的分期限结果另见预测账本。",
                "Macro evidence has not established exploitable Edge; this does not predict a range. Frozen quantitative horizons remain in the ledger."), language),
            "next_watch": pick((
                "先补合格的发布前预期与政策路径；随后用相同时点观察利率、美元和资产反应。若价格与机会成本假设持续不符，应调查持仓、资金流或其他机制，而不是强迫旧解释成立。",
                "Capture qualified pre-release expectations and policy paths, then observe synchronized rates, FX and asset response. Persistent disagreement warrants flows/positioning or alternative mechanisms, not forced confirmation."), language),
            "team": team, "research_run": run, "chief_brief": sections, "morning_brief": chief if analyzed else None,
            "data_gaps": [c for c in cards if c["status"] != "available"], "history": view["history"],
            "upstream": view["upstream"], "upstream_pending_reviews": view["upstream_pending_reviews"],
            "ai_status": config()["status"]}
