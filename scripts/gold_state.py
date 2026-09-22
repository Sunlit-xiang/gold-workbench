"""Authenticated encrypted SQLite archives for GitHub Releases; never publish raw DBs."""
import argparse
from contextlib import closing
import gzip
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet
from digital_oracle.asset_store import AssetStore


def pack(db, output, key):
    store = AssetStore(db)
    try:
        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder)/"oracle.sqlite"
            with closing(sqlite3.connect(snapshot)) as backup:
                store.db.backup(backup)
            payload = gzip.compress(snapshot.read_bytes(), compresslevel=6, mtime=0)
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_bytes(Fernet(key).encrypt(payload))
    finally:
        store.close()


def unpack(source, db, key):
    target = Path(db)
    if target.exists():
        raise ValueError("Restore target already exists; refusing to replace an evidence ledger")
    raw = gzip.decompress(Fernet(key).decrypt(Path(source).read_bytes()))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    with closing(sqlite3.connect(target)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
    store = AssetStore(target)
    try:
        for table in store.TABLES:
            store.list(table, 1_000_000)  # verify content hashes before using any restored evidence
    finally:
        store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["pack","unpack","initialize"])
    parser.add_argument("--db",required=True)
    parser.add_argument("--archive",required=True)
    parser.add_argument("--repository")
    args=parser.parse_args()
    if args.command=="initialize":
        if not args.repository:
            parser.error("initialize requires a repository")
        existing=subprocess.check_output(["gh","secret","list","--repo",args.repository,"--json","name"],text=True)
        if 'ORACLE_STATE_KEY' in existing:
            raise ValueError("State key already exists; refusing to rotate it or invalidate archives")
        key=Fernet.generate_key()
        pack(args.db,args.archive,key)
        subprocess.run(["gh","secret","set","ORACLE_STATE_KEY","--repo",args.repository],input=key,check=True,capture_output=True)
        print("Encrypted seed prepared; state key stored in repository Secrets (not printed).")
    else:
        key=os.environ["ORACLE_STATE_KEY"].encode()
        if args.command=="pack":pack(args.db,args.archive,key)
        else:unpack(args.archive,args.db,key)
        print(args.command+" complete")


if __name__=="__main__":main()
