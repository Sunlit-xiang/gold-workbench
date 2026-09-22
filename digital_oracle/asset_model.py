"""Gold's registered deterministic feature model; no LLM runtime dependencies."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from .asset_store import digest

ASSET = {"id": "gold", "name": "Gold · GC Proxy", "instrument": "GC=F", "asset_id": "METAL.GC.CONTINUOUS.PROXY",
         "currency": "USD", "unit": "USD/oz", "cohort": "EOD_NEXT_SESSION", "horizons": {"H4": None, "D1": 1, "D3": 3, "D5": 5}}
FEATURES = ["trend", "dxy", "real", "bei", "risk", "cot"]
MODEL_SPEC = {"version": "G001.2", "train_window": 756, "min_train": 504, "ridge": 10.0,
              "normalizer_window": 756, "normalizer_min": 252, "threshold": .35, "flat_sigma": .25,
              "gap": 5, "cohort": ASSET["cohort"], "feature_ids": FEATURES,
              "status": "research_shadow", "validated_edge": False, "regime_rule": "VIX_level>=25:stress; otherwise ordinary; missing:unknown"}

# id, family, source, formula, role, economic meaning
LEAVES = [
    ("trend", "技术趋势", "gold", "0.5 Z756(log(P/P[-20])) + 0.5 Z756(log(P/P[-60]))", "candidate", "自身中短趋势；不是12个月TSMOM的原样复现"),
    ("mom5", "技术趋势", "gold", "Z756(log(P/P[-5]))", "context", "短趋势，与主趋势重复，不另加方向"),
    ("mom20", "技术趋势", "gold", "Z756(log(P/P[-20]))", "context", "主趋势组成；不能独立多计一票"),
    ("mom252", "技术趋势", "gold", "sign(log(P/P[-252]))", "context", "经典12个月TSMOM基线；日持有改造非文献原绩效"),
    ("slope", "技术趋势", "gold", "OLS slope(last5(log(P/P[-5])))", "context", "动量加速度，与趋势同簇"),
    ("ma", "技术趋势", "gold", "(SMA5-SMA20)/ATR14", "context", "均线距离，避免与动量重复计权"),
    ("atr", "波动与风险", "gold", "Wilder ATR14 / close", "risk", "范围风险，不赋方向"),
    ("rv", "波动与风险", "gold", "std(last20 log returns,ddof=1)*sqrt(252)", "risk", "未来结果的事前噪声尺度"),
    ("persistence", "技术趋势", "gold", "abs(P-P[-20])/sum(abs(delta P),20)", "context", "趋势路径效率，不重复加分"),
    ("dxy", "机会成本 · 美元与利率", "dxy", "Z756(log(DXY/DXY[-5]))", "candidate", "美元计价与全球金融条件，前瞻符号由训练估计"),
    ("real", "机会成本 · 美元与利率", "real", "Z756(100*(DFII10-DFII10[-5]))", "candidate", "10Y实际收益率机会成本；同步负相关不保证未来负向"),
    ("us2", "机会成本 · 美元与利率", "us2", "Z756(100*delta5(DGS2))", "context", "政策路径定价背景，避免利率重复"),
    ("us10", "机会成本 · 美元与利率", "us10", "Z756(100*delta5(DGS10))", "context", "名义包含real和breakeven，不三重加权"),
    ("curve", "机会成本 · 美元与利率", "us10", "Z756(100*delta5(DGS10-DGS2))", "context", "期限形变不预设多空"),
    ("bei", "通胀与流动性", "bei", "Z756(100*delta5(T10YIE))", "candidate", "通胀补偿含流动性与风险溢价；不是实际CPI"),
    ("cpi", "通胀与流动性", None, "首次core CPI surprise / past surprise MAD", "disabled", "缺公布前consensus及vintage契约"),
    ("liquidity", "通胀与流动性", None, "RZ156(delta4W(WALCL-TGA-RRP)/lag WALCL)", "disabled", "需共同可知周截面，不能使用最新修订历史冒充PIT"),
    ("risk", "跨资产与避险", "vix", "0.5*(Z756(delta5 log VIX)-Z756(delta5 log SPX))", "candidate", "压力冲击；黄金避险/去杠杆反应可能相反"),
    ("spx", "跨资产与避险", "spx", "Z756(log(SPX/SPX[-5]))", "context", "risk组成，不再独立贡献"),
    ("vix", "跨资产与避险", "vix", "Z756(log(VIX/VIX[-5]))", "risk", "风险状态及risk组成，水平不是方向"),
    ("silver", "跨资产与避险", "silver", "Z756(log(Silver/Silver[-20])-log(Gold/Gold[-20]))", "context", "工业与贵金属相对表现，含黄金自身项"),
    ("brent", "跨资产与避险", "brent", "Z756(log(Brent/Brent[-5]))", "context", "需求与供给冲击方向不等价"),
    ("cot", "持仓与资金流", "cot", "Z156weekly(delta4((ManagedLong-ManagedShort)/OI)); release lag 6 calendar days", "candidate", "拥挤/资金偏好；机构净多不等于未来必涨"),
    ("cot_level", "持仓与资金流", "cot", "(ManagedLong-ManagedShort)/OI", "context", "净仓水平，区别周变化"),
    ("etf", "持仓与资金流", None, "RZ756(delta5(GLD gold tonnes)/lag tonnes)", "disabled", "未建立官方实物持仓档案，GLD价格不是资金流"),
    ("central_banks", "持仓与资金流", None, "delta published official gold tonnes", "disabled", "发布滞后及修订，不给日频方向分"),
    ("carry", "期货与期权结构", None, "log(Far/Near)/(Tfar-Tnear)", "disabled", "GC=F不是可重建的双腿期限结构"),
    ("iv", "期货与期权结构", None, "sqrt(interpolated total variance at30D / (30/365))", "disabled", "缺合格历史surface；IV只属风险"),
    ("skew", "期货与期权结构", None, "IV25deltaPut30D-IV25deltaCall30D", "disabled", "缺期限匹配、delta与历史双边报价"),
    ("fed", "事件与信息", None, "actual policy change - prerelease expected change", "disabled", "缺合格预期路径历史，不让AI临场打鹰鸽分"),
    ("pce", "事件与信息", None, "first core PCE MoM - frozen consensus", "disabled", "缺首次发布/consensus档案"),
    ("nfp", "事件与信息", None, "first payrolls change - frozen consensus", "disabled", "修订必须另列，不能替代首次值"),
    ("geopolitics", "事件与信息", None, "2*(1-exp(-sum(confirmed severity*exp(-age/72h))))", "disabled", "缺版本化正式事件feed；无新闻不等于无风险"),
    ("prediction_markets", "事件与信息", None, "RZ(delta24h logit(mid)), liquidity + settlement gates", "disabled", "未绑定合约/期限与盘口历史"),
]


def scalar(value):
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def zscore(s, window=756, minimum=252):
    prior = s.shift(1).rolling(window, min_periods=minimum)
    return ((s-prior.mean())/prior.std(ddof=1).replace(0, np.nan)).clip(-5, 5)


def native(dataset, key):
    rows = dataset.get("series", {}).get(key, {}).get("rows", [])
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series({pd.Timestamp(r["date"]): r["close"] for r in rows}, dtype=float).sort_index()


def align(series, index, tolerance=4):
    return series.reindex(index, method="ffill", tolerance=pd.Timedelta(days=tolerance)) if len(series) else pd.Series(np.nan, index=index)


def build_features(dataset):
    gold = native(dataset, "gold")
    if len(gold) < 30:
        raise ValueError("Gold completed daily history unavailable")
    f = pd.DataFrame(index=gold.index)
    f["price"] = gold
    r = np.log(gold).diff()
    m5, m20, m60 = [np.log(gold/gold.shift(k)) for k in (5, 20, 60)]
    f["mom5"], f["mom20"] = zscore(m5), zscore(m20)
    f["trend"] = (zscore(m20)+zscore(m60))/2
    f["raw_trend20"], f["mom252"] = m20, np.sign(np.log(gold/gold.shift(252)))
    f["slope"] = m5.rolling(5).apply(lambda x: float(np.dot(x-x.mean(), np.arange(5)-2)/10), raw=True)
    f["rv"] = r.rolling(20).std(ddof=1)*np.sqrt(252)
    rows = pd.DataFrame(dataset["series"]["gold"]["rows"]).set_index("date")
    rows.index = pd.to_datetime(rows.index)
    high, low = rows["high"].astype(float), rows["low"].astype(float)
    tr = pd.concat([high-low, (high-gold.shift()).abs(), (low-gold.shift()).abs()], axis=1).max(axis=1)
    tr[high.isna() | low.isna()] = np.nan
    # Canonical Wilder seed, not an unseeded ewm approximation.
    atr = pd.Series(np.nan, index=f.index)
    if len(tr) >= 14:
        atr.iloc[13] = tr.iloc[:14].mean() if tr.iloc[:14].notna().all() else np.nan
        for i in range(14, len(tr)):
            if pd.notna(atr.iloc[i-1]):
                atr.iloc[i] = (atr.iloc[i-1]*13+tr.iloc[i])/14
            elif tr.iloc[i-13:i+1].notna().all():
                atr.iloc[i] = tr.iloc[i-13:i+1].mean()
    f["atr"] = atr/gold
    f["ma"] = (gold.rolling(5).mean()-gold.rolling(20).mean())/atr.replace(0, np.nan)
    f["persistence"] = gold.diff(20).abs()/gold.diff().abs().rolling(20).sum().replace(0, np.nan)
    for key in ("dxy", "spx", "vix", "brent"):
        s = native(dataset, key)
        f[key] = align(zscore(np.log(s/s.shift(5))), f.index)
    for key in ("real", "us2", "us10", "bei"):
        s = native(dataset, key)
        f[key] = align(zscore(100*s.diff(5)), f.index)
    f["risk"] = (f["vix"]-f["spx"])/2
    curve = native(dataset, "us10")-native(dataset, "us2")
    f["curve"] = align(zscore(100*curve.diff(5)), f.index)
    silver = align(native(dataset, "silver"), f.index)
    f["silver"] = zscore(np.log(silver/silver.shift(20))-m20)
    cot = native(dataset, "cot")
    cotz = zscore(cot.diff(4), window=156, minimum=104)
    # Report date is Tuesday, not release date. Use next Monday conservatively.
    cotz.index = cotz.index+pd.Timedelta(days=6)
    cot.index = cot.index+pd.Timedelta(days=6)
    f["cot"], f["cot_level"] = align(cotz, f.index, 14), align(cot, f.index, 14)
    f["gld"] = align(native(dataset, "gld"), f.index)
    f["gld_dislocation"] = r-np.log(f["gld"]).diff()
    f["vix_level"] = align(native(dataset, "vix"), f.index)
    f["regime"] = np.where(f["vix_level"].isna(), "unknown", np.where(f["vix_level"]>=25, "stress", "ordinary"))
    return f


def targets(frame, horizon):
    # Feature date d; signal at d+1 06UTC; first baseline date > signal date.
    dates = frame.index
    baseline = dates.searchsorted(dates+pd.Timedelta(days=1), side="right")
    endpoint = baseline+horizon
    valid = endpoint < len(frame)
    r = np.full(len(frame), np.nan)
    prices = frame["price"].to_numpy()
    r[valid] = np.log(prices[endpoint[valid]]/prices[baseline[valid]])
    sigma = frame["rv"].to_numpy()/np.sqrt(252)*np.sqrt(horizon)
    return r, sigma, baseline, endpoint


def fit_ridge(x, y):
    a = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(a.shape[1])*MODEL_SPEC["ridge"]
    penalty[0, 0] = 0
    return np.linalg.solve(a.T@a+penalty, a.T@y)


def fit_live(frame, horizon, keys=FEATURES):
    r, sigma, _, endpoints = targets(frame, horizon)
    x = frame[keys].to_numpy(dtype=float)
    y = r/np.where(sigma > 0, sigma, np.nan)
    eligible = np.flatnonzero(np.isfinite(x).all(axis=1) & np.isfinite(y) & (endpoints < len(frame)-1-MODEL_SPEC["gap"]))
    eligible = eligible[-MODEL_SPEC["train_window"]:]
    if len(eligible) < max(MODEL_SPEC["min_train"], 20*(len(keys)+1)*horizon):
        return None
    coef = fit_ridge(x[eligible], y[eligible])
    return {"coefficients": dict(zip(["intercept"]+list(keys), map(float, coef))), "n_train": len(eligible),
            "train_last_feature": str(frame.index[eligible[-1]].date()),
            "train_last_outcome": str(frame.index[endpoints[eligible[-1]]].date()), "feature_ids": list(keys)}


def transform_trace(dataset, key, cutoff):
    """Actual rolling scale operands, not an LLM explanation of a formula."""
    source_keys = {"trend": ["gold"], "risk": ["vix", "spx"]}.get(key, [key])
    traces = []
    for source in source_keys:
        s = native(dataset, source)
        if source=="cot":
            s.index = s.index+pd.Timedelta(days=6)
        s = s[s.index<=cutoff]
        for lag in ([20,60] if key=="trend" else [4] if source=="cot" else [5]):
            moves = s.diff(lag)*(100 if source in ("real","bei") else 1) if source in ("real","bei","cot") else np.log(s/s.shift(lag))
            window = 156 if source=="cot" else 756
            history = moves.iloc[-window-1:-1].dropna()
            mean, std = scalar(history.mean()), scalar(history.std(ddof=1))
            value = scalar(moves.iloc[-1]) if len(moves) else None
            traces.append({"source": source, "lag": lag, "move": value, "historical_mean": mean, "historical_std": std,
                           "history_n": len(history), "window": window, "excludes_current": True,
                           "z": max(-5,min(5,(value-mean)/std)) if value is not None and mean is not None and std else None})
    return traces


def prediction_details(frame, model, horizon, dataset):
    row = frame.iloc[-1]
    keys = model.get("feature_ids", []) if model else []
    valid = model is not None and all(scalar(row.get(k)) is not None for k in keys)
    effects = {k: model["coefficients"][k]*float(row[k]) for k in keys} if valid else {}
    intercept = model["coefficients"]["intercept"] if valid else 0
    yhat = intercept+sum(effects.values()) if valid else None
    score = 2*math.tanh(yhat/1.5) if valid else None
    common_scale = score/yhat if valid and abs(yhat)>1e-10 else 4/3
    tree = []
    for key, family, source, formula, role, meaning in LEAVES:
        value = scalar(row.get(key))
        src = dataset.get("series", {}).get(source, {})
        cutoff = frame.index[-1]
        native_rows = [r for r in src.get("rows", []) if pd.Timestamp(r["date"])+(pd.Timedelta(days=6) if source == "cot" else pd.Timedelta(0)) <= cutoff]
        observed = native_rows[-1] if native_rows else None
        available = (pd.Timestamp(observed["date"])+pd.Timedelta(days=7 if source=="cot" else 1, hours=6)).isoformat()+"Z" if observed else None
        coefficient = model["coefficients"].get(key, 0) if model else 0
        active = valid and key in keys
        traces = transform_trace(dataset,key,cutoff) if key in FEATURES else []
        related = {"trend":["gold"],"risk":["vix","spx"],"curve":["us10","us2"],"silver":["gold","silver"]}.get(key,[source] if source else [])
        tree.append({"id": "G."+key, "family": family, "label": key, "role": "predictive_research" if active else role,
                     "status": "available" if value is not None else "disabled" if role=="disabled" else "missing",
                     "value": value, "raw_value": observed.get("close") if observed else None, "unit": src.get("unit"),
                     "source": src.get("source"), "instrument": src.get("instrument"), "source_url": src.get("url"),
                     "observation_date": observed.get("date") if observed else None,
                     "available_at_assumed": available, "first_seen_at": src.get("first_seen_at"),
                     "payload_id": src.get("payload_id"), "transformation": formula,
                     "transform_components": traces,
                     "inputs": [{"series": s, "payload_id": dataset["series"].get(s,{}).get("payload_id")} for s in related],
                     "context_score": (2*math.tanh(value/1.5)*(-1 if key in ("dxy","real") else 1)) if value is not None and role!="risk" else None,
                     "score": 2*math.tanh(effects[key]/1.5) if active else (2*math.tanh(value/1.5) if value is not None and role not in ("risk",) else None),
                     "coefficient": coefficient if active else 0, "effective_weight": common_scale*coefficient if active else 0,
                     "contribution": common_scale*effects[key] if active else 0,
                     "contribution_formula": "normalized value × theta × common_squash_scale; diagnostic FactorScore is not summed",
                     "common_squash_scale": common_scale if active else 0,
                     "validation": "research_candidate; not forward validated", "meaning": meaning})
    return {"score": score, "linear_prediction_sigma": yhat, "direction": None if not valid else "Positive" if score>=.35 else "Negative" if score<=-.35 else "Neutral",
            "edge": "No Edge", "candidate_threshold_met": bool(valid and abs(score)>=.35),
            "validation": "research_shadow", "data_status": "reconstructed_history / archived_current" if valid else "insufficient_data",
            "regime": str(row["regime"]), "tree": tree, "intercept_contribution": common_scale*intercept,
            "sigma": scalar(row["rv"])/math.sqrt(252)*math.sqrt(horizon) if scalar(row["rv"]) is not None else None,
            "price": scalar(row["price"]), "feature_date": str(frame.index[-1].date())}
