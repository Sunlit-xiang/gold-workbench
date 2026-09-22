"""Forward-label research statistics, not an order/execution backtest engine."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from .asset_model import FEATURES, MODEL_SPEC, fit_ridge, targets, scalar

VARIANTS = {"trend_ridge": ["trend"], "opportunity_cost": ["trend", "dxy", "real"],
            "plus_inflation": ["trend", "dxy", "real", "bei"],
            "plus_risk": ["trend", "dxy", "real", "bei", "risk"], "full": FEATURES}
VARIANTS.update({"without_"+key: [k for k in FEATURES if k != key] for key in FEATURES})


def walk_forward(frame, h, keys):
    returns, sigma, _, endpoints = targets(frame, h)
    x = frame[keys].to_numpy(dtype=float)
    y = returns/np.where(sigma>0, sigma, np.nan)
    valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
    out = np.full(len(frame), np.nan)
    coefs, fit_dates, last_month = None, [], None
    for i, day in enumerate(frame.index):
        month = str(day.to_period("M"))
        if month != last_month:
            train = np.flatnonzero(valid & (endpoints < i-MODEL_SPEC["gap"]))[-MODEL_SPEC["train_window"]:]
            minimum = max(MODEL_SPEC["min_train"], 20*(len(keys)+1)*h)
            coefs = fit_ridge(x[train], y[train]) if len(train)>=minimum else None
            if coefs is not None:
                fit_dates.append({"date": str(day.date()), "last_label": str(frame.index[endpoints[train[-1]]].date()),
                                  "n": len(train), "coef": dict(zip(["intercept"]+keys, map(float, coefs)))})
            last_month = month
        if coefs is not None and np.isfinite(x[i]).all():
            out[i] = 2*np.tanh((coefs[0]+x[i]@coefs[1:])/1.5)
    return out, fit_dates


def bootstrap_interval(values, block=20, repetitions=400):
    values = np.asarray(values, dtype=float)
    if np.isfinite(values).sum()<30:
        return None
    rng = np.random.default_rng(20260918)
    estimates = []
    n = len(values)
    for _ in range(repetitions):
        starts = rng.integers(0, n, int(np.ceil(n/block)))
        indexes = ((starts[:, None]+np.arange(block)) % n).ravel()[:n]
        sample = values[indexes]
        if np.isfinite(sample).any():
            estimates.append(float(np.nanmean(sample)))
    return [float(v) for v in np.quantile(estimates, [.025, .975])]


def metrics(scores, actual, sigma, baseline, h, baseline_indices=None, endpoint_indices=None):
    scores, actual, sigma, baseline = map(np.asarray, (scores, actual, sigma, baseline))
    valid = np.isfinite(scores) & np.isfinite(actual) & np.isfinite(sigma) & (sigma>0)
    threshold = np.maximum(.001, .25*sigma)
    target = np.where(actual>threshold, 1, np.where(actual < -threshold, -1, 0))
    direction = np.where(scores>=.35, 1, np.where(scores<=-.35, -1, 0))
    selected = valid & (direction!=0)
    hit = (direction==target)
    baseline_hit = (np.sign(baseline)==target)
    paired = selected & np.isfinite(baseline)
    diff = np.where(paired, hit.astype(float)-baseline_hit.astype(float), np.nan)
    hit_series = np.where(selected, hit.astype(float), np.nan)
    nonoverlap = []
    starts = np.arange(len(scores)) if baseline_indices is None else np.asarray(baseline_indices)
    ends = starts+h if endpoint_indices is None else np.asarray(endpoint_indices)
    for offset in range(h):
        mask = np.zeros(len(scores), dtype=bool)
        last_end = -1
        for i in range(offset,len(scores)):
            if selected[i] and starts[i]>=last_end:
                mask[i] = True
                last_end = ends[i]
        nonoverlap.append({"offset": offset, "n": int(mask.sum()), "hit_rate": scalar(np.mean(hit[mask])) if mask.any() else None})
    rank_ic = scalar(pd.Series(scores[valid]).rank().corr(pd.Series(actual[valid]).rank())) if valid.sum()>2 and np.std(scores[valid])>0 else None
    return {"n": int(valid.sum()), "opportunities": len(scores), "data_coverage": float(valid.mean()) if len(valid) else 0,
            "directional_n": int(selected.sum()), "coverage": float(selected.sum()/valid.sum()) if valid.any() else 0,
            "hit_rate": scalar(np.mean(hit[selected])) if selected.any() else None,
            "hit_ci95_block20": bootstrap_interval(hit_series), "three_class_accuracy": scalar(np.mean(hit[valid])) if valid.any() else None,
            "flat_rate": scalar(np.mean(target[valid]==0)) if valid.any() else None,
            "baseline_same_dates_hit": scalar(np.mean(baseline_hit[paired])) if paired.any() else None,
            "increment_vs_mom20": scalar(np.nanmean(diff)) if paired.any() else None,
            "increment_ci95_block20": bootstrap_interval(diff), "rank_ic": rank_ic,
            "nonoverlap": nonoverlap, "nonoverlap_min_n": min((v["n"] for v in nonoverlap), default=0)}


def research(frame, include_holdout=False):
    if not include_holdout:
        raise ValueError("G001 requires explicit --open-holdout after preregistration and implementation tests; no silent sealed access")
    if len(frame)<1200:
        raise ValueError("Need >=1200 daily observations for registered train/OOS/holdout protocol")
    holdout_start = frame.index[-252]
    # Before explicit opening, truncate BEFORE feature construction in caller too.
    result = {"protocol": "G001.2", "holdout_start": str(holdout_start.date()),
              "holdout_opened": include_holdout, "data_status": "exploratory_latest_vintage_gc_proxy",
              "verdict": "No validated Edge; PIT/roll and forward-validation gates unresolved", "horizons": {}}
    for horizon, h in (("D1", 1), ("D3", 3), ("D5", 5)):
        returns, sigma, baseline_idx, endpoint_idx = targets(frame, h)
        base = np.sign(frame["raw_trend20"].to_numpy())
        scores = {"neutral": np.zeros(len(frame)), "always_up": np.full(len(frame), 2.),
                  "momentum20": 2*base, "tsmom252": 2*frame["mom252"].to_numpy()}
        coef_history = {}
        for name, keys in VARIANTS.items():
            scores[name], coef_history[name] = walk_forward(frame, h, keys)
        common = np.isfinite(scores["full"]) & np.isfinite(returns)
        if not include_holdout:
            common &= frame.index < holdout_start
            # No development outcome may extend into the sealed block.
            common &= endpoint_idx < len(frame)-252
        summaries = {}
        for name, values in scores.items():
            summaries[name] = {}
            for split, splitmask in (("development", frame.index<holdout_start), ("holdout", frame.index>=holdout_start)):
                if split=="holdout" and not include_holdout:
                    continue
                mask = common & splitmask
                if split=="development":
                    mask &= endpoint_idx < len(frame)-252
                summaries[name][split] = metrics(values[mask], returns[mask], sigma[mask], base[mask], h, baseline_idx[mask], endpoint_idx[mask])
        full = scores["full"]
        groups = {}
        for year in sorted(set(frame.index.year[common])):
            mask = common & (frame.index.year==year)
            groups[str(year)] = metrics(full[mask], returns[mask], sigma[mask], base[mask], h, baseline_idx[mask], endpoint_idx[mask])
        regimes = {}
        for regime in ("stress", "ordinary", "unknown"):
            mask = common & (frame["regime"].to_numpy()==regime)
            if mask.any():
                regimes[regime] = metrics(full[mask], returns[mask], sigma[mask], base[mask], h, baseline_idx[mask], endpoint_idx[mask])
        rows = []
        for i in np.flatnonzero(common):
            rows.append({"feature_date": str(frame.index[i].date()), "signal_date": str((frame.index[i]+pd.Timedelta(days=1)).date()),
                         "baseline_date": str(frame.index[baseline_idx[i]].date()), "endpoint_date": str(frame.index[endpoint_idx[i]].date()),
                         "return": float(returns[i]), "sigma": float(sigma[i]), "regime": str(frame.iloc[i]["regime"]),
                         "scores": {k: scalar(v[i]) for k,v in scores.items()},
                         "split": "holdout" if frame.index[i]>=holdout_start else "development"})
        gc_gld = frame["gld_dislocation"].dropna()
        ablations = {}
        for name in ["trend_ridge", "opportunity_cost"]+["without_"+k for k in FEATURES]:
            mask = common & (frame.index>=holdout_start) & (np.abs(full)>=.35) & (np.abs(scores[name])>=.35)
            label = np.where(returns>np.maximum(.001,.25*sigma),1,np.where(returns < -np.maximum(.001,.25*sigma),-1,0))
            difference = (np.sign(full)==label).astype(float)-(np.sign(scores[name])==label).astype(float)
            ablations[name] = {"both_directional_n": int(mask.sum()), "full_minus_comparator_hit": scalar(np.mean(difference[mask])) if mask.any() else None,
                               "ci95_block20": bootstrap_interval(np.where(mask,difference,np.nan))}
        result["horizons"][horizon] = {"models": summaries, "by_year": groups, "by_regime": regimes,
                                          "matched_directional_ablations_holdout": ablations,
                                          "eligible_common_dates": int(common.sum()), "all_feature_dates": len(frame),
                                          "comparison_scope": "same complete-case dates for every model; not whole-schedule coverage",
                                          "coefficient_history": coef_history, "forecasts": rows,
                                          "proxy_diagnostic": {"daily_gc_gld_diff_std": scalar(gc_gld.std()), "days_abs_diff_gt_2pct": int((gc_gld.abs()>.02).sum())}}
    result["horizons"]["H4"] = {"status": "insufficient_data", "reason": "No audited PIT hourly Gold/driver history or synchronous outcome feed"}
    return result
