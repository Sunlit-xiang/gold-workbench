"""Vercel/FastAPI interface. Browser research requests never carry model secrets."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from starlette.concurrency import run_in_threadpool
from vercel import workflow
from digital_oracle.macro_ai import config, PROVIDERS
from digital_oracle.research_team import ROLES, run_analyst, session_key
from digital_oracle.war_room import board
from warroom_cloud.store import CloudStore
from warroom_cloud.pack import read_public
from warroom_cloud.workflows import team_research, bounded_call

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
# Vercel precompiles modules: __file__ can live under __pycache__, whereas
# the documented runtime working directory remains the project root.
PUBLIC=(Path.cwd() if os.getenv('VERCEL') else Path(__file__).resolve().parent)/'web/public'
ASSETS={'gold','audnzd'}
COOKIE='oracle_owner'


def password(): return os.getenv('WAR_ROOM_PASSWORD','')


def signed_cookie(expiry):
    value=str(expiry)
    return value+'.'+hmac.new(password().encode(),value.encode(),hashlib.sha256).hexdigest()


def authenticated(request):
    value=request.cookies.get(COOKIE,'')
    if len(password())<20: return False
    try:
        expiry=int(value.split('.')[0])
        return time.time()<expiry and hmac.compare_digest(value,signed_cookie(expiry))
    except (ValueError,IndexError): return False


def same_origin(request):
    origin=request.headers.get('origin')
    if not origin or urlparse(origin).netloc!=request.url.netloc:
        raise HTTPException(403,'Same-origin request required')
    if request.headers.get('sec-fetch-site') not in (None,'same-origin','none'):
        raise HTTPException(403,'Cross-site request rejected')


def owner(request):
    same_origin(request)
    if not authenticated(request): raise HTTPException(401,'请在 AI 配置窗口登录 / Owner sign-in required')


def storage():
    if not os.getenv('DATABASE_URL'): raise HTTPException(503,'DATABASE_URL 尚未配置 / Storage not configured')
    store=CloudStore()
    try: store.initialize(); return store
    except Exception: store.close(); raise HTTPException(503,'Research storage unavailable') from None


def contract(asset,language):
    if asset not in ASSETS or language not in ('zh','en'): raise HTTPException(400,'Invalid asset or language')


async def body(request):
    raw=await request.body()
    if len(raw)>12000: raise HTTPException(413,'Request too large')
    try: value=json.loads(raw)
    except ValueError: raise HTTPException(400,'Invalid JSON') from None
    if not isinstance(value,dict): raise HTTPException(400,'Object required')
    return value


@app.middleware('http')
async def security(request, call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
    return response


@app.exception_handler(Exception)
async def sanitized_error(request, exc):
    return JSONResponse({'error':'Server operation unavailable','type':type(exc).__name__},status_code=503)


@app.exception_handler(HTTPException)
async def request_error(request,exc):
    return JSONResponse({'error':exc.detail},status_code=exc.status_code)


@app.get('/api/war-room/capabilities')
def capabilities(request: Request):
    providers={p:config(p)['status']=='configured' for p in (*PROVIDERS,'openai-compatible')}
    missing=[]
    if not any(providers.values()): missing.append('AI provider secret')
    if not os.getenv('DATABASE_URL'): missing.append('DATABASE_URL')
    if len(password())<20: missing.append('WAR_ROOM_PASSWORD (at least 20 characters)')
    return {'interactive':True,'deployment':'vercel','on_demand_only':True,
            'authenticated':authenticated(request),'providers':providers,'missing_configuration':missing,
            'settings_url':'https://vercel.com/sunlit-xiangs-projects/macro-war-room/settings/environment-variables'}


@app.post('/api/war-room/login')
async def login(request: Request):
    same_origin(request); value=await body(request);supplied=value.get('password','')
    if len(password())<20: raise HTTPException(503,'WAR_ROOM_PASSWORD 尚未配置（至少20位）')
    if not isinstance(supplied,str) or not hmac.compare_digest(supplied.encode(),password().encode()): raise HTTPException(401,'Invalid owner password')
    response=JSONResponse({'authenticated':True})
    response.set_cookie(COOKIE,signed_cookie(int(time.time())+12*3600),httponly=True,
                        secure=request.url.scheme=='https',samesite='strict',max_age=12*3600,path='/api/war-room')
    return response


@app.post('/api/war-room/logout')
def logout(request: Request):
    same_origin(request);response=JSONResponse({'authenticated':False});response.delete_cookie(COOKIE,path='/api/war-room');return response


class SelectedRunStore:
    def __init__(self,store,job,pack): self.store=store;self.job=job;self.pack=pack
    def list(self,table,limit=100):
        if table=='macro_snapshots': return [self.pack['view']]
        rows=self.store.list(table,limit)
        if table in ('research_runs','research_sessions'): rows=[r for r in rows if r.get('research_run_id')==self.job['id']]
        return rows
    def get(self,table,key): return self.store.get(table,key)
    def as_of(self,table,instant,limit=10000):
        if table=='macro_snapshots': return self.list(table,limit)
        return self.store.as_of(table,instant,limit)


def job_view(store,job,language):
    pack=store.get('research_packs',job['pack_id']) if job.get('pack_id') else None
    data=board(SelectedRunStore(store,job,pack),job['asset'],language) if pack else read_public(f"war-room-{job['asset']}-{language}.json")
    checkpoints=[r for r in reversed(store.list('research_materials',10000)) if r.get('run_id')==job['id'] and r.get('kind')=='workflow_checkpoint']
    if job['status'] in ('starting','queued','running'):
        stages=[r for r in reversed(store.list('research_materials',10000)) if r.get('run_id')==job['id'] and r.get('kind')=='workflow_stage']
        by_key={c['checkpoint']:c for c in checkpoints}
        data['research_run']={'status':job['status'],'reports':[c['report'] for c in checkpoints],
            'process':[{'report_id':by_key.get(s['checkpoint'],{}).get('report',{}).get('id'),
                        'analyst':s['analyst'],'stage':s['stage'],'question':s['question'],
                        'status':by_key[s['checkpoint']]['report']['status'] if s['checkpoint'] in by_key else 'awaiting_result'} for s in stages]}
    data['job']=job
    data['research_pack']={k:v for k,v in (pack or {}).items() if k not in ('view',)}
    return data


@app.get('/api/war-room/{asset}')
async def get_board(asset: str, language: str='zh', run_id: str | None=None):
    contract(asset,language)
    if not os.getenv('DATABASE_URL'): return read_public(f'war-room-{asset}-{language}.json')
    store=storage()
    try:
        job=store.job(run_id) if run_id and re.fullmatch('[a-f0-9]{32}',run_id) else next(iter(store.jobs(asset,language)),None)
        if job and (job['asset'],job['language'])!=(asset,language): raise HTTPException(400,'Run identity mismatch')
        if job and job.get('workflow_id') and job['status'] in ('starting','queued','running'):
            try:
                state=await workflow.Run(job['workflow_id']).status()
                if state in ('failed','cancelled'):
                    store.update_job(job['id'],status=state,error='workflow_'+state)
                    job=store.job(job['id'])
            except workflow.RunExpiredError:
                store.update_job(job['id'],status='failed',error='workflow_expired')
                job=store.job(job['id'])
        return job_view(store,job,language) if job else read_public(f'war-room-{asset}-{language}.json')
    finally: store.close()


@app.post('/api/war-room/research')
async def start_research(request: Request):
    owner(request); value=await body(request)
    if not set(value)<= {'asset','language','provider','model','snapshot_id','request_id'}: raise HTTPException(400,'Unsupported parameter; secrets never belong here')
    asset=value.get('asset','gold');language=value.get('language','zh');contract(asset,language)
    provider=value.get('provider','deepseek');model=value.get('model')
    if provider not in (*PROVIDERS,'openai-compatible') or model and (not isinstance(model,str) or not re.fullmatch(r'[\w.\-/:]{1,100}',model)):
        raise HTTPException(400,'Invalid provider/model')
    cfg=config(provider,model)
    if cfg['status']!='configured': return JSONResponse({'status':cfg['status'],'work_done':False,'error':'Provider secret not configured in Vercel'},status_code=503)
    request_id=value.get('request_id','')
    if not isinstance(request_id,str) or not re.fullmatch(r'[a-zA-Z0-9\-]{16,80}',request_id): raise HTTPException(400,'Idempotency request_id required')
    store=storage()
    try:
        try: job,created=store.admit(request_id,asset,language,provider,cfg['model'])
        except ValueError as exc: raise HTTPException(429,str(exc)) from None
        if created:
            try:
                run=await workflow.start(team_research,job_id=job['id'])
                # Do not overwrite running/completed state if a fast workflow already advanced.
                store.update_job(job['id'],workflow_id=run.run_id)
                store.db.execute("UPDATE oracle_war_room.jobs SET status='queued' WHERE id=%s AND status='starting'",(job['id'],))
                job=store.job(job['id'])
            except Exception:
                store.update_job(job['id'],status='failed',error='workflow_start_failed')
                raise HTTPException(503,'Unable to enqueue durable research') from None
        return JSONResponse({'status':job['status'],'run_id':job['id'],'workflow_id':job['workflow_id'],
                             'work_done':False,'poll_url':f"/api/war-room/{asset}?language={language}&run_id={job['id']}"},status_code=202)
    finally: store.close()


@app.get('/api/war-room/{asset}/runs')
def runs(asset: str, language: str='zh'):
    contract(asset,language)
    if not os.getenv('DATABASE_URL'): return {'runs':[]}
    store=storage()
    try: return {'runs':store.jobs(asset,language)}
    finally:store.close()


@app.get('/api/war-room/{asset}/analysts/{analyst}')
def analyst_history(request: Request, asset: str, analyst: str, language: str='zh',run_id: str | None=None,snapshot_id: str | None=None):
    if not authenticated(request): raise HTTPException(401,'Owner sign-in required for private history')
    contract(asset,language)
    if analyst not in ROLES: raise HTTPException(400,'Unknown analyst')
    store=storage()
    try:
        job=store.job(run_id) if run_id else next(iter(store.jobs(asset,language)),None)
        if not job or job['asset']!=asset or job['language']!=language or not job.get('pack_id'): return {'turns':[]}
        pack=store.get('research_packs',job['pack_id']);view={**pack['view'],'research_run_id':job['id']}
        sid=session_key(view,analyst,language)
        questions={r['id']:r['question'] for r in store.list('research_requests',10000) if r.get('session_id')==sid}
        return {'turns':[{'question':questions.get(r['id']),**{k:r.get(k) for k in ('id','status','sections','summary','available_at')}}
                         for r in reversed(store.list('research_turns',10000)) if r.get('session_id')==sid]}
    finally:store.close()


@app.post('/api/war-room/ask')
async def ask(request: Request):
    owner(request);value=await body(request)
    if not set(value)<= {'asset','language','provider','model','snapshot_id','run_id','analyst','question'}: raise HTTPException(400,'Unsupported parameter')
    asset=value.get('asset');language=value.get('language');contract(asset,language)
    analyst=value.get('analyst');question=value.get('question');key=value.get('run_id','')
    if analyst not in ROLES or not isinstance(question,str) or not 1<=len(question)<=4000 or not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key): raise HTTPException(400,'Invalid follow-up')
    store=storage()
    try:
        job=store.job(key)
        if not job or (job['asset'],job['language'])!=(asset,language) or job['status'] not in ('completed','partial'):
            raise HTTPException(409,'Select a completed research run first')
        pack=store.get('research_packs',job['pack_id']);view={**pack['view'],'research_run_id':key,'research_pack':{k:v for k,v in pack.items() if k!='view'}}
        with store.step_lock(key,analyst,'private'):
            sid=session_key(view,analyst,language)
            count=sum(r.get('session_id')==sid for r in store.list('research_requests',10000))
            if count>=12: raise HTTPException(429,'Follow-up budget reached for this analyst/run')
            peers=[r for r in store.list('research_turns',10000) if r.get('research_run_id')==key and r.get('audience')=='daily']
            result=await run_in_threadpool(run_analyst,view,store,analyst,question,language=language,
                       provider=job['provider'],model=job['model'],peers=peers,phase='followup',
                       call=bounded_call(time.monotonic()+190),max_steps=4)
            return {k:result.get(k) for k in ('id','status','summary','sections','confidence','available_at')}
    finally:store.close()


@app.get('/data/{path:path}')
def data_proxy(path: str):
    if not re.fullmatch(r'(?:(?:macro-(?:gold|audnzd)|war-room-(?:gold|audnzd)-(?:zh|en)|gold(?:-[\w-]+)?|ledger-manifest|oracle-seed-(?:gold|audnzd))|(?:predictions|macro-snapshots)/[a-f0-9]{64})\.json',path):
        raise HTTPException(404,'Unknown public artifact')
    return read_public(path)


@app.get('/')
def home(): return FileResponse(PUBLIC/'war-room.html')


@app.get('/{path:path}')
def static(path: str):
    allowed={p.name for p in PUBLIC.iterdir() if p.is_file() and p.suffix in ('.html','.js','.css','.svg')}
    if path not in allowed: raise HTTPException(404,'Not found')
    return FileResponse(PUBLIC/path)
