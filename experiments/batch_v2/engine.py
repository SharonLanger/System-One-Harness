"""Experiment-owned adapters, durable execution and isolated model workers."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import os
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import json, time, uuid, platform, subprocess, hashlib, importlib.metadata
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dataclasses import asdict
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from laya_context_router import log_utils
log_utils.LOG_PATH=HERE/'checks/output/runtime.jsonl'
from schema import load, validate, hash_value
from fixture_inspection import plumbing_provider

def now(): return datetime.now(timezone.utc).isoformat()
def save(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w') as f:
        json.dump(value,f,ensure_ascii=False,allow_nan=False,indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)

def file_hash(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): value.update(chunk)
    return value.hexdigest()

def source_fingerprint():
    return hash_value({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json')})

def versions():
    result={}
    for name in ('laya-mlx','mlx'):
        try: result[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: result[name]=None
    return result

def adapter_fingerprint():
    return hash_value({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))})

def model_fingerprint(suite,mode):
    if mode=='fixture': return {'fixture':hash_value(load(HERE/'examples/generic-choice/responses.json'))}
    values={}
    for cfg in suite['configurations']:
        path=resolve_model(cfg['model'])
        values[cfg['id']]={str(p.relative_to(path)):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':file_hash(p)} for p in sorted(path.rglob('*')) if p.is_file()}
        for name in ('rl_agent_config.json','encoder/config.json'):
            values[cfg['id']][name]['sha256']=hashlib.sha256((path/name).read_bytes()).hexdigest()
    return values

def resolve_model(model):
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['TRANSFORMERS_OFFLINE']='1'
    path=Path(model).expanduser()
    if not path.is_dir():
        from huggingface_hub import try_to_load_from_cache
        cached=try_to_load_from_cache(model,'rl_agent_config.json')
        if not isinstance(cached,str): raise ValueError('Model not cached locally: '+model)
        path=Path(cached).parent
    for name in ('rl_agent_config.json','encoder/config.json','model.safetensors'):
        if not (path/name).is_file(): raise ValueError('Missing local model asset: '+name)
    return path

def vectors(suite):
    exclusions={(e['question_id'],e['rule_id'],e['config_id']) for e in suite.get('exclusions',[])}
    return [(q,r,c) for q in suite['questions'] for r in suite['rules'] for c in suite['configurations'] if (q['id'],r['id'],c['id']) not in exclusions]

def case_path(root,q,r,c,case): return Path(root)/'batches'/f"{q['id']}__{r['id']}"/c['id']/'cases'/f"{case['id']}.json"
def inference_id(q,r,c,case,rule_mode): return hash_value([q['id'],r['id'] if rule_mode=='direct' else None,c['id'],case['id']])[:32]

def execute(input_data,question,rule,suite,config,registry):
    from laya_context_router.block_runtime import Block, PreparedInput
    from laya_context_router.answers.rules import RulesConfig
    from laya_context_router.block_runtime.catalog import Catalog, TypedRule
    from laya_context_router.questions.models import Question
    name=question['definition']['name']
    class ExperimentCatalog(Catalog):
        def rule(self,reference):
            if reference=='experiment-rule':
                d=deepcopy(rule['definition']); d['question_type']=suite['question_type']
                return TypedRule.from_dict(d)
            return super().rule(reference)
    catalog=ExperimentCatalog()
    if suite['adapter']=='generic-question':
        def valid(value):
            if not isinstance(value,str) or not value.strip(): raise ValueError('input must be a nonblank string')
            return value
        block=Block({'name':'experiment','questions':{name:{'definition':question['definition'],'rule_ref':'experiment-rule'}}},validate_input=valid,prepare_input=lambda v,qs:PreparedInput(v,qs,{}),reduce=lambda ds,_:{'label':ds.get(name,{}).get('answer','undecided')},validate_output=lambda x:x,catalog=catalog)
        return block.run(input_data,config=config,registry=registry)
    module='requested_action' if suite['adapter']=='requested-action' else 'context_scope'
    import importlib
    run=importlib.import_module('laya_context_router.building_blocks.questions.'+module+'.block').run
    return run(input_data,config=config,registry=registry,catalog=catalog,question_overrides={name:question['definition']},rule_overrides={name:'experiment-rule'})

class Boundary:
    def __init__(self,agent,*,inspector): self.inspector=inspector; self.agent=agent; self.raw=None; self.payload=None; self.seconds=None
    def get_inspector(self,config): return self.inspector
    def get_agent(self,config):
        outer=self
        class Agent:
            def predict(self,text,questions,**kwargs):
                outer.payload={'text':text,'questions':deepcopy(questions),'predict_kwargs':kwargs}; start=time.monotonic()
                try:
                    outer.raw=deepcopy(outer.agent.predict(text,questions,**kwargs)); return deepcopy(outer.raw)
                finally: outer.seconds=time.monotonic()-start
        return Agent()

class RecordedAgent:
    def __init__(self,raw): self.raw=raw
    def predict(self,*args,**kwargs): return deepcopy(self.raw)

def row_base(manifest,q,r,c,case,iid):
    return {**deepcopy(case),'case_id':case['id'],'experiment_id':manifest['suite']['experiment_id'],'run_id':manifest['run_id'],'question_id':q['id'],'rule_id':r['id'],'config_id':c['id'],'inference_id':iid,'inference_shared':manifest['rule_mode']=='replay','dataset_version':manifest['cases']['dataset_version'],'input_hash':hash_value(case['input']),'evaluation_kind':'rule-replay' if manifest['rule_mode']=='replay' and r['id']!=manifest['suite']['baseline']['rule_id'] else 'direct','question_hash':hash_value(q),'rule_hash':hash_value(r),'config_hash':hash_value(c),'_labels':manifest['suite']['labels']}

def worker(root,config_id):
    from laya_context_router import log_utils
    from laya_context_router.laya.config import RunConfig
    from laya_context_router.laya.registry import AgentRegistry
    from laya_context_router.answers.interpret import extract_answer
    from laya_context_router.answers.enrich import enrich_prediction
    root=Path(root); m=load(root/'manifest.json'); suite=m['suite']; cfg=next(c for c in suite['configurations'] if c['id']==config_id)
    config=RunConfig.from_dict({k:v for k,v in cfg.items() if k!='id'})
    log_utils.LOG_PATH=root/f'worker-{config_id}.jsonl'
    baseline=next(r for r in suite['rules'] if r['id']==suite['baseline']['rule_id'])
    fixture=load(HERE/'examples/generic-choice/responses.json') if m['mode']=='fixture' else None
    def loader(model,**kwargs):
        import laya_mlx
        return laya_mlx.load(str(resolve_model(model)),local_files_only=True,**kwargs)
    registry=None; load_seconds=0
    if m['mode']=='live':
        try:
            registry=AgentRegistry(loader=loader); start=time.monotonic(); agent=registry.get_agent(config); load_seconds=time.monotonic()-start
        except Exception as exc:
            save(root/f'worker-{config_id}-status.json',{'status':'configuration_error','error':str(exc)}); return
    inspector = registry.get_inspector(config) if registry is not None else plumbing_provider(None, config)
    trace_cursor=0
    def logs():
        nonlocal trace_cursor
        p=log_utils.LOG_PATH
        if not p.exists(): return []
        with p.open() as f:
            f.seek(trace_cursor); lines=f.readlines(); trace_cursor=f.tell()
        return [json.loads(l) for l in lines if l.strip()]
    for q in suite['questions']:
        selected=[r for qq,r,c in vectors(suite) if qq['id']==q['id'] and c['id']==config_id]
        for case in m['cases']['cases']:
            for rule in selected:
                dest=case_path(root,q,rule,cfg,case)
                if dest.exists(): continue
                iid=inference_id(q,rule,cfg,case,m['rule_mode']); ip=root/'inferences'/f'{iid}.json'
                start_rule=time.monotonic(); row=row_base(m,q,rule,cfg,case,iid)
                try:
                    if not ip.exists():
                        if fixture is not None:
                            key='|'.join([q['id'],config_id,case['id']]); raw=fixture['responses'][key]
                            boundary=Boundary(RecordedAgent(raw), inspector=inspector)
                        else: boundary=Boundary(agent, inspector=inspector)
                        
                        # Parent permits one prediction at a time, accounting failed attempts too.
                        attempts=root/'attempts.json'; count=load(attempts)['count'] if attempts.exists() else 0
                        cap=m['limits'].get('max_calls')
                        if cap is not None and count>=cap: return
                        save(attempts,{'count':count+1})
                        save(root/'active.json',{'config_id':config_id,'question_id':q['id'],'rule_id':rule['id'],'case_id':case['id'],'inference_id':iid,'started_utc':now()})
                        actual=baseline if m['rule_mode']=='replay' else rule
                        result=None; error=None
                        try: result=execute(case['input'],q,actual,suite,config,boundary)
                        except Exception as exc: error={'type':type(exc).__name__,'message':str(exc)}
                        record={'id':iid,'status':'error' if error else 'completed','error':error,'raw_response':boundary.raw,'payload':boundary.payload,'inference_seconds':boundary.seconds,'baseline_rule_seconds':max(0,time.monotonic()-start_rule-(boundary.seconds or 0)),'load_seconds':load_seconds,'baseline_result':asdict(result) if result else None,'logs':logs(),'requested_config':cfg,'effective_temperature':None,'availability':{'effective_temperature':'not exposed at the SDK boundary','tokens':'not exposed','checkpoint_revision':'local fingerprint in manifest','precision':'not exposed'},'created_utc':now()}
                        # Preserve malformed non-JSON SDK values without hiding a technical error.
                        try: json.dumps(record,allow_nan=False)
                        except (ValueError,TypeError): record['raw_response']={'unserializable_repr':repr(boundary.raw)}
                        save(ip,record)
                        (root/'active.json').unlink(missing_ok=True)
                    record=load(ip)
                    if record['error']: raise RuntimeError(record['error']['type']+': '+record['error']['message'])
                    if m['rule_mode']=='direct' or rule['id']==baseline['id']:
                        output=record['baseline_result']; rule_seconds=record['baseline_rule_seconds']
                    else:
                        rt=time.monotonic(); output=asdict(execute(case['input'],q,rule,suite,config,Boundary(RecordedAgent(record['raw_response']), inspector=inspector))); rule_seconds=time.monotonic()-rt
                    name=q['definition']['name']; answer=record['raw_response']['answers'][name]
                    decision=output['decisions'].get(name,{})
                    row.update(status=output['status'],raw_label=extract_answer(answer),final_label=decision.get('answer'),accepted=decision.get('decided'),reason=decision.get('reason',output['reason']),enriched=enrich_prediction(answer),block_result=output,inference_seconds=record['inference_seconds'],rule_seconds=rule_seconds,rule_definition=rule['definition'])
                except Exception as exc:
                    row.update(status='error',error={'type':type(exc).__name__,'message':str(exc)},raw_label=None,final_label=None,accepted=None)
                save(dest,row)
                save(root/f'heartbeat-{config_id}.json',{'completed_utc':now(),'last_case':case['id']})
    save(root/f'worker-{config_id}-status.json',{'status':'completed','load_seconds':load_seconds})

def create(cases,suite,mode,rule_mode,limits):
    validate(cases,suite)
    supported={('generic-question','choice'),('generic-question','noul'),('requested-action','choice'),('context-scope','choice')}
    if rule_mode=='replay' and (suite['adapter'],suite['question_type']) not in supported: raise ValueError('Replay parity not verified for adapter/type')
    parent=HERE/'results'/suite['experiment_id']; parent.mkdir(parents=True,exist_ok=True)
    while True:
        rid=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'__'+uuid.uuid4().hex[:10]; root=parent/rid
        try: root.mkdir(); break
        except FileExistsError: pass
    try: mf=model_fingerprint(suite,mode); model_error=None
    except Exception as exc: mf=None; model_error=str(exc)
    m={'schema_version':1,'run_id':rid,'cases':deepcopy(cases),'suite':deepcopy(suite),'cases_hash':hash_value(cases),'suite_hash':hash_value(suite),'mode':mode,'rule_mode':rule_mode,'limits':limits,'source_hash':source_fingerprint(),'adapter_hash':adapter_fingerprint(),'runtime_versions':versions(),'python':platform.python_version(),'model_fingerprint':mf,'model_error':model_error,'parity_revision':'rv2-offline-contracts-v1','source_revision':load(HERE/'source-snapshot.json'),'device':platform.machine(),'precision':None,'availability':{'precision':'not exposed by loader','effective_settings':'requested settings are not proof of effective settings'},'started_utc':now(),'started_local':datetime.now(ZoneInfo('Asia/Jerusalem')).isoformat(),'status':'created'}
    m['execution_hash']=hash_value({'mode':mode,'rule_mode':rule_mode,'limits':limits})
    vs=vectors(suite); n=len(cases['cases'])
    m['planned_counts']={'vectors':len(vs),'cases':n,'logical_outcomes':len(vs)*n,'inference_calls':len({(q['id'],c['id']) for q,r,c in vs})*n if rule_mode=='replay' else len(vs)*n}
    m['replay_reference_rule']=suite['baseline']['rule_id'] if rule_mode=='replay' else None
    m['excluded_baseline_note']='Replay may evaluate baseline internally when its vector is excluded; excluded vectors are not scored.'
    save(root/'manifest.json',m); return root

def resume_check(root):
    m=load(Path(root)/'manifest.json'); validate(m['cases'],m['suite'])
    for key,value in [('execution_hash',hash_value({k:m[k] for k in ('mode','rule_mode','limits')})),('cases_hash',hash_value(m['cases'])),('suite_hash',hash_value(m['suite'])),('source_hash',source_fingerprint()),('adapter_hash',adapter_fingerprint()),('runtime_versions',versions()),('python',platform.python_version())]:
        if m[key]!=value: raise ValueError('Resume mismatch: '+key)
    if m['model_error'] is None and model_fingerprint(m['suite'],m['mode'])!=m['model_fingerprint']: raise ValueError('Resume model mismatch')
    return m

def run(root):
    from reporting import collect
    root=Path(root); m=resume_check(root); start=time.monotonic(); m['status']='running'; save(root/'manifest.json',m)
    process=None; failure=False
    try:
        for cfg in m['suite']['configurations']:
            if m['model_error']:
                save(root/f"worker-{cfg['id']}-status.json",{'status':'configuration_error','error':m['model_error']}); failure=True; continue
            process=subprocess.Popen([sys.executable,'-B',str(HERE/'run.py'),'--worker',str(root),'--config-id',cfg['id']],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            worker_start=time.monotonic(); stop=None
            while process.poll() is None:
                elapsed=time.monotonic()
                if m['limits'].get('max_seconds') is not None and elapsed-start+m.get('wall_seconds',0)>=m['limits']['max_seconds']: stop='time_budget'
                if m['limits'].get('worker_timeout') is not None and elapsed-worker_start>=m['limits']['worker_timeout']: stop='timeout'
                if stop:
                    process.terminate()
                    try: process.wait(timeout=2)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
                    failure=True; save(root/f"worker-{cfg['id']}-status.json",{'status':stop})
                    active=root/'active.json'
                    if active.exists():
                        a=load(active)
                        if a['config_id']==cfg['id']:
                            q=next(q for q in m['suite']['questions'] if q['id']==a['question_id']); case=next(c for c in m['cases']['cases'] if c['id']==a['case_id'])
                            rs=[r for qq,r,c in vectors(m['suite']) if qq['id']==q['id'] and c['id']==cfg['id'] and (m['rule_mode']=='replay' or r['id']==a['rule_id'])]
                            for r in rs:
                                p=case_path(root,q,r,cfg,case)
                                if not p.exists(): save(p,{**row_base(m,q,r,cfg,case,a['inference_id']),'status':'timeout','error':stop})
                    break
                time.sleep(.03)
            if process.returncode not in (None,0):
                failure=True
                if not stop: save(root/f"worker-{cfg['id']}-status.json",{'status':'error','error':f'Worker exited {process.returncode}'})
            if stop=='time_budget': break
    except KeyboardInterrupt:
        if process and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        m['status']='interrupted'; failure=True
    finally:
        if m['status']!='interrupted': m['status']='completed'
        m['unique_inference_seconds']=sum((load(p).get('inference_seconds') or 0) for p in (root/'inferences').glob('*.json'))
        m['ended_utc']=now(); m['wall_seconds']=m.get('wall_seconds',0)+time.monotonic()-start
        m['inference_attempts']=load(root/'attempts.json')['count'] if (root/'attempts.json').exists() else 0
        rows=collect(root)
        if any(r['status'] in ('error','timeout','configuration_error') for r in rows): failure=True
        if any(r['status']!='completed' for r in rows): m['status']='partial'
        save(root/'manifest.json',m)
    return 1 if failure else 0
