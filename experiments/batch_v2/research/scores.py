"""Pure probability scores. Returned values never replace original evidence."""
import math


def distribution(values, tolerance=0.001):
    p = list(values)
    if len(p) < 2 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p):
        raise ValueError('invalid probability vector')
    total = sum(p)
    if total <= 0 or abs(total - 1) > tolerance:
        raise ValueError('probabilities do not sum to one within tolerance')
    return [v / total for v in p], {'original_sum': total, 'normalization_correction': total != 1, 'zero_count': p.count(0), 'zero_origin': 'exact_or_rounded_unknown'}


def scores(probabilities, logits=None, answer_confidence=None, confidence=None):
    p, metadata = distribution(probabilities)
    ordered = sorted(p, reverse=True)
    out = {'max_probability': ordered[0], 'probability_gap': ordered[0] - ordered[1],
           'normalized_entropy': -sum(v * math.log(v) for v in p if v) / math.log(len(p)),
           'doctor': sum(v*v for v in p), 'answer_confidence': answer_confidence, 'confidence': confidence,
           'raw_margin': None, 'probability_metadata': metadata}
    for name, value in (('answer_confidence', answer_confidence), ('confidence', confidence)):
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError('invalid ' + name)
    if logits is not None:
        if len(logits) != len(p) or any(type(v) not in (int,float) or not math.isfinite(v) for v in logits):
            raise ValueError('invalid logits')
        z = sorted(logits, reverse=True)
        out['raw_margin'] = z[0] - z[1]
    return out


def transform_temperature(values, temperature, *, logits=False, source_temperature=None):
    if type(temperature) not in (int,float) or not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('positive finite numeric temperature required')
    if logits:
        if len(values) < 2 or any(not math.isfinite(v) for v in values):
            raise ValueError('invalid logits')
        z = [v / temperature for v in values]
    else:
        p, metadata = distribution(values)
        if metadata['normalization_correction'] or any(v == 0 for v in p):
            raise ValueError('offline probability route requires full precision positive normalized probabilities')
        if source_temperature is None or not math.isfinite(source_temperature) or source_temperature <= 0:
            raise ValueError('known source temperature required')
        z = [math.log(v)*source_temperature/temperature for v in p]
    shift = max(z)
    exp = [math.exp(v-shift) for v in z]
    return [v/sum(exp) for v in exp]
