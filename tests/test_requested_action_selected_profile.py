"""Pin the adopted C1/T1/R4 profile without loading a live model."""
import json
from pathlib import Path

import pytest

from test_requested_action_block import Harness, response
from laya_context_router.block_runtime import Catalog
from laya_context_router.laya.config import RunConfig

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / 'experiments/batch_v2/experiments/requested-action-500/rounds/001-broad/suite.json'


def test_defaults_match_frozen_experiment_combination_three():
    suite = json.loads(SUITE.read_text())
    selected = next(q['definition'] for q in suite['questions'] if q['id'] == 'c1-short-choices')
    expected_question = {k: v for k, v in selected.items() if k != 'name'}
    actual = Catalog().question('requested_action')
    assert actual == expected_question
    assert list(actual['criteria']) == suite['labels']
    rule = next(r['definition'] for r in suite['rules'] if r['id'] == 'r4-gap-010')
    assert Catalog().rule('requested_action_default').conditions == rule['conditions']


def test_default_temperature_is_block_local_and_reuses_explicit_one():
    h = Harness()
    supplied = RunConfig(model='synthetic')
    h.run(config=supplied)
    h.run(config=RunConfig(model='synthetic', temperature=1.0))
    assert h.loads == [('synthetic', {'lang_temperatures': {'en': {'temperature': [1.0] * 3}}})]
    assert all(call[2] == {'lang': 'en'} for call in h.calls)
    assert supplied.temperature is None
    # Another block using the original caller config still gets the SDK default.
    h.registry.get_agent(supplied)
    assert h.loads[-1] == ('synthetic', {})


@pytest.mark.parametrize('temperature', [0, 0.5, 1.5])
def test_explicit_temperature_and_language_are_preserved(temperature):
    h = Harness()
    h.run(config=RunConfig(model='custom', temperature=temperature, lang='he'))
    assert h.loads == [('custom', {'lang_temperatures': {'he': {'temperature': [temperature] * 3}}})]
    assert h.calls[0][2] == {'lang': 'he'}


@pytest.mark.parametrize('probs,accepted', [((.4, .3, .2, .1), True), ((.4, .3001, .2, .0999), False)])
def test_selected_gap_boundary_without_confidence_gate(probs, accepted):
    raw = response(probs=probs, confidence=0)
    del raw['answers']['requested_action']['answer_confidence']
    result = Harness(raw).run()
    assert result.data == {'action': 'explain' if accepted else 'undecided'}
    assert result.decisions['requested_action']['decided'] is accepted


@pytest.mark.parametrize('probs,accepted', [((.8, .1, .05, .05), True), ((.3, .29, .21, .2), False)])
def test_unclear_is_non_actionable_and_remains_distinguishable_in_decisions(probs, accepted):
    raw = {'answers': {'requested_action': {'type': 'choice', 'choice': 'unclear',
        'probabilities': dict(zip(('unclear', 'explain', 'generate_tests', 'modify_code'), probs)),
        'answer_confidence': probs[0]}}}
    result = Harness(raw).run()
    assert result.status == 'completed'
    assert result.data == {'action': 'undecided'}
    assert result.decisions['requested_action']['answer'] == ('unclear' if accepted else 'undecided')
    assert result.decisions['requested_action']['decided'] is accepted


def test_accepted_unclear_uses_existing_flow_fallback_before_outline(monkeypatch):
    from laya_context_router.building_blocks import typescript
    from laya_context_router.building_blocks.questions.method_selection_v2 import block as selection
    from laya_context_router.flows.first_method_context import run
    from laya_context_router.hooks.contracts import Noop

    def forbidden(*args, **kwargs):
        pytest.fail('unclear must stop before source outline or method selection')

    monkeypatch.setattr(typescript, 'outline', forbidden)
    monkeypatch.setattr(selection, 'run', forbidden)
    h = Harness(response('unclear'))
    result = run('Do something with `src/billing/invoice-service.ts`.',
                 project_root=ROOT / 'tests/fixtures/first_flow_project',
                 config=RunConfig(model='synthetic'), registry=h.registry,
                 logger=lambda *args, **kwargs: None)
    assert result == Noop('undecided')
    assert len(h.calls) == 1
