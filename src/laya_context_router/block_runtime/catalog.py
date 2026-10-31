"""Typed named defaults resolved using package resources, independent of cwd."""
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
import math
import re
from ..answers.rules import RulesConfig
from ..questions.models import Question
from ..json_utils import load_json
from .contracts import BlockConfigurationError

_TYPES = {'choice', 'noul', 'score'}
_COMMON = {'confidence', 'answer_confidence', 'action.act_probability'}
_FIELDS = {kind: _COMMON | extra for kind, extra in {
    'choice': {'probability_gap', 'normalized_entropy'},
    'score': {'probability_gap', 'normalized_entropy'},
    'noul': {'distance_from_boundary'},
}.items()}

def identifier(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', name):
        raise BlockConfigurationError(f'invalid catalog identifier: {name!r}')
    return name

class TypedRule(RulesConfig):
    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get('question_type') not in _TYPES:
            raise BlockConfigurationError('rule requires supported question_type')
        try:
            identifier(data.get('name'))
            base = RulesConfig.from_dict(data)
            if 'conditions_by_type' in data:
                raise ValueError('typed rules use only conditions')
            for condition in base.conditions:
                if condition['field'] not in _FIELDS[data['question_type']]:
                    raise ValueError(f"unsupported metric for {data['question_type']}: {condition['field']}")
                value = condition['value']
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError('metric threshold must be a finite number')
        except ValueError as exc:
            raise BlockConfigurationError(str(exc)) from exc
        result = cls(base.name, conditions=base.conditions)
        result.question_type = data['question_type']
        return result

class Catalog:
    def __init__(self, directory=None):
        root = Path(directory) if directory is not None else files('laya_context_router').joinpath('defaults')
        self._rules, self._questions = {}, {}
        for folder, target in [('rules', self._rules), ('questions', self._questions)]:
            try:
                paths = sorted(root.joinpath(folder).iterdir(), key=lambda p: p.name)
            except OSError as exc:
                raise BlockConfigurationError(f'catalog directory unavailable: {folder}') from exc
            for path in paths:
                if not path.name.endswith('.json'): continue
                try:
                    data = load_json(path)
                    value = TypedRule.from_dict(data) if folder == 'rules' else Question.from_dict(data)
                    name = identifier(value.name)
                    if name in target: raise ValueError(f'duplicate catalog name: {name}')
                    target[name] = value
                except (ValueError, TypeError, KeyError, OSError) as exc:
                    raise BlockConfigurationError(f'invalid {folder} catalog file {path.name}: {exc}') from exc

    def rule(self, name):
        identifier(name)
        try: return deepcopy(self._rules[name])
        except KeyError as exc: raise BlockConfigurationError(f'rule_not_found: {name}') from exc

    def question(self, name):
        identifier(name)
        try: return deepcopy(self._questions[name].to_predict_dict())
        except KeyError as exc: raise BlockConfigurationError(f'question_not_found: {name}') from exc
