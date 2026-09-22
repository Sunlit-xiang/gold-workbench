"""Append-only research artifacts. Mutable queues are deliberately not evidence."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class AssetStore:
    TABLES = ("payloads", "datasets", "models", "predictions", "outcomes", "reports", "events", "calibrations")

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        for table in self.TABLES:
            self.db.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL)")
            for action in ("UPDATE", "DELETE"):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'append-only evidence'); END")
        self.db.commit()

    def close(self):
        self.db.close()

    def put(self, table, body, key=None):
        if table not in self.TABLES:
            raise ValueError("unknown evidence table")
        body_hash = digest(body)
        key = key or body_hash
        existing = self.db.execute(f"SELECT hash FROM {table} WHERE id=?", (key,)).fetchone()
        if existing:
            if existing[0] != body_hash:
                raise ValueError(f"immutable identity conflict: {table}/{key}")
            return key
        self.db.execute(f"INSERT INTO {table} VALUES (?,?,?,?)", (key, utcnow(), canonical(body), body_hash))
        self.db.commit()
        return key

    def get(self, table, key):
        if table not in self.TABLES:
            raise ValueError("unknown evidence table")
        row = self.db.execute(f"SELECT body,hash FROM {table} WHERE id=?", (key,)).fetchone()
        if not row:
            return None
        body = json.loads(row[0])
        if digest(body) != row[1]:
            raise ValueError("evidence hash mismatch")
        return body

    def list(self, table, limit=100):
        if table not in self.TABLES:
            raise ValueError("unknown evidence table")
        rows = self.db.execute(f"SELECT id,body,hash FROM {table} ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for key, text, expected in rows:
            body = json.loads(text)
            if digest(body) != expected:
                raise ValueError("evidence hash mismatch")
            result.append({"id": key, **body})
        return result

    def latest(self, table):
        rows = self.list(table, 1)
        return rows[0] if rows else None

    def event(self, kind, **fields):
        return self.put("events", {"kind": kind, "time": utcnow(), **fields})

    def backup(self, path):
        target = Path(path)
        if target.exists():
            raise ValueError("backup destination already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(target) as backup:
            self.db.backup(backup)
