"""Postgres append-only evidence plus a separate mutable job index.

All identifiers are fixed; values are bound parameters. This schema cannot address
the local Gold SQLite ledger. Workflow state is not evidence and may be updated.
"""
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

import psycopg
from psycopg.types.json import Jsonb
from digital_oracle.asset_store import digest, utcnow
from digital_oracle.macro_store import MacroStore


class CloudStore:
    TABLES = (*MacroStore.TABLES, 'research_packs')

    def __init__(self):
        self.db=psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=8, autocommit=True)

    def close(self): self.db.close()

    def initialize(self):
        self.db.execute('CREATE SCHEMA IF NOT EXISTS oracle_war_room')
        self.db.execute('''CREATE TABLE IF NOT EXISTS oracle_war_room.evidence (
            seq BIGSERIAL UNIQUE, namespace TEXT NOT NULL, id TEXT NOT NULL, body JSONB NOT NULL,
            hash TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now(), PRIMARY KEY(namespace,id))''')
        self.db.execute('''CREATE OR REPLACE FUNCTION oracle_war_room.reject_evidence_change() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'append-only research evidence'; END $$''')
        # Install once without racing a concurrent connection.
        with self.db.transaction():
            self.db.execute("SELECT pg_advisory_xact_lock(723184010)")
            exists=self.db.execute("SELECT 1 FROM pg_trigger WHERE tgname='oracle_research_immutable' AND tgrelid='oracle_war_room.evidence'::regclass").fetchone()
            if not exists:
                self.db.execute('''CREATE TRIGGER oracle_research_immutable BEFORE UPDATE OR DELETE
                    ON oracle_war_room.evidence FOR EACH ROW EXECUTE FUNCTION oracle_war_room.reject_evidence_change()''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS oracle_war_room.jobs (
            id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, asset TEXT NOT NULL, language TEXT NOT NULL,
            provider TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL, workflow_id TEXT,
            pack_id TEXT, created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now(), error TEXT)''')

    def _table(self, table):
        if table not in self.TABLES: raise ValueError('outside research-only namespace')

    def put(self, table, body, key=None):
        self._table(table); expected=digest(body); key=key or expected
        self.db.execute('''INSERT INTO oracle_war_room.evidence(namespace,id,body,hash)
            VALUES(%s,%s,%s,%s) ON CONFLICT(namespace,id) DO NOTHING''',(table,key,Jsonb(body),expected))
        actual=self.db.execute('SELECT hash FROM oracle_war_room.evidence WHERE namespace=%s AND id=%s',(table,key)).fetchone()
        if actual[0]!=expected: raise ValueError('immutable identity conflict')
        return key

    def get(self, table, key):
        self._table(table)
        row=self.db.execute('SELECT body,hash FROM oracle_war_room.evidence WHERE namespace=%s AND id=%s',(table,key)).fetchone()
        if not row: return None
        if digest(row[0])!=row[1]: raise ValueError('evidence hash mismatch')
        return row[0]

    def list(self, table, limit=100):
        self._table(table)
        rows=self.db.execute('SELECT id,body,hash FROM oracle_war_room.evidence WHERE namespace=%s ORDER BY seq DESC LIMIT %s',(table,limit)).fetchall()
        if any(digest(r[1])!=r[2] for r in rows): raise ValueError('evidence hash mismatch')
        return [{'id':r[0],**r[1]} for r in rows]

    def latest(self, table): return next(iter(self.list(table,1)),None)

    def as_of(self, table, instant, limit=10000):
        cutoff=datetime.fromisoformat(instant.replace('Z','+00:00'))
        return [r for r in self.list(table,limit) if r.get('available_at',r.get('checked_at')) and
                datetime.fromisoformat(r.get('available_at',r.get('checked_at')).replace('Z','+00:00'))<=cutoff]

    def admit(self, request_id, asset, language, provider, model):
        with self.db.transaction():
            self.db.execute('SELECT pg_advisory_xact_lock(723184011)')
            old=self.db.execute('SELECT id FROM oracle_war_room.jobs WHERE request_id=%s',(request_id,)).fetchone()
            if old:
                previous=self.job(old[0])
                if (previous['asset'],previous['language'],previous['provider'],previous['model'])!=(asset,language,provider,model):
                    raise ValueError('idempotency request belongs to a different research contract')
                return previous,False
            # Owner-only application; one job at a time and a hard daily paid-call cap.
            active=self.db.execute("SELECT id FROM oracle_war_room.jobs WHERE status IN ('starting','queued','running') ORDER BY created_at DESC LIMIT 1").fetchone()
            if active:
                current=self.job(active[0])
                if (current['asset'],current['language'])!=(asset,language): raise ValueError('another asset/language research is still active')
                return current,False
            count=self.db.execute("SELECT count(*) FROM oracle_war_room.jobs WHERE created_at > now()-interval '24 hours'").fetchone()[0]
            if count>=int(os.getenv('WAR_ROOM_DAILY_LIMIT','8')): raise ValueError('daily research budget reached')
            key=uuid.uuid4().hex
            self.db.execute('''INSERT INTO oracle_war_room.jobs(id,request_id,asset,language,provider,model,status)
                VALUES(%s,%s,%s,%s,%s,%s,'starting')''',(key,request_id,asset,language,provider,model))
            return self.job(key),True

    def job(self, key):
        row=self.db.execute('''SELECT id,asset,language,provider,model,status,workflow_id,pack_id,
            created_at,updated_at,error FROM oracle_war_room.jobs WHERE id=%s''',(key,)).fetchone()
        if not row: return None
        names=('id','asset','language','provider','model','status','workflow_id','pack_id','created_at','updated_at','error')
        return {k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in zip(names,row)}

    def update_job(self, key, **fields):
        if not fields or not set(fields)<= {'status','workflow_id','pack_id','error'}: raise ValueError('invalid job fields')
        assignments=','.join(f'{k}=%s' for k in fields)
        self.db.execute(f'UPDATE oracle_war_room.jobs SET {assignments},updated_at=now() WHERE id=%s',(*fields.values(),key))

    def jobs(self, asset, language):
        ids=self.db.execute('SELECT id FROM oracle_war_room.jobs WHERE asset=%s AND language=%s ORDER BY created_at DESC LIMIT 20',(asset,language)).fetchall()
        return [self.job(r[0]) for r in ids]

    @contextmanager
    def step_lock(self, job_id, role, phase):
        # Session lock survives individual evidence commits; release on connection close.
        key=int(digest([job_id,role,phase])[:15],16)
        self.db.execute('SELECT pg_advisory_lock(%s)',(key,))
        try: yield
        finally: self.db.execute('SELECT pg_advisory_unlock(%s)',(key,))
