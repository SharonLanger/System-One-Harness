"""Inner policy validation and acceptance; no question envelope at this layer."""
from copy import deepcopy
from dataclasses import dataclass, field
import json
import math
from .conditions import OPS, evaluate_conditions


def _validate_conditions(conditions):
    if not isinstance(conditions,list): raise ValueError('conditions must be a list')
    for condition in conditions:
        if not isinstance(condition,dict) or not {'field','op','value'}<=condition.keys():
            raise ValueError('condition requires field, op and value')
        if not isinstance(condition['field'],str) or not condition['field'] or any(not part for part in condition['field'].split('.')):
            raise ValueError('condition field must be a dotted path')
        if not isinstance(condition['op'],str) or condition['op'] not in OPS:
            raise ValueError('unknown condition operator')
        try: json.dumps(condition['value'],allow_nan=False)
        except (TypeError,ValueError) as exc: raise ValueError('condition value must be finite JSON') from exc

@dataclass
class RulesConfig:
    name: str
    tags: list[str] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)
    conditions_by_type: dict[str,list[dict]] = field(default_factory=dict)

    def conditions_for(self,prediction_type):
        return deepcopy(self.conditions+self.conditions_by_type.get(prediction_type,[]))

    @classmethod
    def from_file(cls,path):
        with open(path) as handle: return cls.from_dict(json.load(handle))

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or not isinstance(data.get('name'),str) or not data['name'] or 'conditions' not in data:
            raise ValueError('policy requires name and conditions')
        _validate_conditions(data['conditions'])
        by_type=data.get('conditions_by_type',{})
        if not isinstance(by_type,dict): raise ValueError('conditions_by_type must be an object')
        for kind,conditions in by_type.items():
            if kind not in ('choice','noul','score'): raise ValueError('unknown prediction type in policy')
            _validate_conditions(conditions)
        tags=data.get('tags',[])
        if not isinstance(tags,list) or not all(isinstance(t,str) for t in tags): raise ValueError('tags must be strings')
        return cls(data['name'],deepcopy(tags),deepcopy(data['conditions']),deepcopy(by_type))


def accepts(prediction,rules):
    return evaluate_conditions(prediction,rules.conditions_for(prediction.get('type','')))


def load_named_rules(path,question_names):
    from ..json_utils import load_json
    data=load_json(path)
    if not isinstance(data,dict) or set(data)!={'rules_by_question'} or not isinstance(data['rules_by_question'],dict):
        raise ValueError('rules must contain only a rules_by_question object')
    policies=data['rules_by_question']
    if set(policies)!=set(question_names):
        raise ValueError('rules_by_question keys must exactly match question names')
    return {name:RulesConfig.from_dict(policy) for name,policy in policies.items()}
