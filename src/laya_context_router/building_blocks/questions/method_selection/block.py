"""Signature-only baseline; deterministic mechanics, no accuracy claim."""
from copy import deepcopy
import json
from pathlib import Path

from ....blocks import QuestionBlock

BLOCK_DIR = Path(__file__).parent


def run(text, source_outline, *, config, registry, max_candidates=64, max_input_chars=16000):
    """Return named decisions plus a source map kept outside inference inputs.

    Input budget counts Unicode characters in text plus compact question JSON,
    not tokens. Overflow is an explicit no-op; nothing is truncated.
    """
    if (type(max_candidates) is not int or max_candidates < 0
            or type(max_input_chars) is not int or max_input_chars <= 0):
        raise ValueError('budgets must be nonnegative candidates and positive input characters')
    if not isinstance(text, str):
        raise TypeError('text must be a string')
    candidates = source_outline.get('callables')
    if not isinstance(candidates, list):
        raise ValueError('outline must contain a candidate list')
    mapping = {}
    for candidate in candidates:
        if (not isinstance(candidate, dict) or not all(isinstance(candidate.get(k), str) and candidate[k]
                for k in ('id', 'name', 'signature')) or candidate['id'] == 'none_or_unclear'
                or candidate['id'] in mapping):
            raise ValueError('invalid or duplicate candidate')
        mapping[candidate['id']] = {**deepcopy(candidate), 'path': source_outline['path'],
                                   'source_hash': source_outline['source_hash']}
    def result(reason, decisions=None, selected_id=None):
        return {'selected_id': selected_id, 'reason': reason, 'decisions': decisions or {},
                'candidate_map': deepcopy(mapping)}
    if not candidates:
        return result('no_candidates')
    if len(candidates) > max_candidates:
        return result('candidate_budget_exceeded')
    block = QuestionBlock(BLOCK_DIR)
    payloads = {name: q.to_predict_dict() for name, q in block.questions.items()}
    sentinel = payloads['method']['criteria']['none_or_unclear']
    payloads['method']['criteria'] = {c['id']: c['signature'] for c in candidates}
    payloads['method']['criteria']['none_or_unclear'] = sentinel
    size = len(text) + len(json.dumps(payloads, ensure_ascii=False, separators=(',', ':')))
    if size > max_input_chars:
        return result('input_budget_exceeded')
    decisions = block.run(text, config=config, registry=registry, question_payloads=payloads)
    method, multiple = decisions['method'], decisions['multiple_relevant']
    if not method['decided']:
        return result('method_undecided', decisions)
    if method['answer'] == 'none_or_unclear':
        return result('no_single_match', decisions)
    if not multiple['decided']:
        return result('multiple_undecided', decisions)
    if multiple['answer'] == 'yes':
        return result('multiple_relevant', decisions)
    if method['answer'] not in mapping:
        return result('unknown_candidate', decisions)
    return result(None, decisions, method['answer'])
