"""Pure metrics; Brier uses sum over canonical classes. No IO/model dependency."""
import math
from .scores import distribution


def classification(expected, predicted, labels):
    if len(labels) < 2 or len(labels) != len(set(labels)) or len(expected) != len(predicted):
        raise ValueError('invalid labels or paired lengths')
    index = {label:i for i,label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for actual, guess in zip(expected,predicted):
        if actual not in index or guess not in index:
            raise ValueError('noncanonical label')
        matrix[index[actual]][index[guess]] += 1
    n = len(expected)
    support = [sum(row) for row in matrix]
    totals = [sum(row[j] for row in matrix) for j in range(len(labels))]
    correct = sum(matrix[i][i] for i in range(len(labels)))
    recall = [matrix[i][i]/s if s else None for i,s in enumerate(support)]
    f1 = [2*matrix[i][i]/(support[i]+totals[i]) if support[i]+totals[i] else 0 for i in range(len(labels))]
    denominator = math.sqrt((n*n-sum(p*p for p in totals))*(n*n-sum(t*t for t in support)))
    present = [v for v in recall if v is not None]
    return {'n':n,'labels':list(labels),'confusion':matrix,'support':dict(zip(labels,support)),
            'recall':dict(zip(labels,recall)), 'accuracy':correct/n if n else None,
            'balanced_accuracy_present_classes':sum(present)/len(present) if present else None,
            'missing_classes':[l for l,s in zip(labels,support) if not s],
            'comparable_all_classes':all(support), 'macro_f1':sum(f1)/len(labels) if n else None,
            'mcc':(correct*n-sum(p*t for p,t in zip(totals,support)))/denominator if denominator else (0 if n else None),
            'mcc_degenerate':bool(n and not denominator)}


def probability_quality(expected, probabilities, labels, clip=1e-15):
    if len(expected) != len(probabilities) or not 0 < clip < 1:
        raise ValueError('invalid paired lengths or clip')
    losses=[]; briers=[]; clipped=[]; metadata=[]
    for actual, original in zip(expected, probabilities):
        if actual not in labels or len(original) != len(labels): raise ValueError('invalid class/vector')
        p, meta = distribution(original); metadata.append(meta)
        correct = p[labels.index(actual)]
        losses.append(-math.log(correct) if correct else math.inf)
        clipped.append(-math.log(max(clip,correct)))
        briers.append(sum((v-(label==actual))**2 for label,v in zip(labels,p)))
    n=len(losses); infinite=any(math.isinf(v) for v in losses)
    return {'n':n,'strict_nll':None if not n or infinite else sum(losses)/n,
            'strict_nll_status':'unavailable_empty' if not n else ('infinite_zero_probability' if infinite else 'finite'),
            'brier_sum':sum(briers)/n if n else None,
            'clipped_nll_diagnostic':sum(clipped)/n if n else None,'clip':clip,
            'zero_count':sum(m['zero_count'] for m in metadata),
            'normalization_corrections':sum(m['normalization_correction'] for m in metadata),
            'zero_origin':'exact_or_rounded_unknown'}


def gate(correct, accepted):
    if len(correct) != len(accepted) or any(type(v) is not bool for v in list(correct)+list(accepted)):
        raise ValueError('gate requires paired booleans')
    cells={k:0 for k in ('AC','AW','RC','RW')}
    for c,a in zip(correct,accepted): cells[('A' if a else 'R')+('C' if c else 'W')] += 1
    ac,aw,rc,rw=(cells[k] for k in ('AC','AW','RC','RW')); n=len(correct); a=ac+aw
    d=math.sqrt((ac+aw)*(ac+rc)*(rw+aw)*(rw+rc))
    return {**cells,'n':n,'accepted_n':a,'coverage':a/n if n else None,'accepted_error':aw/a if a else None,
            'correct_accepted_yield':ac/n if n else None,'gate_mcc':(ac*rw-aw*rc)/d if d else (0 if n else None),
            'gate_mcc_degenerate':bool(n and not d)}


def risk_coverage(correct, values, higher=True):
    if len(correct)!=len(values) or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):
        raise ValueError('invalid score vector')
    points=[{'threshold':None,'endpoint':'all_reject',**gate(correct,[False]*len(correct))}]
    previous=0; area=0
    for threshold in sorted(set(values),reverse=higher):
        accepted=[v>=threshold if higher else v<=threshold for v in values]
        point={'threshold':threshold,**gate(correct,accepted)}; points.append(point)
        area += (point['coverage']-previous)*point['accepted_error']; previous=point['coverage']
    return {'points':points,'grouped_step_aurc':area if correct else None,'convention':'complete tied-score groups; right-step observed risk'}
