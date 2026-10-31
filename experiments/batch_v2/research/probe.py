"""Opt-in, counted Mac interface probe. Uses installed assets; never installs packages."""
import argparse
import copy
import json
import math
import platform
from pathlib import Path
from .records import extract_answer
from .scores import transform_temperature
from .protocol import digest


def assess(observations, labels, *, known_source_temperature=None, precision_verified=False, tolerance=1e-6, verification_evidence=None):
    if not observations: raise ValueError('no probe observations')
    if not math.isfinite(tolerance) or tolerance<=0: raise ValueError('invalid parity tolerance')
    provenance=bool(verification_evidence and verification_evidence.get('precision_reference') and verification_evidence.get('source_temperature_reference'))
    precision_verified=bool(precision_verified and provenance)
    successes=[r for r in observations if r.get('status')=='completed' and r.get('answer')]
    extracted=[(r,extract_answer(r['answer'],labels)) for r in successes]
    supported=[r['requested_temperature'] for r,e in extracted if e['probabilities'] is not None]
    report={'route':'live_temperature_matrix','offline_verified':False,'precision_tolerance':tolerance,
        'requested_temperatures':[r['requested_temperature'] for r in observations],'supported_temperatures':supported,
        'unsupported':[{'temperature':r['requested_temperature'],'reason':r.get('error','invalid/missing probabilities')} for r in observations if r['requested_temperature'] not in supported],
        'effective_settings':[{'requested':r['requested_temperature'],'effective':r.get('effective_temperature'),'reason':r.get('effective_reason','not exposed at captured boundary')} for r in observations],
        'probability_observations':[{'requested':r['requested_temperature'],'original':e['probabilities'],'sum':sum(e['probabilities']) if e['probabilities'] else None,'logits_available':e['logits'] is not None,'availability':e['availability']} for r,e in extracted],
        'precision_verified':precision_verified,'known_source_temperature':known_source_temperature,'verification_evidence':verification_evidence,'parity':[]}
    source=next(((r,e) for r,e in extracted if r['requested_temperature']==known_source_temperature),None)
    if source:
        sr,se=source
        route='captured_logits' if se['logits'] is not None else ('verified_probability_transform' if precision_verified and known_source_temperature is not None else None)
        if route and provenance:
            for r,e in extracted:
                t=r['requested_temperature']
                if t is None or t<=0 or e['probabilities'] is None: continue
                try:
                    transformed=transform_temperature(se['logits'] if route=='captured_logits' else se['probabilities'],t,logits=route=='captured_logits',source_temperature=known_source_temperature)
                    delta=max(abs(a-b) for a,b in zip(transformed,e['probabilities']))
                    report['parity'].append({'temperature':t,'max_abs_error':delta,'passed':delta<=tolerance})
                except ValueError as exc: report['parity'].append({'temperature':t,'passed':False,'reason':str(exc)})
            if len({p['temperature'] for p in report['parity']})>=2 and all(p['passed'] for p in report['parity']): report.update(route=route,offline_verified=True)
    report['live_matrix_sufficient']=len({t for t in supported if t is not None})>=2
    return report


def run_probe(cases, suite, temperatures, *, max_calls, output, allow_live=False, known_source_temperature=None, precision_verified=False, tolerance=1e-6, verification_evidence=None):
    if not allow_live: raise ValueError('explicit --allow-live required')
    if platform.system()!='Darwin': raise ValueError('live capability probe requires Mac; Linux fixtures do not establish capabilities')
    if not temperatures or len(temperatures)>max_calls: raise ValueError('probe would exceed counted call budget')
    if any(t is not None and (type(t) not in (int,float) or not math.isfinite(t) or t<=0) for t in temperatures): raise ValueError('positive finite temperatures required')
    path=Path(output)
    if path.exists(): raise ValueError('probe evidence output already exists')
    path.parent.mkdir(parents=True,exist_ok=True)
    from schema import validate
    from engine import execute, Boundary, resolve_model
    from laya_context_router.laya.config import RunConfig
    from laya_context_router.laya.registry import AgentRegistry
    validate(cases,suite)
    if not cases['cases']: raise ValueError('probe needs one preauthored interface input')
    question=next(q for q in suite['questions'] if q['id']==suite['baseline']['question_id'])
    rule=next(r for r in suite['rules'] if r['id']==suite['baseline']['rule_id'])
    base=next(c for c in suite['configurations'] if c['id']==suite['baseline']['config_id'])
    def loader(model,**kwargs):
        import laya_mlx
        return laya_mlx.load(str(resolve_model(model)),local_files_only=True,**kwargs)
    registry=AgentRegistry(loader=loader); observations=[]; calls=0
    state={'status':'running','campaign_ready':False,'mode':'live','platform':platform.platform(),'max_calls':max_calls,'attempted_calls':0,'observations':observations}
    with path.open('x') as stream: json.dump(state,stream,indent=2)
    def checkpoint():
        temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(state,indent=2,allow_nan=False)+'\n');temporary.replace(path)
    class CountedAgent:
        def __init__(self,agent):self.agent=agent
        def predict(self,*args,**kwargs):
            nonlocal calls
            if calls>=max_calls: raise ValueError('actual predict budget exhausted')
            calls+=1;state['attempted_calls']=calls;checkpoint()
            return self.agent.predict(*args,**kwargs)
    for t in temperatures:
        cfg={**base,'temperature':t}; boundary=None
        try:
            config=RunConfig.from_dict({k:v for k,v in cfg.items() if k!='id'})
            boundary=Boundary(CountedAgent(registry.get_agent(config)))
            execute(cases['cases'][0]['input'],question,rule,suite,config,boundary)
            answer=(boundary.raw or {}).get('answers',{}).get(question['definition']['name'])
            observations.append({'status':'completed','requested_temperature':t,'effective_temperature':None,
                'effective_reason':'not exposed at SDK boundary','answer':answer,'raw_response':boundary.raw,'payload':boundary.payload})
        except Exception as exc: observations.append({'status':'error','requested_temperature':t,'error':str(exc),'raw_response':getattr(boundary,'raw',None)})
        checkpoint()
    report=assess(observations,suite['labels'],known_source_temperature=known_source_temperature,precision_verified=precision_verified,tolerance=tolerance,verification_evidence=verification_evidence)
    report.update(platform=platform.platform(),mode='live',attempted_calls=calls,max_calls=max_calls,observations=observations,
        cases_hash=digest(cases),suite_hash=digest(suite),campaign_ready=report['live_matrix_sufficient'],
        capability_provenance={'suite_hash':digest(suite),'requested_boundaries':[min(t for t in temperatures if t is not None),max(t for t in temperatures if t is not None)] if any(t is not None for t in temperatures) else None,'effective_settings_verified':False},
        limitations=['Requested support means successful returned distributions, not proof of effective numeric setting.','Offline route requires separately verified precision/T0 provenance.'])
    report['status']='completed'
    path.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',required=True);p.add_argument('--suite',required=True);p.add_argument('--temperatures',default='[null,0.5,1,1.5,2,3,5]');p.add_argument('--max-calls',type=int,required=True);p.add_argument('--output',required=True);p.add_argument('--allow-live',action='store_true')
    a=p.parse_args(); from .records import load
    report=run_probe(load(a.cases),load(a.suite),json.loads(a.temperatures),max_calls=a.max_calls,output=a.output,allow_live=a.allow_live)
    print(json.dumps({k:report[k] for k in ('route','attempted_calls','campaign_ready')},indent=2))
if __name__=='__main__': main()
