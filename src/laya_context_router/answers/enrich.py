"""Original confidence mathematics, applied to a validated deep copy."""
from copy import deepcopy
import json
import math


def _number(value,minimum=0,maximum=1):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and minimum<=value<=maximum


def enrich_prediction(prediction):
    if not isinstance(prediction,dict) or prediction.get('type') not in ('choice','score','noul'):
        raise ValueError('unsupported prediction type')
    try: json.dumps(prediction,allow_nan=False)
    except (TypeError,ValueError) as exc: raise ValueError('prediction must be finite JSON') from exc
    result=deepcopy(prediction)
    kind=result['type']
    if kind in ('choice','score'):
        probs=result.get('probabilities',{})
        if not isinstance(probs,dict) or not all(_number(v) for v in probs.values()):
            raise ValueError('invalid probability distribution')
        if probs and not math.isclose(sum(probs.values()),1,abs_tol=0.001):
            raise ValueError('probabilities must sum to one')
        if len(probs)>=2:
            vals=sorted(probs.values(),reverse=True)
            result['probability_gap']=round(vals[0]-vals[1],4)
            entropy=-sum(p*math.log(p) for p in vals if p>0)
            max_entropy=math.log(len(vals))
            result['normalized_entropy']=round(entropy/max_entropy,4) if max_entropy>0 else 0.0
    else:
        noul=result.get('noul')
        if noul is not None:
            if not _number(noul): raise ValueError('noul must be finite and in [0,1]')
            result['distance_from_boundary']=round(abs(noul-0.5),4)
    return result


def enrich_response(raw):
    if not isinstance(raw,dict) or not isinstance(raw.get('answers'),dict):
        raise ValueError('response must contain answers mapping')
    result=deepcopy(raw)
    result['answers']={name:enrich_prediction(answer) for name,answer in raw['answers'].items()}
    return result
