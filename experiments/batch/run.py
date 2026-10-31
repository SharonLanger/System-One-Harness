"""One fixed question, many labeled inputs, isolated sequential configurations."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reporting import save, comparison, diagnostics
from laya_context_router.questions.models import Question
from laya_context_router.answers.rules import RulesConfig
from laya_context_router.laya.config import RunConfig


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def unique_pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise ValueError(f'duplicate JSON key: {k}')
        d[k]=v
    return d


def load_json(path):
    def bad(value): raise ValueError(f'nonfinite JSON: {value}')
    return json.loads(Path(path).read_text(),object_pairs_hook=unique_pairs,parse_constant=bad)


def keys(obj, required, optional=()):
    if not isinstance(obj,dict) or not set(required)<=obj.keys() or obj.keys()-set(required)-set(optional):
        raise ValueError(f'expected keys {required}, optional {optional}')


def validate(d):
    keys(d,('schema_version','question','rule','cases','configurations'))
    if type(d['schema_version']) is not int or d['schema_version']!=1: raise ValueError('schema_version must be 1')
    q=d['question']; keys(q,('name','type','instructions'),('criteria',))
    if q['type'] not in ('choice','noul'): raise ValueError('only choice/noul supported')
    if not isinstance(q['instructions'],str) or not q['instructions'].strip(): raise ValueError('empty question')
    Question.from_dict(q)
    if q['type']=='noul' and 'criteria' in q: raise ValueError('noul has no criteria')
    labels=set(q['criteria']) if q['type']=='choice' else {'yes','no'}
    if 'undecided' in labels: raise ValueError('undecided is reserved')
    rule=d['rule']; keys(rule,('name','conditions'),('tags','conditions_by_type'))
    policy=RulesConfig.from_dict(rule)
    all_conditions=policy.conditions + [c for conditions in policy.conditions_by_type.values() for c in conditions]
    for condition in all_conditions:
        keys(condition,('field','op','value'))
        if condition['op']!='eq' and (type(condition['value']) not in (int,float) or not math.isfinite(condition['value'])):
            raise ValueError('ordered conditions require finite numeric thresholds')
    for field in ('cases','configurations'):
        if not isinstance(d[field],list) or not d[field]: raise ValueError(f'{field} must be nonempty')
    ids=set()
    for c in d['cases']:
        keys(c,('id','input','expected'))
        if not isinstance(c['id'],str) or not c['id'] or c['id'] in ids: raise ValueError('invalid/duplicate case ID')
        ids.add(c['id'])
        if not isinstance(c['input'],str) or not isinstance(c['expected'],str) or c['expected'] not in labels: raise ValueError('invalid case input/expected')
    names=set()
    for cfg in d['configurations']:
        keys(cfg,('name','model','temperature','lang'))
        n=cfg['name']
        if not isinstance(n,str) or not re.fullmatch('[a-z0-9][a-z0-9_-]*',n) or n in names or n=='comparison': raise ValueError('unsafe/duplicate/reserved configuration name')
        if cfg['temperature'] is None and cfg['lang']!='en': raise ValueError('SDK-default temperature supports only en; use explicit temperature for another lang')
        names.add(n); RunConfig.from_dict({k:v for k,v in cfg.items() if k!='name'})
    json.dumps(d,allow_nan=False)
    return d


def allocate(parent, stamp=None):
    stamp=stamp or datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%Y-%m-%d_%H-%M-%S')
    parent.mkdir(parents=True,exist_ok=True)
    for i in range(10000):
        p=parent/(stamp if not i else f'{stamp}_{i:03}')
        try: p.mkdir(); return p
        except FileExistsError: pass
    raise RuntimeError('too many timestamp collisions')


def fresh(d,cfg,mode):
    try: revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError): revision='unavailable'
    versions={}
    for p in ('laya-mlx','mlx','huggingface-hub'):
        try: versions[p]=importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError: versions[p]='not installed'
    return {'schema_version':1,'runner_version':1,'revision':revision,'python':sys.version,'versions':versions,
            'definition':deepcopy(d),'definition_sha256':hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest(),
            'configuration':deepcopy(cfg),'effective_settings':'not_exposed','mode':mode,'status':'running',
            'started_utc':timestamp(),'started_local':datetime.now(ZoneInfo('Asia/Jerusalem')).isoformat(),
            'cases':[],'events':[],'load_seconds':0,'duration_seconds':0}


def real_local_loader(model, **kwargs):
    # Fail closed: no network resolution or silent downloads, even for SDK helpers.
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    import laya_mlx
    path=Path(model).expanduser()
    if not path.is_dir():
        from huggingface_hub import try_to_load_from_cache
        cached=try_to_load_from_cache(model,'rl_agent_config.json')
        if not isinstance(cached,str):
            raise RuntimeError('local LAYA cache is missing rl_agent_config.json; prepare the model on your Mac first')
        # Keep the snapshot parent: resolving the symlink would select blobs/.
        path=Path(cached).parent
    required=('rl_agent_config.json','encoder/config.json','model.safetensors')
    missing=[name for name in required if not (path/name).is_file()]
    if missing:
        raise RuntimeError('local LAYA model is missing required assets: '+', '.join(missing))
    # Pass the resolved local directory so the SDK need not resolve the remote ID.
    return laya_mlx.load(str(path),local_files_only=True,**kwargs)


def execute_configuration(d,cfg,path,loader=None,*,inspection_provider=None):
    from laya_context_router import log_utils
    from laya_context_router.laya.registry import AgentRegistry
    from laya_context_router.laya.predict import predict
    from laya_context_router.answers.interpret import interpret, extract_answer
    path=Path(path); trace=path.with_suffix('.trace.tmp')
    old=log_utils.LOG_PATH; log_utils.LOG_PATH=trace
    r=fresh(d,cfg,'real' if loader is None else 'injected'); started=time.monotonic()
    q=Question.from_dict(d['question']); questions={q.name:q.to_predict_dict()}
    policy=RulesConfig.from_dict(d['rule'])
    config=RunConfig.from_dict({k:v for k,v in cfg.items() if k!='name'})
    cursor=0
    def events():
        nonlocal cursor
        if not trace.exists(): return []
        with trace.open() as f:
            f.seek(cursor); records=[json.loads(l) for l in f if l.strip()]; cursor=f.tell()
        return records
    def checkpoint():
        r['duration_seconds']=time.monotonic()-started
        save(r,path)
    try:
        checkpoint()
        registry=AgentRegistry(loader=loader or real_local_loader, inspection_provider=inspection_provider)
        t=time.monotonic()
        agent=registry.get_agent(config)
        r['load_seconds']=time.monotonic()-t; r['events']+=events()
        class Observed:
            raw=None
            def get_inspector(self, config): return registry.get_inspector(config)
            def get_agent(self,_):
                owner=self
                class Wrapper:
                    def predict(self,*args,**kwargs):
                        owner.raw=agent.predict(*args,**kwargs)
                        return owner.raw
                return Wrapper()
        observer=Observed()
        for case in d['cases']:
            c={**deepcopy(case),'started_utc':timestamp(),'recommendation':None,'final':None,
               'recommendation_outcome':'error','final_outcome':'error','payload':{'text':case['input'],'questions':deepcopy(questions)},'raw_response':None}
            r['cases'].append(c); observer.raw=None; stage='inference'; ct=time.monotonic()
            try:
                response=predict(case['input'],questions,config=config,registry=observer)
                c['inference_seconds']=time.monotonic()-ct
                c['raw_response']=deepcopy(observer.raw)
                c['recommendation']=extract_answer(response['answers'][q.name])
                from reporting import outcome
                c['recommendation_outcome']=outcome(c['recommendation'],case['expected'])
                stage='interpretation'; pt=time.monotonic()
                c['decision']=interpret(response,questions,{q.name:policy})[q.name]
                if str(c['decision'].get('reason','')).startswith('invalid_prediction:'): raise ValueError(c['decision']['reason'])
                c['final']=c['decision']['answer']; c['final_outcome']=outcome(c['final'],case['expected'])
                c['processing_seconds']=time.monotonic()-pt
            except Exception as exc:
                c['error']={'stage':stage,'type':type(exc).__name__,'message':str(exc)}
            except KeyboardInterrupt:
                c['error']={'stage':stage,'type':'KeyboardInterrupt','message':'interrupted'}
                raise
            finally:
                raw=observer.raw
                try: json.dumps(raw,allow_nan=False); c['raw_response']=deepcopy(raw)
                except (ValueError,TypeError): c['raw_response']={'invalid_json_representation':repr(raw)}
                c['events']=events()
                enriched=next((e['details']['enriched'] for e in c['events'] if e.get('component')=='enrichment' and e.get('event')=='completed'),None)
                c['enriched_response']=enriched
                if enriched is not None:
                    try: c['diagnostics']=diagnostics(enriched,policy.conditions_for(q.type),case['expected'],c['recommendation'])
                    except (TypeError,ValueError,KeyError) as exc: c['diagnostics_error']=str(exc)
                c['ended_utc']=timestamp(); c['duration_seconds']=time.monotonic()-ct
                checkpoint()
            print(f"{cfg['name']} {len(r['cases'])}/{len(d['cases'])}: {case['id']} {c['final_outcome']}",flush=True)
        r['status']='completed' if not any(c.get('error') for c in r['cases']) else 'completed_with_errors'
    except KeyboardInterrupt:
        r['status']='interrupted'; r['error']={'stage':'execution','message':'interrupted'}
    except Exception as exc:
        r['status']='failed'; r['error']={'stage':'load_or_execution','type':type(exc).__name__,'message':str(exc)}
    finally:
        r['events']+=events(); r['ended_utc']=timestamp()
        try:
            checkpoint()
            trace.unlink(missing_ok=True)
        finally: log_utils.LOG_PATH=old
    return r


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment',default='apple-choice')
    parser.add_argument('--configuration')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--output',help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if not re.fullmatch('[a-z0-9][a-z0-9_-]*',args.experiment): parser.error('invalid experiment name')
    folder=HERE/args.experiment
    if not folder.resolve().is_relative_to(HERE): parser.error('experiment escapes batch folder')
    try:
        if args.worker:
            if not args.configuration or not re.fullmatch('[a-z0-9][a-z0-9_-]*',args.configuration): raise ValueError('invalid worker configuration')
            output=Path(args.output).resolve()
            if not output.is_relative_to((folder/'results').resolve()): raise ValueError('output outside experiment results')
            snapshot=load_json(output/f'{args.configuration}.json')
            d=validate(snapshot['definition'])
        else:
            d=validate(load_json(folder/'experiment.json'))
        configs=[c for c in d['configurations'] if not args.configuration or c['name']==args.configuration]
        if not configs: raise ValueError('configuration not found')
        if args.worker:
            output=Path(args.output).resolve()
            if not output.is_relative_to((folder/'results').resolve()): raise ValueError('output outside experiment results')
            # Parent snapshot is authoritative if the definition changes mid-run.
            snapshot=load_json(output/f'{configs[0]["name"]}.json')
            r=execute_configuration(validate(snapshot['definition']),snapshot['configuration'],output/f'{configs[0]["name"]}.json')
            return 0 if r['status']=='completed' else 1
        output=allocate(folder/'results'); records=[]
        for cfg in configs:
            p=output/f'{cfg["name"]}.json'; save(fresh(d,cfg,'real'),p)
        interrupted=False
        worker_failed=False
        for cfg in configs:
            p=output/f'{cfg["name"]}.json'
            cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'--experiment',args.experiment,'--configuration',cfg['name'],'--worker','--output',str(output)]
            child=subprocess.Popen(cmd,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
            try: child.wait()
            except KeyboardInterrupt:
                child.terminate()
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired: child.kill(); child.wait()
                interrupted=True
            r=load_json(p)
            if child.returncode or interrupted:
                worker_failed=True
                r['status']='interrupted' if interrupted else 'failed'
                r.setdefault('error',{'stage':'worker','message':f'worker exit {child.returncode}'})
                save(r,p)
            comparison([load_json(output/f'{c["name"]}.json') for c in configs],output/'comparison.md')
            if interrupted: break
        records=[load_json(output/f'{c["name"]}.json') for c in configs]
        for r in records:
            if r['status']=='running': r['status']='unattempted'; save(r,output/f'{r["configuration"]["name"]}.json')
        comparison(records,output/'comparison.md')
        print(f'Results: {output}')
        return 0 if not worker_failed and all(r['status']=='completed' for r in records) else 1
    except Exception as exc:
        print(f'ERROR: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
