"""Durable, on-demand team orchestration. Each paid unit is checkpointed."""
import json
import os
import time
from urllib.request import Request, urlopen

from vercel import workflow
from digital_oracle.asset_store import canonical, digest, utcnow
from digital_oracle.research_team import run_analyst, public_report, ROLES, PROMPT_VERSION
from .store import CloudStore
from .pack import assemble

wf=workflow.Workflows(sandbox_policy=workflow.SandboxPolicy(share_sandboxes=True))


@wf.step(max_retries=0)
async def prepare(job_id: str) -> str:
    store=CloudStore()
    try:
        job=store.job(job_id)
        store.update_job(job_id,status='running')
        existing=next((p for p in store.list('research_packs',100) if p.get('run_id')==job_id),None)
        pack=existing or assemble(store,job)
        store.update_job(job_id,pack_id=pack['id'])
        return pack['id']
    except Exception as exc:
        store.update_job(job_id,status='failed',error=type(exc).__name__)
        raise workflow.FatalError('Research Pack unavailable') from None
    finally: store.close()


def bounded_call(deadline):
    def call(body,cfg):
        remaining=deadline-time.monotonic()
        if remaining<2: raise TimeoutError('research unit deadline')
        req=Request(cfg['base']+'/chat/completions',data=canonical(body).encode(),headers={
            'Authorization':'Bearer '+os.environ[cfg['secret_name']],'Content-Type':'application/json'})
        with urlopen(req,timeout=min(40,remaining)) as response: raw=response.read(1_000_001)
        if len(raw)>1_000_000: raise ValueError('provider response budget')
        return json.loads(raw)['choices'][0]['message']
    return call


@wf.step(max_retries=0)
async def investigate(job_id: str, pack_id: str, role: str, question: str, phase: str, stage: str) -> dict:
    store=CloudStore()
    try:
        with store.step_lock(job_id,role,phase):
            job=store.job(job_id); pack=store.get('research_packs',pack_id)
            view={**pack['view'],'research_run_id':job_id,
                  'research_pack':{k:v for k,v in pack.items() if k not in ('view',)}}
            peers=[r for r in reversed(store.list('research_turns',10000)) if r.get('research_run_id')==job_id and r.get('audience')=='daily']
            checkpoint=digest([job_id,role,phase,question])
            completed=store.get('research_materials',checkpoint)
            if completed: return completed['report']
            admission={'kind':'workflow_stage','run_id':job_id,'analyst':role,'stage':stage,'question':question,
                       'status':'running','available_at':utcnow(),'checkpoint':checkpoint}
            store.put('research_materials',admission)
            deadline=time.monotonic()+190
            from digital_oracle.research_team import fetch_official
            def fetch(url):
                if time.monotonic()+16>deadline: raise TimeoutError('tool deadline')
                return fetch_official(url)
            row=run_analyst(view,store,role,question,language=job['language'],provider=job['provider'],model=job['model'],
                            peers=peers,call=bounded_call(deadline),fetch=fetch,max_steps=4,audience='daily',phase=phase)
            # Durable job association lives outside immutable turn bodies.
            report=public_report(row)
            checkpoint_body={'kind':'workflow_checkpoint','run_id':job_id,'checkpoint':checkpoint,'analyst':role,
                             'stage':stage,'question':question,'report':report,'turn_id':row.get('id'),'available_at':utcnow()}
            store.put('research_materials',checkpoint_body,checkpoint)
            return report
    except Exception as exc:
        store.update_job(job_id,status='failed',error=type(exc).__name__)
        raise workflow.FatalError('Research unit interrupted; no automatic paid retry') from None
    finally: store.close()


@wf.step(max_retries=0)
async def finish(job_id: str, pack_id: str, reports: list) -> dict:
    store=CloudStore()
    try:
        job=store.job(job_id); pack=store.get('research_packs',pack_id)
        checkpoints=[r for r in reversed(store.list('research_materials',10000)) if r.get('run_id')==job_id and r.get('kind')=='workflow_checkpoint']
        final=next((r for r in reports if r.get('analyst')=='chief' and r.get('phase')=='final' and r.get('status')=='available'),None)
        run={'snapshot_id':pack['view']['id'],'research_run_id':job_id,'asset':job['asset'],'language':job['language'],
             'prompt_version':PROMPT_VERSION,'available_at':utcnow(),'reports':reports,
             'process':[{'report_id':c['report'].get('id'),'analyst':c['analyst'],'question':c['question'],
                         'stage':c['stage'],'status':c['report']['status'],'available_at':c['available_at']} for c in checkpoints],
             'status':'available' if final and all(r['status']=='available' for r in reports) else 'partial',
             'work_done':bool(final)}
        store.put('research_runs',run,digest(['run-final',job_id]))
        store.update_job(job_id,status='completed' if run['status']=='available' else 'partial')
        return {'id':job_id,'status':run['status']}
    finally: store.close()


@wf.workflow
async def team_research(job_id: str) -> dict:
    pack_id=await prepare(job_id)
    director=await investigate(job_id,pack_id,'director','Read the assembled Research Pack, identify answerable questions and assign targeted investigation.','plan','assignment')
    reports=[director]
    if director.get('status')=='available':
        for task in director.get('assignments',[]):
            reports.append(await investigate(job_id,pack_id,task['analyst'],task['question'],'plan','investigation'))
        reports.append(await investigate(job_id,pack_id,'skeptic','Audit actual specialist reports for time mismatches, duplicate evidence, missing pricing and alternative explanations.','review','critique'))
        review=await investigate(job_id,pack_id,'director','Read actual reports and critiques. Decide what evidence must be supplemented before synthesis.','review','review')
        reports.append(review)
        if review.get('status')=='available':
            for task in review.get('rework_requests',[]):
                reports.append(await investigate(job_id,pack_id,task['analyst'],task['question'],'review','supplement'))
            reports.append(await investigate(job_id,pack_id,'chief','Read all actual reports and write the final on-demand asset Brief. Preserve unresolved disagreements and missing evidence.','final','synthesis'))
    return await finish(job_id,pack_id,reports)
