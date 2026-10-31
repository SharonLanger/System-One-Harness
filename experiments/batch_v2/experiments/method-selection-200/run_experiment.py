"""Campaign launcher. No arguments validate/dry-run without loading a model."""
import argparse,json,sys,platform
from pathlib import Path
HERE=Path(__file__).resolve().parent
RV2=HERE.parents[1]
sys.path[:0]=[str(RV2),str(HERE.parents[3]/'src')]
from schema import load,validate,hash_value

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validate-only',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--mode',choices=['live']);p.add_argument('--resume');p.add_argument('--max-seconds',type=float);p.add_argument('--worker-timeout',type=float)
    a=p.parse_args(argv)
    try:
        cases=load(HERE/'cases.json');suite=load(HERE/'rounds/001-small/suite.json');validate(cases,suite)
        original=load(RV2/'experiments/requested-action-500/versions/1/suite.json')
        if suite['rules']!=original['rules']:raise ValueError('source rule copy mismatch')
        if len(cases['cases'])!=200 or len(suite['questions'])!=2 or [c['temperature'] for c in suite['configurations']]!=[.5,.8,1.,1.1]:raise ValueError('campaign dimensions mismatch')
        if a.resume:
            if a.mode or a.smoke or a.max_seconds or a.worker_timeout:raise ValueError('resume uses frozen settings')
            from engine import run,resume_check
            m=resume_check(a.resume)
            if m['suite']['experiment_id']!='method-selection-200':raise ValueError('wrong campaign')
            return run(a.resume)
        if a.smoke:
            cases['cases']=[cases['cases'][0],next(c for c in cases['cases'] if 'absent' in c['tags'])];suite['questions']=suite['questions'][:1]
        n=len(cases['cases']);calls=n*len(suite['questions'])*len(suite['configurations']);vectors=len(suite['questions'])*len(suite['rules'])*len(suite['configurations'])
        print(json.dumps(dict(cases=n,vectors=vectors,inference_calls=calls,logical_outcomes=n*vectors),indent=2))
        if a.validate_only or a.dry_run or a.mode is None:return 0
        if platform.system()!='Darwin' or platform.machine()!='arm64':raise ValueError('live inference requires the configured Apple Silicon Mac')
        if any(v is not None and v<=0 for v in [a.max_seconds,a.worker_timeout]):raise ValueError('time limits must be positive')
        from engine import create,run,save
        root=create(cases,suite,'live','replay',dict(max_calls=calls,max_seconds=a.max_seconds,worker_timeout=a.worker_timeout))
        m=load(root/'manifest.json');m['campaign_kind']='smoke' if a.smoke else 'main';save(root/'manifest.json',m)
        print('Run folder:',root)
        code=run(root)
        if not a.smoke:
            from method_reporting import summarize
            summarize(root,allow_partial=bool(code))
        return code
    except (ValueError,OSError) as exc:print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
