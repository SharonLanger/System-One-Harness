"""Bounded canonical evidence partitions. Atomic rewrite, no duplicate raw checkpoints."""
import json
from pathlib import Path

def read(root, iid):
    index=Path(root)/'evidence-index.json'
    entries=json.loads(index.read_text()) if index.exists() else {}
    if iid not in entries:return None
    records=json.loads((Path(root)/entries[iid]).read_text())
    return records[iid]

def write(root,q,cfg,iid,record):
    from engine import save
    root=Path(root);path=f'evidence/{q}__{cfg}.json'
    dest=root/path;records=json.loads(dest.read_text()) if dest.exists() else {}
    records[iid]=record
    if len(records)>500:raise ValueError('evidence partition limit')
    save(dest,records)
    ip=root/'evidence-index.json';index=json.loads(ip.read_text()) if ip.exists() else {}
    index[iid]=path;save(ip,index)

def all_records(root):
    ip=Path(root)/'evidence-index.json'
    if not ip.exists():return []
    index=json.loads(ip.read_text());cache={};out=[]
    for iid,path in index.items():
        if path not in cache:cache[path]=json.loads((Path(root)/path).read_text())
        record=cache[path][iid]
        if record['id']!=iid:raise ValueError('evidence identity mismatch')
        out.append(record)
    return out
