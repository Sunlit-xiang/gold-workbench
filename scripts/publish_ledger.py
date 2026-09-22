"""Fail closed if a publication would rewrite frozen prediction or evaluated outcome."""
import argparse
import json
from pathlib import Path


def publish(source, destination):
    source, destination=Path(source),Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    incoming={p.name:p for p in source.glob('*.json')}
    for old in destination.glob('*.json'):
        if old.name not in incoming:
            raise ValueError('Ledger continuity failure: an old prediction is missing')
        before=json.loads(old.read_text(encoding='utf-8'))
        after=json.loads(incoming[old.name].read_text(encoding='utf-8'))
        if before['prediction']!=after['prediction']:
            raise ValueError('Frozen prediction changed')
        if before.get('outcome') and before['outcome']!=after.get('outcome'):
            raise ValueError('Frozen outcome changed')
    for filename,path in incoming.items():
        (destination/filename).write_bytes(path.read_bytes())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--destination',required=True)
    a=p.parse_args()
    publish(a.source,a.destination)
