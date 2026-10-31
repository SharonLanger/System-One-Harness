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
