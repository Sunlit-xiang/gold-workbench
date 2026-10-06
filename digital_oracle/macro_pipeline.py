"""Shared Macro Core -> asset-specific evidence -> immutable daily research views."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urlencode

from .asset_store import digest, utcnow
from .macro_core import ASSETS, COUNTRIES, VERSION, Evidence, change, instant, memory_relevance, surprise, unique_clusters
from .macro_sources import REGISTRY, collect_public
from .upstream import latest_tracking, pending_reviews

GOLD_LEAVES = {
    "gold": ("Price / Trend", "tactical", 1, "GC proxy price action; not a spot fixing"),
    "dxy": ("Opportunity cost", "tactical", -1, "USD appreciation raises foreign-currency gold cost; sign is a theory prior"),
    "real": ("Opportunity cost", "tactical", -1, "10Y TIPS real yield opportunity cost; not inflation-free pure expectations"),
    "us2": ("Opportunity cost", "tactical", -1, "2Y nominal yield includes expected policy and risk premia; not Fed probability"),
    "us10": ("Opportunity cost", "tactical", -1, "10Y nominal yield; overlaps real plus inflation compensation"),
    "bei": ("Inflation / policy", "tactical", 0, "10Y breakeven includes liquidity/risk premia; inflation protection and tightening can conflict"),
    "spx": ("Cross-market risk", "risk", 0, "Equity risk context; no stable fixed Gold directional sign"),
    "vix": ("Cross-market risk", "risk", 0, "Equity implied volatility, not gold options volatility"),
    "brent": ("Cross-market risk", "event", 0, "Energy inflation and growth channels can oppose; oil price alone does not verify geopolitics"),
    "cot": ("Positioning / flows", "structural", 0, "Managed money net/OI; crowdedness and trend-following have opposing interpretations"),
    "gld": ("Positioning / flows", "tactical", 0, "ETF PRICE, explicitly not ETF inflows or tonnes"),
    "silver": ("Cross-market risk", "tactical", 0, "Silver price; industry and gold exposures overlap"),
}
MISSING_GOLD = [
    ("Central bank gold demand", "structural", "Quarterly official/WGC releases, revision and reporting lags; not yet normalized"),
    ("ETF holdings / flows", "tactical", "Need holdings/tonnage and publication times, not GLD price"),
    ("Gold options IV / skew", "risk", "Need timestamped licensed CME or comparable options surface"),
    ("Liquidity / financial conditions", "structural", "Need vintage-aware financial conditions and balances; no score from stale M2"),
    ("Geopolitical verified events", "event", "Need independently sourced event ledger, no inference from oil alone"),
    ("Fed futures / OIS path", "tactical", "INSUFFICIENT PRICING DATA: no qualified implied policy curve"),
]


def health_date(day, now, max_age=5):
    if not day:
        return "MISSING"
    age = (instant(now).date() - datetime.fromisoformat(day).date()).days
    return "UNKNOWN" if age < 0 else "STALE" if age > max_age else "available"


def leaf(asset, key, source, now, family, layer, sign=0, meaning="", lag=5, kind="return", max_age=5):
    rows = [r for r in source.get("rows", []) if r["date"] < now[:10]]
    moved = change(rows, lag, kind)
    latest = rows[-1] if rows else {}
    status = source.get("status", "available")
    if status == "available":
        status = health_date(latest.get("date"), now, max_age)
    fetched = source.get("fetched_at") or source.get("ingestion_time") or now
    stance = "unknown"
    if status == "available" and moved and sign and moved["value"]:
        stance = "support" if sign * moved["value"] > 0 else "oppose"
    elif status == "available":
        stance = "context"
    source_url=source.get("url", "")
    if source.get("params"):
        source_url += ('&' if '?' in source_url else '?') + urlencode(source['params'])
    evidence = Evidence(asset=asset, country=ASSETS[asset]["countries"], topic=key, family=family, layer=layer,
                        source=source.get("source", "Unknown"), source_quality=source.get("tier", 1 if source.get("source") in ('fred','cftc') else 2),
                        url=source_url, ingestion_time=fetched, available_at=fetched,
                        observation_date=latest.get("date"), actual=latest.get("close"),
                        previous=rows[-1-lag]["close"] if len(rows)>lag else None,
                        units="net/OI" if kind=="pp" else source.get("unit", "% p.a." if kind=="bp" else "native"), status=status,
                        raw_payload_id=source.get("payload_id"), transformation=moved or {"status":"MISSING"},
                        interpretation=meaning, stance=stance,
                        independence_cluster="usd_rates" if key in ("real", "us10", "bei", "us2") else key)
    return evidence.record()


def numeric(raw):
    if raw is None:
        return None, ""
    # Units must match exactly; never silently strip K/M, ranges or currency labels.
    match = re.fullmatch(r"\s*([+-]?[0-9]+(?:\.[0-9]+)?)\s*(%|bp)?\s*", str(raw))
    return (float(match[1]), match[2] or "number") if match else (None, "")


def calendar_events(store, now):
    from .providers.economic_calendar import TradingEconomicsCalendarProvider, EconomicCalendarQuery
    provider = TradingEconomicsCalendarProvider()
    if not provider.configured:
        return [], {"status":"MISSING", "reason":"TRADING_ECONOMICS_API_KEY not configured; no consensus is invented"}
    day = instant(now).date()
    try:
        rows = provider.list_events(EconomicCalendarQuery(start_date=(day-timedelta(days=7)).isoformat(),
                         end_date=(day+timedelta(days=7)).isoformat(), countries=("united states","australia","new zealand","euro area","japan")))
    except Exception as exc:
        return [], {"status":"UNKNOWN", "error":type(exc).__name__}
    prior = store.list("macro_events",100000)
    result=[]
    for event in rows:
        raw=event.to_dict()
        actual, unit=numeric(event.actual)
        consensus, consensus_unit=numeric(event.forecast)
        frozen=[e for e in prior if e.get("calendar_id")==event.event_id and e.get("event_time")==event.time_utc
                and e.get("forecast") is not None and e.get("time_precision")=="exact" and instant(e["available_at"])<instant(event.time_utc)]
        frozen.sort(key=lambda e:e["available_at"])
        # Earliest captured consensus is the defined benchmark; later revisions stay in ledger.
        pre=frozen[0] if frozen else None
        calc=surprise(actual,pre["forecast"] if pre else None,units=unit,
                      consensus_units=pre["units"] if pre else "",consensus_available_at=pre["available_at"] if pre else None,
                      event_time=event.time_utc) if event.time_precision=="exact" else {"status":"UNKNOWN","reason":"event time not exact"}
        body={"calendar_id":event.event_id,"event_time":event.time_utc,"time_precision":event.time_precision,
              "publication_time":None,"ingestion_time":now,"available_at":now,"country":event.country,
              "title":event.name,"source":"Trading Economics radar", "source_quality":4,"source_url":event.source_url,
              "original_source":event.source,"actual":actual,"forecast":consensus,"units":consensus_unit or unit,
              "previous":event.previous,"revision":None,"raw_extraction":raw,"surprise":calc,
              "consensus_evidence_id":pre.get("id") if pre else None,
              "reaction":{w:{"status":"MISSING","reason":"no qualified event quotes"} for w in ("5m","30m","2h","1d")}}
        body["id"]=store.put("macro_events",body); result.append(body)
    return result,{"status":"available","events":len(result),"scope":"aggregator radar; original facts need source verification"}


def matched_spread(asset, a, b, now, topic, meaning):
    left={r["date"]:r["close"] for r in a.get("rows",[])}
    right={r["date"]:r["close"] for r in b.get("rows",[])}
    shared=sorted(left.keys() & right.keys())
    source={"source":a.get("source","")+" minus "+b.get("source",""),"tier":1,
            "url":a.get("url",""),"unit":"percentage points", "ingestion_time":max(a.get("ingestion_time",now),b.get("ingestion_time",now),key=instant),
            "status":"available" if a.get("status")==b.get("status")=="available" else "MISSING",
            "rows":[{"date":d,"close":left[d]-right[d]} for d in shared]}
    result=leaf(asset,topic,source,now,"Relative policy / carry","structural",0,meaning,1,"bp",75 if "money" in topic else 5)
    result["source_refs"]=[{"url":s.get("url"),"payload_id":s.get("payload_id"),"date":s.get("rows",[{}])[-1].get("date") if s.get("rows") else None} for s in (a,b)]
    result["id"]=digest({k:v for k,v in result.items() if k!="id"})
    return result


def build_asset(asset, dataset, public, now, events=()):
    if asset not in ASSETS: raise ValueError("unknown asset")
    evidence=[]
    if asset=="gold":
        for key,(family,layer,sign,meaning) in GOLD_LEAVES.items():
            source=dataset.get("series",{}).get(key)
            if source:
                evidence.append(leaf(asset,key,source,now,family,layer,sign,meaning,4 if key=="cot" else 5,
                                     "pp" if key=="cot" else "bp" if key in ("real","us2","us10","bei") else "return",12 if key=="cot" else 5))
            else:
                evidence.append(Evidence(asset=asset,country=["US"],topic=key,family=family,layer=layer,
                                source="Existing Gold provider",source_quality=2,url="",ingestion_time=now,available_at=now,
                                interpretation="Source absent in the latest dataset; not a neutral observation. "+meaning,
                                independence_cluster=key).record())
        missing=MISSING_GOLD
    else:
        fx=public.get("ecb_fx",{})
        price={**fx,"rows":fx.get("series",{}).get(asset,[]),"unit":ASSETS[asset]["instrument"]}
        evidence.append(leaf(asset,asset,price,now,"Relative price / trend","tactical",1,"Reference cross trend; not executable spot and not a forward prediction"))
        if asset=="audnzd":
            for key in ("au_cash","nz_cash","au_money","nz_money"):
                spec=public.get(key,{})
                evidence.append(leaf(asset,key,spec,now,"Country macro profile","structural",0,
                                REGISTRY[key]["role"],1,"bp",75 if "money" in key else 5))
            evidence.append(matched_spread(asset,public.get("au_cash",{}),public.get("nz_cash",{}),now,"policy_spread",
                         "AU cash target minus NZ OCR on matched dates; current policy level is not unexpected policy path or executable carry"))
            evidence.append(matched_spread(asset,public.get("au_money",{}),public.get("nz_money",{}),now,"money_spread",
                         "Same-month AU minus NZ overnight money rate; OECD monthly proxy, not policy/OIS. Dates must match."))
        missing=[("Relative OIS / forward carry","tactical","INSUFFICIENT PRICING DATA: matched maturity, timestamp and venue required"),
                 ("Inflation / growth / labour differentials","structural","Comparable release definitions and vintages are not yet normalized"),
                 ("Terms of trade / commodity exposures","structural","AU iron ore vs NZ dairy; broad commodity index cannot replace relative export basket"),
                 ("Housing / credit / China exposure","structural","Country profiles registered; numerical comparability not yet validated"),
                 ("FX positioning / options","risk","Need pair-specific positioning/IV; no proxy substitution by name"),
                 ("Event price rejection","event","Timestamped consensus and FX quotes required")]
    for topic,layer,meaning in missing:
        evidence.append(Evidence(asset=asset,country=ASSETS[asset]["countries"],topic=topic,family="Data / research gaps",layer=layer,
                        source="Registry / pending qualified provider",source_quality=1,url="",ingestion_time=now,available_at=now,
                        interpretation=meaning,independence_cluster=topic).record())
    for key,country in (("fed_news","US"),("rba_news","AU"),("ecb_news","EA")):
        if country not in ASSETS[asset]["countries"]: continue
        feed=public.get(key,{})
        for news in feed.get("items",[])[:6]:
            fetched=feed.get("ingestion_time",now)
            evidence.append(Evidence(asset=asset,country=[country],topic=news["title"],family="Official events",layer="event",
                            source=feed.get("source",""),source_quality=1,url=news["url"],ingestion_time=fetched,available_at=fetched,
                            publication_time=news["publication_time"],status=health_date(news["publication_time"][:10],now,7) if feed.get("status")=="available" else "STALE",
                            raw_payload_id=feed.get("payload_id"),interpretation="Official title verified only. No extracted surprise or policy-path claim.",
                            independence_cluster=key).record())
    # Contradictions are descriptions of aligned observed windows, not causal verdicts.
    conflicts=[]
    indexed={e["topic"]:e for e in evidence}
    if asset=="gold":
        price=indexed.get("gold"); rate=indexed.get("real"); usd=indexed.get("dxy")
        trio=[price,rate,usd]
        if all(e and e["status"]=="available" and e["transformation"].get("value") is not None for e in trio):
            windows={(e["transformation"]["from_date"],e["transformation"]["to_date"]) for e in trio}
            if len(windows)==1 and all(e["transformation"]["value"]>0 for e in trio):
                conflicts.append({"kind":"SAME_WINDOW_DIVERGENCE","evidence_ids":[e["id"] for e in trio],
                                  "text":"Gold, USD and real yield rose in the same window. Opportunity-cost prior does not fully explain observed Gold strength; not event rejection and not forward Edge."})
            elif len(windows)>1:
                conflicts.append({"kind":"TIME_ALIGNMENT","evidence_ids":[e["id"] for e in trio],"text":"Native data windows differ; no combined price-rejection conclusion."})
    support=[e["id"] for e in evidence if e["stance"]=="support"]
    oppose=[e["id"] for e in evidence if e["stance"]=="oppose"]
    if support and oppose:
        conflicts.append({"kind":"MIXED_PRIORS","evidence_ids":support+oppose,"text":"Directional context priors conflict. No majority vote, no aggregate score."})
    countries=ASSETS[asset]["countries"]
    country_names={"US":"united states","AU":"australia","NZ":"new zealand","EA":"euro area","JP":"japan"}
    relevant_events=[e for e in events if e.get("country","").lower() in [country_names[c] for c in countries]]
    return {"schema_version":1,"model_version":VERSION,"asset_id":asset,"asset":ASSETS[asset],"as_of":now,"available_at":now,
            "regime":{"structural":"UNKNOWN: no inferred long-run regime from a week of prices", "tactical":"MIXED" if support and oppose else "DESCRIPTIVE CONTEXT ONLY", "event":"consensus/reaction gaps remain"},
            "decision":{"edge":"NO CLEAR EDGE","trade":"NO TRADE RECOMMENDATION","reason":"Macro context is not a validated conditional return model. Missing pricing cannot be guessed."},
            "pricing":{"status":"INSUFFICIENT PRICING DATA","missing":["OIS/futures expected path","pre-release consensus unless frozen","timestamped executable prices"],
                       "note":"Treasury yields/current cash rates describe prices or levels, not probability of the next decision."},
            "evidence":evidence,"bull_evidence":support,"bear_evidence":oppose,"conflicts":conflicts,
            "events":relevant_events,"country_profiles":{c:COUNTRIES[c] for c in countries},
            "reaction":{w:{"status":"MISSING","reason":"Daily series do not qualify as event-window observations"} for w in ("5m","30m","2h","1d")},
            "independent_context_clusters":unique_clusters(evidence),
            "prices":dataset.get("series",{}).get("gold",{}).get("rows",[])[-90:] if asset=="gold" else public.get("ecb_fx",{}).get("series",{}).get(asset,[]),
            "lineage":{"legacy_dataset_id":dataset.get("id"),"framework":"deterministic descriptions; no model refit"}}


def collect_macro(store, legacy_store, now=None, fetch=None):
    stamp=now or utcnow()
    public=collect_public(store,stamp,**({"fetch":fetch} if fetch else {}))
    events,event_health=calendar_events(store,stamp)
    dataset=legacy_store.latest("datasets") or {}
    if not dataset.get("series",{}).get("gold"):
        previous=next((d for d in legacy_store.list("datasets",100) if d.get("series",{}).get("gold")),None)
        if previous:
            failed=dataset
            dataset={**previous,"series":{k:{**s,"status":"STALE"} for k,s in previous["series"].items()},
                     "fallback_reason":"Latest Gold collection incomplete; retained last successful dataset",
                     "latest_errors":failed.get("errors",{})}
    snapshots={}
    for asset in ASSETS:
        view=build_asset(asset,dataset,public,stamp,events)
        for evidence in view["evidence"]:
            store.put("macro_evidence",{k:v for k,v in evidence.items() if k!="id"},evidence["id"])
        relevant={'gold':('fed_news',),'audnzd':('ecb_fx','au_cash','nz_cash','au_money','nz_money','rba_news'),
                  'eurusd':('ecb_fx','fed_news','ecb_news'),'usdjpy':('ecb_fx','fed_news')}[asset]
        view["source_health"]={k:{f:v for f,v in s.items() if f not in ("rows","series","items","raw_text","parsed")} for k,s in public.items() if k in relevant}
        if asset=='gold':
            for key,s in dataset.get('series',{}).items():
                view['source_health'][key]={'source':s['source'],'url':s['url'],'fetched_at':s['fetched_at'],
                        'status':s.get('status','available'),'last_observation':s['rows'][-1]['date'] if s.get('rows') else None}
            view['legacy_source_errors']=dataset.get('latest_errors',dataset.get('errors',{}))
        view["calendar_health"]=event_health
        view["id"]=store.put("macro_snapshots",view)
        snapshots[asset]=view
    return snapshots


def macro_dashboard(store, asset="gold", now=None):
    if asset not in ASSETS: raise ValueError("unknown asset")
    stamp=now or utcnow()
    history=[s for s in store.as_of("macro_snapshots",stamp,100000) if s.get("asset_id")==asset]
    if not history:
        return {"status":"MISSING","asset_id":asset,"asset":ASSETS[asset],"reason":"Run macro collection; a preview does not fabricate evidence."}
    current=history[0]
    current["served_at"]=stamp
    current["snapshot_health"]=health_date(current["as_of"][:10],stamp,2)
    for e in current["evidence"]:
        if e["status"]=="available" and e.get("observation_date"):
            threshold=75 if "money" in e["topic"] else 12 if e["topic"]=="cot" else 5
            e["display_health"]=health_date(e["observation_date"],stamp,threshold)
        elif e["status"]=="available" and e.get("publication_time"):
            e["display_health"]=health_date(e["publication_time"][:10],stamp,7)
        else: e["display_health"]=e["status"]
    current["history"]=[{"id":s["id"],"as_of":s["as_of"],"edge":s["decision"]["edge"],"version":s["model_version"],
                         "available":sum(e["status"]=="available" for e in s["evidence"]),"conflicts":len(s["conflicts"])} for s in history[:90]]
    previous=history[1] if len(history)>1 else None
    old={e["topic"]:e for e in previous["evidence"]} if previous else {}
    current["changes_since_previous"]=[{"topic":e["topic"],"evidence_id":e["id"],"previous":old[e["topic"]].get("actual"),"current":e.get("actual")}
                for e in current["evidence"] if e["topic"] in old and e.get("actual")!=old[e["topic"]].get("actual")]
    memories=store.as_of("macro_evidence",stamp,10000)
    current["memory"]=[{k:e.get(k) for k in ("id","topic","layer","publication_time","available_at","interpretation")} | {
                   "relevance":memory_relevance(e.get("publication_time") or e["available_at"],stamp,e["layer"])}
                   for e in memories if e["asset"]==asset and e["family"]=="Official events"][:30]
    current["upstream"]=latest_tracking(store)
    current["upstream_pending_reviews"]=pending_reviews(store)
    current["ai_config"]={"security":"server-side environment/Actions Secrets only", "provider_choices":["off","deepseek","kimi","kimi-cn","openai","openai-compatible"]}
    ai=[a for a in store.list("macro_ai",10000) if a.get("snapshot_id")==current["id"]]
    latest_ai=ai[0] if ai else None
    current["ai_summaries"]={}
    for a in ai:current["ai_summaries"].setdefault(a["language"],a)
    current["ai_summary"]=latest_ai or {"status":"not_generated","note":"Deterministic evidence remains usable without AI"}
    return current
