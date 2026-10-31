"""Deterministic live-matrix refinement proposals; does not invoke models."""
import math
from decimal import Decimal

DEFAULTS={'initial_grid':[0.5,1,1.5,2,3,5], 'steps':[0.1,0.02,0.02],
          'nll_tolerance':0.001,'brier_tolerance':0.001,'max_refinements':3}


def initial_grid(supported, include_default=True, settings=None):
    settings=settings or DEFAULTS
    numeric=[v for v in settings['initial_grid'] if v in supported]
    return {'temperatures':([None] if include_default else [])+numeric,
            'excluded':[{'temperature':v,'reason':'not verified supported'} for v in settings['initial_grid'] if v not in supported]}


def interval_points(low, high, step):
    a,b,s=map(lambda v:Decimal(str(v)),(low,high,step))
    if s<=0 or a>b: raise ValueError('invalid interval')
    if b-a<s: return sorted({float(a),float(b),float((a+b)/2)})
    values=[]; x=a
    while x<=b: values.append(float(x)); x+=s
    return sorted(set(values+[float(b)]))


def refine(curves, refinement, supported_range, settings=None, previous_best=None):
    settings={**DEFAULTS,**(settings or {})}; low,high=supported_range
    if low<=0 or high<low or not isinstance(refinement,int) or refinement<0: raise ValueError('invalid refinement/range')
    if refinement>=settings['max_refinements']: return {'stop':True,'reason':'three-refinement cap','temperatures':[],'questions':{}}
    step=settings['steps'][min(refinement,len(settings['steps'])-1)]; shared=set(); details={}
    for question,records in sorted(curves.items()):
        if not records or any(r.get('complete') is False or r.get('support_ids') is not None and r.get('support_ids')!=records[0].get('support_ids') for r in records):
            raise ValueError('incomplete or incomparable temperature evidence')
        # Null is a provenance-bearing SDK default, never a numeric point.
        numeric=[r for r in records if r['temperature'] is not None]
        if any(type(r['temperature']) not in (int,float) or not math.isfinite(r['temperature']) or not low<=r['temperature']<=high for r in numeric):
            raise ValueError('tested setting outside verified numeric range')
        objective='nll'
        if any(r.get('nll_status')=='infinite_zero_probability' for r in numeric): objective='brier'
        tolerance=settings[objective+'_tolerance']
        pairs={}
        for r in numeric:
            v=r.get(objective)
            if v is not None and math.isfinite(v):
                if r['temperature'] in pairs and pairs[r['temperature']]!=v: raise ValueError('ambiguous repeated temperature evidence')
                pairs[r['temperature']]=v
        if len(pairs)!=len({r['temperature'] for r in numeric}): raise ValueError('temperature objective unavailable; cannot select from reduced support')
        tested=sorted(pairs)
        if len(tested)<2:
            raise ValueError('insufficient numeric temperature curve')
        best=min(pairs.values()); minima=[t for t in tested if pairs[t]<=best+tolerance]
        flat=max(pairs.values())-best<=tolerance
        regions=[]; candidates=set()
        stable=bool(previous_best and question in previous_best and step<=.02 and previous_best[question]['objective']==objective and 0<=previous_best[question]['value']-best<tolerance)
        if not flat and not stable:
            for t in minima:
                i=tested.index(t); a=tested[max(0,i-1)]; b=tested[min(len(tested)-1,i+1)]
                regions.append([a,b]); candidates.update(interval_points(a,b,step))
        new=sorted(t for t in candidates if t not in tested and low<=t<=high)
        shared.update(new)
        details[question]={'status':'flat_plateau' if flat else ('fine_improvement_below_tolerance' if stable else ('refine' if new else 'no_new_requested_values')),
            'objective':objective,'tolerance':tolerance,'best':best,'near_minima':minima,'regions':regions,'step':step,'proposed':new,
            'default_retained':any(r['temperature'] is None for r in records),'representatives':tested if flat else minima,
            'boundary_note':'best within supported range' if low in minima or high in minima else None,
            'nll_diagnostics':[r.get('nll_status') for r in records]}
    return {'stop':not shared,'reason':'no new values or stable/flat curves' if not shared else 'refine shared matrix',
            'temperatures':sorted(shared),'questions':details,'settings':settings,'refinement':refinement,'effective_settings_note':'requested grid; effective temperature may be unobservable'}


def curves_from_evidence(evidences, roles):
    """Selection input contains only temperature-role records; combine verified rounds."""
    from .records import compatible
    from .metrics import probability_quality
    compatible([e['identity'] for e in evidences]);curves={};seen=set()
    for evidence in evidences:
        if evidence['stage']!='temperature' or evidence['run_status']!='completed': raise ValueError('complete temperature-role evidence required')
        vectors={}
        for row in evidence['rows']:
            if roles[row['source_family_id']]!='temperature': raise ValueError('forbidden temperature selection role')
            vectors.setdefault((row['question_id'],row['config_id']),[]).append(row)
        for (question,config),rows in vectors.items():
            settled=[r for r in rows if r['label_status']=='settled']
            if not settled or any(r['status']!='completed' or r['probabilities'] is None or r['raw_label'] is None for r in settled):
                raise ValueError('incomplete temperature probability support')
            temperature=rows[0]['requested_config']['temperature']
            identity=(question,temperature)
            if identity in seen:
                baseline_config=next(c for c in evidence['suite']['configurations'] if c['id']==evidence['suite']['baseline']['config_id'])
                if config!=baseline_config['id'] or temperature!=baseline_config['temperature']:
                    raise ValueError('multiple live inferences at same temperature need explicit repetition protocol')
                original=next(r for r in curves[question] if r['temperature']==temperature)
                original.setdefault('excluded_repeat_diagnostics',[]).append({'run_id':evidence['run_id'],'inference_ids':[r['inference_id'] for r in settled],
                    'reason':'predeclared baseline repeat excluded; earliest supplied frozen baseline evidence retained'})
                continue
            seen.add(identity)
            metric=probability_quality([r['expected'] for r in settled],[r['probabilities'] for r in settled],evidence['labels'])
            curves.setdefault(question,[]).append({'temperature':temperature,'nll':metric['strict_nll'],'nll_status':metric['strict_nll_status'],
                'brier':metric['brier_sum'],'complete':True,'support_ids':sorted(r['case_id'] for r in settled),
                'requested_config':rows[0]['requested_config'],'effective_temperature':rows[0]['effective_temperature'],
                'run_id':evidence['run_id'],'source_inference_ids':[r['inference_id'] for r in settled]})
    return curves
