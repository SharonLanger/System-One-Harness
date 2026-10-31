"""Isolated experimental gates; native rules are replayed through production read-only."""
import itertools
import math
from .metrics import gate, risk_coverage

SCALARS={'max_probability':True,'probability_gap':True,'normalized_entropy':False,'doctor':True,'raw_margin':True,'answer_confidence':True,'confidence':True}
OPS={'gte':lambda x,t:x>=t,'gt':lambda x,t:x>t,'lte':lambda x,t:x<=t,'lt':lambda x,t:x<t,'eq':lambda x,t:x==t}


def evaluate(score_rows, conditions):
    decisions=[]
    for row in score_rows:
        accepted=True
        for condition in conditions:
            field=condition['field']; op=condition['op']; threshold=condition['value']
            value=row.get(field)
            if field not in SCALARS or op not in OPS or type(threshold) not in (int,float) or not math.isfinite(threshold): raise ValueError('unsupported experimental condition')
            if value is None: raise ValueError('required score unavailable: '+field)
            accepted=accepted and OPS[op](value,threshold)
        decisions.append(accepted)
    return decisions


def frontier(points):
    valid=[p for p in points if p['accepted_error'] is not None]
    return [p for p in valid if not any(q['coverage']>=p['coverage'] and q['accepted_error']<=p['accepted_error'] and
             (q['coverage']>p['coverage'] or q['accepted_error']<p['accepted_error']) for q in valid)]


def sweep(correct, score_rows, field):
    if field not in SCALARS: raise ValueError('unknown scalar')
    values=[r.get(field) for r in score_rows]
    if any(v is None for v in values): return {'available':False,'reason':'missing '+field}
    curve=risk_coverage(correct,values,SCALARS[field])
    points=curve['points']; nondominated=frontier(points)
    return {'available':True,'field':field,'op':'gte' if SCALARS[field] else 'lte',**curve,'frontier':nondominated,
        'coverage_views':{str(target):min((p for p in points if p['coverage'] is not None and p['coverage']>=target),key=lambda p:(p['coverage'],p['accepted_error']),default=None) for target in (.25,.5,.75,.9,1)},
        'risk_views':{str(target):max((p for p in points if p['accepted_error'] is not None and p['accepted_error']<=target),key=lambda p:p['coverage'],default=None) for target in (.01,.02,.05)}}


def and_sweep(correct, score_rows, first='confidence', second='probability_gap'):
    if any(r.get(first) is None or r.get(second) is None for r in score_rows): return {'available':False,'reason':'missing AND score'}
    points=[{'thresholds':None,'endpoint':'all_reject',**gate(correct,[False]*len(correct))}]
    for a,b in itertools.product(sorted({r[first] for r in score_rows}),sorted({r[second] for r in score_rows})):
        mask=[r[first]>=a and r[second]>=b for r in score_rows]
        points.append({'thresholds':[a,b],**gate(correct,mask)})
    return {'available':True,'fields':[first,second],'op':'gte','points':points,'frontier':frontier(points),**reference_views(points),'aurc':None,'aurc_reason':'AND threshold pairs have no scalar ordering'}


def replay_native(raw, question, rule, suite, config, frozen_input):
    from engine import execute, Boundary, RecordedAgent
    from laya_context_router.laya.config import RunConfig
    # Exact input text has no labels/tags; runtime rules and derived rounding remain authoritative.
    result=execute(frozen_input,question,rule,suite,RunConfig.from_dict({k:v for k,v in config.items() if k!='id'}),Boundary(RecordedAgent(raw)))
    return result.decisions[question['definition']['name']]


def reference_views(points):
    return {'coverage_views':{str(target):min((p for p in points if p['coverage'] is not None and p['coverage']>=target),key=lambda p:(p['coverage'],p['accepted_error']),default=None) for target in (.25,.5,.75,.9,1)},
        'risk_views':{str(target):max((p for p in points if p['accepted_error'] is not None and p['accepted_error']<=target),key=lambda p:p['coverage'],default=None) for target in (.01,.02,.05)}}
