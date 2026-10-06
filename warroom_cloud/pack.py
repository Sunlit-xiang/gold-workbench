"""PIT-first research inputs, assembled by code before any model call."""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from digital_oracle.asset_store import digest, utcnow
from digital_oracle.macro_pipeline import build_asset
from digital_oracle.macro_sources import collect_public
from digital_oracle.macro_store import MacroStore
from digital_oracle.macro_core import instant
from digital_oracle.providers.research_history import ResearchHistoryProvider, SOURCES
from digital_oracle.http import UrllibJsonClient

DATA_ORIGIN='https://sunlit-xiang.github.io/gold-workbench/data/'


def read_public(path):
    with urlopen(Request(DATA_ORIGIN+path,headers={'User-Agent':'DigitalOracleWarRoom/3'}),timeout=15) as response:
        raw=response.read(8_000_001)
    if len(raw)>8_000_000: raise ValueError('public archive exceeds budget')
    return json.loads(raw)


def load_seed(asset):
    try: return read_public(f'oracle-seed-{asset}.json')
    except Exception:
        # The old public export is an honest fallback, never newly stamped as live data.
        snapshot=read_public(f'macro-{asset}.json')
        return {'asset_id':asset,'snapshot':snapshot,'dataset':{'series':{}},'pit_history':[],
                'seed_gap':'PIT archive seed not yet published; no reconstructed PIT history invented'}


def assemble(store, job, *, seed=None, provider=None, public_fetch=None):
    seed=seed or load_seed(job['asset'])
    if seed.get('asset_id')!=job['asset']: raise ValueError('asset seed mismatch')
    started=utcnow()
    # Archived rows retain their original available_at. A later download is not a vintage.
    history=[r for r in seed.get('pit_history',[]) if r.get('asset')==job['asset'] and r.get('available_at') and instant(r['available_at'])<=instant(started)]
    for r in history:
        store.put('macro_evidence',{k:v for k,v in r.items() if k!='id'},r['id'])
    series=dict(seed.get('dataset',{}).get('series',{})); errors={}; refreshed=[]
    if job['asset']=='gold':
        provider=provider or ResearchHistoryProvider(UrllibJsonClient(timeout_seconds=8,retry_attempts=1))
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures={pool.submit(provider.fetch,key):key for key in SOURCES}
            for f in as_completed(futures):
                key=futures[f]
                try:
                    s=f.result(); raw=s.pop('raw'); s['raw_content_hash']=digest(raw); s['rows']=s['rows'][-400:]
                    series[key]=s; refreshed.append(key)
                except Exception as exc:
                    errors[key]=type(exc).__name__
                    if key in series: series[key]={**series[key],'status':'STALE','refresh_error':type(exc).__name__}
    public=collect_public(store,utcnow(),**({'fetch':public_fetch} if public_fetch else {}))
    frozen_at=utcnow()
    view=build_asset(job['asset'],{'id':digest(series),'series':series},public,frozen_at,[])
    view['source_health']={k:{f:v for f,v in s.items() if f not in ('rows','series','items','raw_text','parsed')} for k,s in public.items()}
    view['calendar_health']={'status':'MISSING','note':'No pre-release consensus or event-window market quotes in this pack'}
    for e in view['evidence']: store.put('macro_evidence',{k:v for k,v in e.items() if k!='id'},e['id'])
    view['id']=store.put('macro_snapshots',view)
    metadata={'schema':'ResearchPack.PIT.v1','asset':job['asset'],'run_id':job['id'],'assembled_at':frozen_at,
              'snapshot_id':view['id'],'seed_snapshot_id':seed.get('snapshot',{}).get('id'),
              'seed_as_of':seed.get('snapshot',{}).get('as_of'),'refreshed_series':refreshed,'refresh_failures':errors,
              'freshness':[{'id':e['id'],'topic':e['topic'],'status':e['status'],'observation_date':e.get('observation_date'),
                           'available_at':e['available_at'],'source':e['source'],'url':e['url']} for e in view['evidence']],
              'gaps':[{'id':e['id'],'topic':e['topic'],'status':e['status'],'meaning':e['interpretation']}
                      for e in view['evidence'] if e['status']!='available'],
              'pit_history_count':len(history),'archive_gap':seed.get('seed_gap'),
              'pit_contract':'Original first-seen archive only. Refreshed FRED/Yahoo history is latest-vintage, not certified historical PIT. No same-day executable quotes.',
              'tool_policy':'Read assembled evidence first. Target official domains only for a named unresolved gap. No free web search.'}
    # Each leaf includes its actual values, transformation, dates and provenance.
    pack={**metadata,'view':view,'pit_history_ids':[e['id'] for e in history],
          'macro_materials':view.get('memory',[]),'available_at':frozen_at}
    pack['id']=store.put('research_packs',pack)
    return pack
