"""Scripted SDK boundary for offline harness scenarios."""
from copy import deepcopy

from laya.registry import AgentRegistry


class ScriptedLaya:
    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls = []
        self.loads = []

    def registry(self):
        return AgentRegistry(loader=self.load)

    def load(self, model, **options):
        self.loads.append((model, deepcopy(options)))
        return self

    def predict(self, text, questions, **options):
        self.calls.append((text, deepcopy(questions), deepcopy(options)))
        if not self.steps:
            raise AssertionError('Unexpected Laya prediction')
        step = self.steps.pop(0)
        result = step(text, questions) if callable(step) else step
        if isinstance(result, BaseException):
            raise result
        return deepcopy(result)

    def assert_complete(self):
        assert not self.steps, f'{len(self.steps)} Laya responses were unused'


def choice_response(name, selected, criteria):
    keys = list(criteria)
    assert selected in criteria and len(keys) > 1
    return {name: {'type': 'choice', 'choice': selected,
                   'probabilities': {key: 0.9 if key == selected else 0.1 / (len(keys) - 1)
                                     for key in keys}, 'answer_confidence': 0.95}}


def action_answer(text, questions):
    assert set(questions) == {'requested_action'}
    assert 'Explain' in text
    return {'answers': choice_response('requested_action', 'explain',
                                       questions['requested_action']['criteria'])}


def method_answer(text, questions):
    assert set(questions) == {'method', 'multiple_relevant'}
    assert 'calculateTotal' in text
    selected = next(key for key in questions['method']['criteria'] if key != 'none_or_unclear')
    return {'answers': {**choice_response('method', selected, questions['method']['criteria']),
                        'multiple_relevant': {'type': 'noul', 'noul': 0.1,
                                              'answer_confidence': 0.95}}}
