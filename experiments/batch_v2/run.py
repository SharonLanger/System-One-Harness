"""RV2 command-line entry point; no model import until live execution."""
import sys
sys.dont_write_bytecode=True
import argparse,json
from pathlib import Path
from engine import create,run,resume_check,worker,vectors
from schema import load,validate

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases'); p.add_argument('--suite'); p.add_argument('--resume')
    p.add_argument('--mode',choices=['live','fixture'],default=None)
    p.add_argument('--rule-mode',choices=['direct','replay'],default=None)
    p.add_argument('--validate-only',action='store_true'); p.add_argument('--dry-run',action='store_true')
    p.add_argument('--max-calls',type=int); p.add_argument('--max-seconds',type=float); p.add_argument('--worker-timeout',type=float)
    p.add_argument('--worker',help=argparse.SUPPRESS); p.add_argument('--config-id',help=argparse.SUPPRESS)
    a=p.parse_args(argv)
    try:
        if a.worker: worker(a.worker,a.config_id); return 0
        if a.resume:
            if any([a.cases,a.suite,a.mode,a.rule_mode,a.max_calls is not None,a.max_seconds is not None,a.worker_timeout is not None,a.validate_only,a.dry_run]): raise ValueError('Resume uses frozen settings; do not supply new inputs/options')
            return run(Path(a.resume).resolve())
        if not a.cases or not a.suite: raise ValueError('--cases and --suite required')
        cases,suite=load(a.cases),load(a.suite); validate(cases,suite)
        limits={'max_calls':a.max_calls,'max_seconds':a.max_seconds,'worker_timeout':a.worker_timeout}
        import math
        if any(v is not None and (not math.isfinite(v) or v<=0) for v in limits.values()): raise ValueError('Limits must be positive finite numbers')
        mode=a.mode or 'fixture'; rule_mode=a.rule_mode or 'direct'
        vs=vectors(suite); n=len(cases['cases']); calls=len({(q['id'],c['id']) for q,r,c in vs})*n if rule_mode=='replay' else len(vs)*n
        print(json.dumps({'vectors':len(vs),'cases':n,'logical_outcomes':len(vs)*n,'inference_calls':calls,'mode':mode,'rule_mode':rule_mode},indent=2))
        if a.dry_run or not a.validate_only:
            from collections import Counter
            print(json.dumps({'noise_levels':dict(Counter(c['noise_level'] for c in cases['cases'])),'tags':dict(Counter(t for c in cases['cases'] for t in c['tags'])),'expected':dict(Counter(json.dumps(c['expected'],sort_keys=True) if isinstance(c['expected'],dict) else c['expected'] or 'unscored' for c in cases['cases'])),'exclusions':suite.get('exclusions',[]),'replay_reference_rule':suite['baseline']['rule_id'] if rule_mode=='replay' else None},indent=2))
        if a.validate_only or a.dry_run: return 0
        if not n: raise ValueError('Empty cases support validation/dry-run only')
        if a.mode is None: raise ValueError('Select --mode live or --mode fixture explicitly')
        root=create(cases,suite,mode,rule_mode,limits); print('Run folder: '+str(root),flush=True)
        return run(root)
    except (ValueError,OSError,ImportError) as exc:
        print(str(exc),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())

