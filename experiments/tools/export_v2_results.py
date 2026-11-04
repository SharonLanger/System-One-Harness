"""Read-only, standard-library export of stopped V2 replay runs. No SDK imports."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

# PyCharm: set these paths, confirm the source run has stopped, then Run.
SOURCE_RUN = None
DESTINATION_PARENT = None
ROLES_FILE = None
SOURCE_STOPPED = False
SAFE = re.compile(r'^[a-z0-9][a-z0-9-]*$')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('Nonfinite JSON number: ' + value)


def read(path, lossless=True):
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_float=Decimal if lossless else float, parse_constant=reject_constant)


def encode(value):
    """Strict JSON; Decimal retains the original finite numerical value."""
    if isinstance(value, Decimal):
        require(value.is_finite(), 'Nonfinite Decimal')
        return str(value)
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k, ensure_ascii=False)+':'+encode(v) for k,v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(map(encode, value)) + ']'
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def write(path, value):
    Path(path).write_text(encode(value)+'\n', encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def legacy_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def safe_id(value):
    require(isinstance(value, str) and SAFE.fullmatch(value), 'Unsafe ID: '+str(value))
    return value


def catalog(entries):
    out = {}
    for entry in entries:
        key = safe_id(entry['id'])
        require(key not in out, 'Duplicate definition ID: '+key)
        out[key] = entry
    return out


def source_snapshot(source, roles_file):
    # Hash only raw evidence and provenance, never traverse rule-result JSON.
    files = [source/'manifest.json']
    files += [p for p in (source/'attempts.json', source/'active.json') if p.exists()]
    files += sorted((source/'inferences').glob('*.json'))
    if roles_file:
        files.append(roles_file)
    h = hashlib.sha256()
    for path in files:
        require(not path.is_symlink() and path.is_file(), 'Source evidence must be regular files')
        h.update(str(path).encode()); h.update(digest(path).encode())
    return h.hexdigest()


def folder(config):
    t = config['temperature']
    if t is None:
        return 'temperature-sdk-default'
    require(not isinstance(t, bool) and isinstance(t, (int,float,Decimal)) and math.isfinite(t) and t>=0,
            'Unsupported temperature')
    text = format(Decimal(str(t)).normalize(), 'f')
    if '.' not in text:
        text += '.0'
    return 'temperature-'+text


def expected_payload(case, question, config):
    definition = question['definition']
    require(isinstance(case['input'], str) and case['input'].strip(), 'Unsupported input')
    require(definition['type'] in ('choice','noul'), 'Unsupported question type')
    body = {k:v for k,v in definition.items() if k!='name'}
    kwargs = {} if config['temperature'] is None else {'lang':config['lang']}
    return {'text':case['input'], 'questions':{definition['name']:body}, 'predict_kwargs':kwargs}


def record(raw, iid, case, question, config):
    require(raw.get('id')==iid, 'Inference identity mismatch')
    require(raw.get('requested_config')==config, 'Requested configuration mismatch')
    # Null payload is possible only when failure happened before SDK invocation.
    payload = raw.get('payload')
    require(payload==expected_payload(case,question,config) or
            (payload is None and raw.get('error') is not None and raw.get('raw_response') is None),
            'Saved request differs from reconstructed request')
    if payload is not None and question['definition']['type']=='choice':
        name=question['definition']['name']
        require(list(payload['questions'][name]['criteria'])==list(question['definition']['criteria']),
                'Choice order differs from reconstructed request')
    require(raw.get('status') in ('completed','error'), 'Unsupported inference status')
    require((raw['status']=='error') == (raw.get('error') is not None), 'Conflicting error status')
    require('raw_response' in raw, 'Missing raw_response field')
    timing_keys = {'inference_seconds','baseline_rule_seconds','load_seconds','created_utc'}
    excluded = timing_keys | {'id','status','error','raw_response','payload','requested_config','availability','logs','baseline_result'}
    return {'inference_id':iid,'case_id':case['id'],'question_id':question['id'],
        'config_id':config['id'],'status':'error' if raw['status']=='error' else 'success',
        'raw_response':raw['raw_response'],'error':raw.get('error'),
        'timing':{k:v for k,v in raw.items() if k in timing_keys},
        'availability':raw.get('availability',{}),
        'source_metadata':{k:v for k,v in raw.items() if k not in excluded}}


def export_run(source_run, destination_parent, *, source_stopped=False, roles_file=None):
    require(source_stopped is True, 'Confirm source process has stopped: source_stopped=True')
    source = Path(source_run).resolve(); parent = Path(destination_parent).resolve()
    require(source!=parent and source not in parent.parents, 'Destination must be outside source run')
    roles_file = Path(roles_file).resolve() if roles_file else None
    before = source_snapshot(source, roles_file)
    manifest = read(source/'manifest.json'); conventional = read(source/'manifest.json',False)
    require(manifest.get('schema_version')==1, 'Unsupported manifest schema_version')
    require(manifest.get('mode') in ('fixture','live'), 'Unsupported execution mode')
    suite = manifest['suite']; cases = catalog(manifest['cases']['cases'])
    require(suite['adapter']=='generic-question' and manifest['rule_mode']=='replay',
            'Initial exporter supports generic-question replay only')
    for key in ('cases','suite'):
        require(legacy_hash(conventional[key])==manifest[key+'_hash'], 'Definition hash mismatch: '+key)
    questions = catalog(suite['questions']); configs = catalog(suite['configurations'])
    rules = catalog(suite['rules'])
    for question in questions.values():
        definition=question['definition']
        if definition['type']=='choice':
            require(list(definition['criteria'])==suite['labels'], 'Catalog choice order differs from labels')
    for item in suite.get('exclusions',[]):
        require(item['question_id'] in questions and item['rule_id'] in rules and item['config_id'] in configs,
                'Unknown exclusion reference')
    excluded = {(x['question_id'],x['rule_id'],x['config_id']) for x in suite.get('exclusions',[])}
    grid = [(q,c) for q in questions for c in configs if any((q,r,c) not in excluded for r in rules)]
    # Scalar grid index only; raw responses are never accumulated.
    identities = {}
    for q,c in grid:
        for cid in cases:
            iid = legacy_hash([q,None,c,cid])[:32]
            require(iid not in identities, 'Inference hash collision')
            identities[iid] = (cid,q,c)
    mapping = {c:folder(configs[c]) for c in configs}
    require(len(set(mapping.values()))==len(mapping), 'Ambiguous temperature folder mapping')
    parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.export-',dir=parent))
    destination = parent/datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%Y-%m-%d_%H-%M-%S')
    suffix=0
    while destination.exists():
        suffix+=1; destination=parent/(datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%Y-%m-%d_%H-%M-%S')+f'_{suffix:03}')
    try:
        definitions = {'format_version':1,'source_manifest':manifest,
            'roles':read(roles_file) if roles_file else None}
        write(temp/'definitions.json',definitions)
        partitions={}
        for q,c in grid:
            rel=f'predictions/{mapping[c]}/{q}.jsonl'; path=temp/rel
            path.parent.mkdir(parents=True,exist_ok=True); path.touch()
            partitions[q,c]={'question_id':q,'config_id':c,'path':rel,'planned':len(cases),'found':0,'success':0,'error':0}
        seen=set()
        for path in (source/'inferences').glob('*.json'):
            iid=path.stem
            require(iid in identities and iid not in seen,'Unknown/duplicate inference: '+iid)
            cid,q,c=identities[iid]; raw=read(path)
            out=record(raw,iid,cases[cid],questions[q],configs[c]); part=partitions[q,c]
            with (temp/part['path']).open('a',encoding='utf-8') as stream:
                stream.write(encode(out)+'\n')
            seen.add(iid); part['found']+=1; part[out['status']]+=1
        # Verify every line against source; only one prediction dictionary at a time.
        verified=set()
        for (q,c),part in partitions.items():
            with (temp/part['path']).open(encoding='utf-8') as stream:
                count=0
                for line in stream:
                    out=json.loads(line,parse_float=Decimal,object_pairs_hook=pairs,parse_constant=reject_constant)
                    iid=out['inference_id']; require(iid not in verified,'Duplicate exported ID')
                    require(iid in identities,'Unknown exported ID'); cid,eq,ec=identities[iid]
                    require((q,c)==(eq,ec),'Wrong partition')
                    require(out==record(read(source/'inferences'/f'{iid}.json'),iid,cases[cid],questions[q],configs[c]),'Round-trip mismatch')
                    verified.add(iid); count+=1
            require(count==part['found'],'Partition count mismatch')
            part.update(missing=part['planned']-count,bytes=(temp/part['path']).stat().st_size,sha256=digest(temp/part['path']))
        require(verified==seen,'Export/source ID mismatch')
        require(source_snapshot(source,roles_file)==before,'Source changed during export')
        totals={k:sum(p[k] for p in partitions.values()) for k in ('planned','found','success','error','missing')}
        source_bytes=sum(p.stat().st_size for p in source.rglob('*') if p.is_file() and not p.is_symlink())
        info={'format_version':1,'export_status':'complete','collection_status':'partial' if totals['missing'] else 'complete',
            'source_execution_status':manifest.get('status','unknown'),'source_run':str(source),
            'source_snapshot_sha256':before,'definitions_sha256':digest(temp/'definitions.json'),
            'source_stopped_acknowledged':True,'source_liveness_verified':False,
            'source_attempts':read(source/'attempts.json') if (source/'attempts.json').exists() else None,
            'config_folders':mapping,'partitions':list(partitions.values()),**totals,
            'source_folder_bytes':source_bytes,'source_inference_bytes':sum(p.stat().st_size for p in (source/'inferences').glob('*.json'))}
        # Fixed-point total includes export.json itself.
        info['export_bytes']=0
        for _ in range(10):
            write(temp/'export.json',info)
            total=sum(p.stat().st_size for p in temp.rglob('*') if p.is_file())
            if total==info['export_bytes']: break
            info['export_bytes']=total
        else: raise ValueError('Export size did not converge')
        require(source_snapshot(source,roles_file)==before,'Source changed before publication')
        # Reserve the final name exclusively so another existing export is never replaced.
        while True:
            try:
                destination.mkdir()
                break
            except FileExistsError:
                suffix+=1
                destination=parent/(datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%Y-%m-%d_%H-%M-%S')+f'_{suffix:03}')
        try:
            os.rename(temp,destination)
        except BaseException:
            destination.rmdir()
            raise
        return destination
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True)
        raise


if __name__=='__main__':
    require(SOURCE_RUN is not None and DESTINATION_PARENT is not None,
            'Set SOURCE_RUN and DESTINATION_PARENT in the settings section first')
    print(export_run(SOURCE_RUN,DESTINATION_PARENT,source_stopped=SOURCE_STOPPED,roles_file=ROLES_FILE))
