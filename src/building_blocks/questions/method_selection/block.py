"""Signature-only baseline; deterministic mechanics, no accuracy claim."""
from copy import deepcopy
import json
from pathlib import Path

from blocks import QuestionBlock

BLOCK_DIR = Path(__file__).parent


def run_legacy(text, source_outline, *, config, registry, max_candidates=64, max_input_chars=16000):
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
    name_counts = {name: sum(c['name'] == name for c in candidates)
                   for name in {c['name'] for c in candidates}}
    labels = {}
    for candidate in candidates:
        label = candidate['name']
        if name_counts[label] > 1 or label == 'none_or_unclear':
            location = candidate.get('location', {})
            label += f"@{location.get('line', '?')}:{location.get('column', '?')}"
        if label in labels:
            raise ValueError('duplicate readable candidate label')
        labels[label] = candidate['id']
    def result(reason, decisions=None, selected_id=None):
        return {'selected_id': selected_id, 'reason': reason, 'decisions': decisions or {},
                'candidate_map': deepcopy(mapping), 'label_map': deepcopy(labels)}
    if not candidates:
        return result('no_candidates')
    if len(candidates) > max_candidates:
        return result('candidate_budget_exceeded')
    if len({c['signature'] for c in candidates}) != len(candidates):
        return result('ambiguous_candidates')
    block = QuestionBlock(BLOCK_DIR)
    payloads = {name: q.to_predict_dict() for name, q in block.questions.items()}
    sentinel = payloads['method']['criteria']['none_or_unclear']
    payloads['method']['criteria'] = {label: mapping[source_id]['signature'] for label, source_id in labels.items()}
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
    if method['answer'] not in labels:
        return result('unknown_candidate', decisions)
    return result(None, decisions, labels[method['answer']])


def run(text, source_outline, *, config, registry, max_candidates=64, max_input_chars=16000):
    """Compatibility dictionary adapter; legacy outlines retain their old contract."""
    from building_blocks.questions.method_selection_v2.block import run as run_v2
    # Older callers supplied partial outlines with opaque IDs. Keep that supported
    # without weakening the new interface's full compiler-outline contract.
    if (not isinstance(text, str) or not isinstance(source_outline, dict)
            or 'schema_version' not in source_outline):
        return run_legacy(text, source_outline, config=config, registry=registry,
                          max_candidates=max_candidates, max_input_chars=max_input_chars)
    result = run_v2({'text': text, 'source_outline': source_outline}, config=config,
                    registry=registry, max_candidates=max_candidates, max_input_chars=max_input_chars)
    return {'selected_id': result.data['selected_id'], 'reason': result.data['reason'],
            'decisions': result.decisions, 'candidate_map': result.data['candidate_map'],
            'label_map': result.data['label_map']}
