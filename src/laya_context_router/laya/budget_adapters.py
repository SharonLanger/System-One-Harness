"""Pinned LAYA sequence rules, independently qualified against upstream helpers.

Encoding/rendering mirrors mizorewww/laya-mlx at 2159c6c (Apache-2.0).
This implementation adds unrestricted component accounting instead of truncation.
The caller's public question validation remains authoritative.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading


class ExactTokenizer:
    """Tokenizer-only inspection, loaded explicitly without weights or SDK imports."""
    def __init__(self, vocabulary, configuration):
        from tokenizers import Tokenizer
        vocabulary, configuration = Path(vocabulary), Path(configuration)
        data, config_bytes = vocabulary.read_bytes(), configuration.read_bytes()
        self.fingerprints = {'tokenizer_sha256': hashlib.sha256(data).hexdigest(),
                             'config_sha256': hashlib.sha256(config_bytes).hexdigest()}
        self.backend = Tokenizer.from_str(data.decode('utf-8'))
        self.backend.no_padding()
        self.backend.no_truncation()
        self.lock = threading.RLock()
        config = json.loads(config_bytes)
        for name in ('cls_token', 'sep_token', 'pad_token', 'mask_token'):
            value = config.get(name)
            if isinstance(value, dict):
                value = value.get('content')
            token_id = self.backend.token_to_id(value) if isinstance(value, str) else None
            if token_id is None:
                raise ValueError(f'missing {name}')
            setattr(self, name, value)
            setattr(self, name + '_id', token_id)

    def encode(self, text):
        with self.lock:
            return self.backend.encode(text, add_special_tokens=False).ids


def serialize_state(state):
    return state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)


def encode_state(tok, state):
    return tok.encode(serialize_state(state).replace(tok.mask_token, ' '))


def normalize_question(question):
    kind = question['type']
    criteria = deepcopy(question.get('criteria'))
    if kind == 'choice' and isinstance(criteria, list):
        criteria = {c: None for c in criteria}
    elif kind == 'noul' and isinstance(criteria, dict):
        criteria = {str(k).lower(): v for k, v in criteria.items()}
    instructions = question['instructions']
    if not isinstance(instructions, str):
        instructions = json.dumps(instructions, ensure_ascii=False)
    result = {'t': kind, 'ins': instructions, 'crit': criteria}
    for key in ('labels', 'option_order'):
        if key in question:
            result[key] = deepcopy(question[key])
    return result


def render_criterion(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(', ', ': '), default=str)


def render_options(question):
    kind, criteria = question['t'], question['crit']
    if kind != 'noul' and 'labels' in question:
        raise ValueError('labels is only supported for noul questions')
    if kind == 'choice':
        return [str(k) if v is None or v == '' else f'{k}: {render_criterion(v)}' for k, v in criteria.items()]
    if kind == 'score':
        return [f'level {i}: {render_criterion(v)}' for i, v in enumerate(criteria)]
    if kind != 'noul':
        raise ValueError('unsupported question type')
    labels = question.get('labels', {'false': 'false', 'true': 'true'})
    if not isinstance(labels, dict) or set(labels) != {'false', 'true'} or not all(isinstance(v, str) and v.strip() for v in labels.values()) or labels['false'].strip() == labels['true'].strip():
        raise ValueError('noul labels must map false/true to distinct nonempty strings')
    criteria = criteria or {}
    defaults = {'false': 'no, the statement does not hold', 'true': 'yes, the statement holds'}
    return [labels[k].strip() + ': ' + (render_criterion(criteria[k]) if criteria.get(k) not in (None, '') else defaults[k]) for k in ('false', 'true')]


def encode_question(tok, definition):
    question = normalize_question(definition)
    options = render_options(question)
    order = question.get('option_order', list(range(len(options))))
    if not isinstance(order, (list, tuple)) or any(not isinstance(i, int) or isinstance(i, bool) for i in order) or sorted(order) != list(range(len(options))):
        raise ValueError('option_order must be a permutation of the option indices')
    keys = list(question['crit']) if question['t'] == 'choice' else (['false', 'true'] if question['t'] == 'noul' else list(range(len(options))))
    return {'instruction_ids': tok.encode(f"{question['t']} question: {question['ins'].replace(tok.mask_token, ' ')}"),
            'option_ids': [tok.encode(' ' + options[i].replace(tok.mask_token, ' ')) for i in order],
            'option_keys': [keys[i] for i in order], 'option_indices': list(order)}


def assemble_sequence(tok, state, question, *, max_len, head_max_len):
    """Reproduce the pinned builder for parity; callers never send this cut input."""
    inspected = inspect_head(tok, question, head_max_len=head_max_len)
    head, markers = inspected['ids'], inspected['markers']
    state_ids = encode_state(tok, state)
    room = max(0, max_len - len(head) - 1)
    kept = state_ids[max(0, len(state_ids) - room):] if isinstance(state, list) else state_ids[:room]
    return {'ids': (head + kept + [tok.sep_token_id])[:max_len],
            'markers': [p for p in markers if p < max_len]}


def violation(boundary, question_id, incoming, limit, retained, *, stage, unit='tokens', option_key=None, option_index=None):
    return {'boundary': boundary, 'question_id': question_id, 'option_key': option_key,
            'option_index': option_index, 'incoming': incoming, 'required': incoming,
            'limit': limit, 'retained': retained, 'unit': unit, 'stage': stage}


def inspect_head(tok, question, *, head_max_len, question_id=None):
    """Keep stage-local loss separate from final content retention."""
    parts = encode_question(tok, question)
    raw = parts['option_ids']
    initial = [[tok.mask_token_id] + ids[:48] for ids in raw]
    allowance = head_max_len - sum(map(len, initial))
    span_cap = max(4, (head_max_len - 16) // max(1, len(initial))) if allowance < 16 else None
    spans = [span[:span_cap] if span_cap is not None else span[:] for span in initial]
    instruction_limit = max(8, head_max_len - sum(map(len, spans)))
    instructions = parts['instruction_ids'][:instruction_limit]
    ids = [tok.cls_token_id] + instructions + [tok.sep_token_id]
    markers, violations, options = [], [], []
    for key, index, original, capped, span in zip(parts['option_keys'], parts['option_indices'], raw, initial, spans):
        markers.append(len(ids)); ids.extend(span)
        options.append({'key': key, 'index': index, 'required_text_tokens': len(original),
                        'after_initial_cap_text_tokens': len(capped)-1,
                        'shared_head_span_limit': span_cap,
                        'after_shared_head_text_tokens': len(span)-1})
        if len(original) > 48:
            violations.append(violation('option_text', question_id, len(original), 48, len(capped)-1,
                                        stage='initial_option_cap', unit='option_text_tokens', option_key=key, option_index=index))
        if len(span) < len(capped):
            violations.append(violation('shared_head_option', question_id, len(capped), span_cap, len(span),
                                        stage='head_redistribution', unit='marker_inclusive_tokens', option_key=key, option_index=index))
    ids.append(tok.sep_token_id)
    if len(instructions) < len(parts['instruction_ids']):
        violations.append(violation('instructions', question_id, len(parts['instruction_ids']), instruction_limit, len(instructions), stage='instruction_allowance'))
    return {'ids': ids, 'markers': markers, 'violations': violations,
            'measurement': {'instructions': {'required_tokens': len(parts['instruction_ids']), 'limit': instruction_limit, 'retained_tokens': len(instructions)},
                            'options': options, 'assembled_head_tokens': len(ids),
                            'untrimmed_head_tokens': 3 + len(parts['instruction_ids']) + sum(1 + len(o) for o in raw)}}


def inspect_request(tok, state, questions, *, model, max_len, head_max_len, request_id=None):
    """Measure every question before any request inference. Never alter input."""
    from .budget import make_report
    report = make_report(model, request_id=request_id)
    report.update(inspection_status='complete', questions=[],
                  tokenizer=deepcopy(getattr(tok, 'fingerprints', None)),
                  limits={'sequence_tokens': max_len, 'head_allocation_tokens': head_max_len,
                          'initial_option_text_tokens': 48, 'provenance': 'pinned_runtime_profile'})
    state_ids = encode_state(tok, state)
    for name, question in questions.items():
        head = inspect_head(tok, question, head_max_len=head_max_len, question_id=name)
        measurement = head['measurement']
        head_len = len(head['ids'])
        room = max(0, max_len-head_len-1)
        state_kept = min(room, len(state_ids))
        assembled = head_len + state_kept + 1
        final = min(max_len, assembled)
        untrimmed = measurement['untrimmed_head_tokens'] + len(state_ids) + 1
        markers_kept = sum(p < max_len for p in head['markers'])
        measurement['instructions']['final_retained_tokens'] = min(measurement['instructions']['retained_tokens'], max(0, max_len-1))
        for option, marker in zip(measurement['options'], head['markers']):
            option['final_retained_text_tokens'] = max(0, min(option['after_shared_head_text_tokens'], max_len-marker-1))
        measurement.update(question_id=name,
                           state={'required_tokens': len(state_ids), 'allowance': room, 'retained_tokens': state_kept,
                                  'direction': 'left' if isinstance(state, list) else 'right'},
                           untrimmed_sequence_tokens=untrimmed, before_final_slice_tokens=assembled,
                           final_sequence_tokens=final,
                           markers={'required': len(head['markers']), 'retained': markers_kept})
        violations = head['violations']
        if state_kept < len(state_ids):
            violations.append(violation('state', name, len(state_ids), room, state_kept, stage='state_allowance'))
        if untrimmed > max_len:
            violations.append(violation('full_request', name, untrimmed, max_len, final, stage='full_request_requirement'))
        if final < assembled:
            violations.append(violation('final_sequence', name, assembled, max_len, final, stage='final_sequence_slice'))
        if markers_kept < len(head['markers']):
            violations.append(violation('option_markers', name, len(head['markers']), markers_kept, markers_kept,
                                        stage='final_sequence_slice', unit='markers'))
        report['questions'].append(measurement)
        report['violations'].extend(violations)
    report['message'] = 'Input would lose content or structure' if report['violations'] else 'All measured input is retained'
    return report
