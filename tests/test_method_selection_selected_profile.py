"""Freeze the adopted Q0 / T0.5 / r9 profile using synthetic model output."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from block_runtime import Catalog
from building_blocks.questions.method_selection_v2 import block
from laya.config import RunConfig
from laya.registry import AgentRegistry
from test_method_selection import questions_for, raw_for
from test_v2_blocks import source

ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / 'experiments/batch_v2/experiments/method-selection-200/rounds/001-small/suite.json').read_text())


class Harness:
    def __init__(self, raw=None):
        self.loads, self.calls = [], []
        self.raw = raw if raw is not None else raw_for(questions_for(source()), 'sum@1:1')
        owner = self
        class Fake:
            def predict(self, text, questions, **kwargs):
                owner.calls.append((text, deepcopy(questions), kwargs))
                return deepcopy(owner.raw)
        def loader(model, **kwargs):
            self.loads.append((model, kwargs))
            return Fake()
        self.registry = AgentRegistry(loader=loader)

    def run(self, config=None, **kwargs):
        return block.run({'text': 'Explain sum', 'source_outline': source()},
                         config=config or RunConfig(model='synthetic'), registry=self.registry, **kwargs)


def test_exact_selected_question_rule_and_fixed_guard():
    catalog = Catalog()
    question = SUITE['questions'][0]['definition']
    assert catalog.question('method_selection_v2') == {k:v for k,v in question.items() if k != 'name'}
    selected = next(r['definition'] for r in SUITE['rules'] if r['id'] == 'r9-combined-strict')
    assert catalog.rule('method_selection_v2_default').conditions == selected['conditions']
    fixed = SUITE['fixed_questions']['multiple_relevant']
    assert catalog.question('multiple_relevant') == {k:v for k,v in fixed.items() if k != 'name'}
    assert catalog.rule('multiple_methods_default').conditions == SUITE['fixed_rules']['multiple_relevant']['conditions']
    # The SDK sees Q0 with dynamic signatures and the exact fixed auxiliary question.
    h = Harness(); h.run()
    assert h.calls[0][1] == questions_for(source())
    assert catalog.rule('method_selection_default').conditions != selected['conditions']


def test_default_temperature_and_caller_config_are_block_local():
    h = Harness(); supplied = RunConfig(model='synthetic')
    h.run(config=supplied)
    h.run(config=RunConfig(model='synthetic', temperature=.5))
    assert h.loads == [('synthetic', {'lang_temperatures': {'en': {'temperature': [.5] * 3}}})]
    assert h.calls[0][2] == {'lang':'en'}
    assert supplied.temperature is None
    h.registry.get_agent(supplied)
    assert h.loads[-1] == ('synthetic', {})


@pytest.mark.parametrize('confidence,probs,accepted', [
    (.7, (.5,.25,.25), True), (.6999, (.5,.25,.25), False),
    (.7, (.4999,.2501,.25), False), (.7001, (.5001,.25,.2499), True)])
def test_strict_threshold_boundaries(confidence, probs, accepted):
    raw = raw_for(questions_for(source()), 'sum@1:1', confidence=confidence)
    raw['answers']['method']['probabilities'] = dict(zip(questions_for(source())['method']['criteria'], probs))
    result = Harness(raw).run()
    assert result.decisions['method']['decided'] is accepted
    assert result.data['selected_id'] == (source()['callables'][0]['id'] if accepted else None)


@pytest.mark.parametrize('multiple,confidence,reason', [(.9,.95,'multiple_relevant'), (.1,.4999,'multiple_undecided'), (.1,.5,None)])
def test_fixed_multiple_guard_is_retained(multiple, confidence, reason):
    raw = raw_for(questions_for(source()), 'sum@1:1', multiple=multiple)
    raw['answers']['multiple_relevant']['answer_confidence'] = confidence
    result = Harness(raw).run()
    assert result.data['reason'] == reason
    assert (result.data['selected_id'] is not None) == (reason is None)


def test_explicit_question_rule_and_temperature_overrides():
    raw = raw_for(questions_for(source()), 'sum@1:1', confidence=.6)
    h = Harness(raw)
    question = deepcopy(SUITE['questions'][1]['definition'])
    result = h.run(config=RunConfig(model='custom', temperature=0, lang='he'),
                   question_overrides={'method':question}, rule_overrides={'method':'method_selection_default'})
    assert result.data['selected_id'] is not None
    assert h.calls[0][1]['method']['instructions'] == question['instructions']
    assert h.loads == [('custom', {'lang_temperatures': {'he': {'temperature': [0] * 3}}})]
    assert h.calls[0][2] == {'lang':'he'}


@pytest.mark.parametrize('temperature', [0, .8, 1.1])
def test_experiment_adapter_preserves_configuration_and_overrides(temperature):
    spec = importlib.util.spec_from_file_location('selected_method_adapter', ROOT / 'experiments/batch_v2/method_adapter.py')
    adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
    h = Harness(raw_for(questions_for(source()), 'sum@1:1', confidence=.6))
    result = adapter.execute({'text':'Explain sum','source_outline':source()},
        SUITE['questions'][1], SUITE['rules'][0], SUITE,
        RunConfig(model='experiment',temperature=temperature), h.registry)
    expected = {} if temperature is None else {'lang_temperatures': {'en': {'temperature': [temperature] * 3}}}
    assert h.loads == [('experiment',expected)]
    assert h.calls[0][1]['method']['instructions'] == SUITE['questions'][1]['definition']['instructions']
    assert result.data['selected_id'] is not None
