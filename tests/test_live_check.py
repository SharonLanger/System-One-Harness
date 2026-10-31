"""Readiness checks inject an SDK boundary; no real Laya import occurs."""
from examples._plumbing_inspection import plumbing_provider
import json
import sys
from copy import deepcopy

import pytest

from laya_context_router.laya.config import RunConfig
from laya_context_router.live_check import run_check, main


class Agent:
    model_id = 'observed-checkpoint'
    temperature = 0.25

    def predict(self, text, questions, **kwargs):
        answers = {}
        for name, q in questions.items():
            if q['type'] == 'choice':
                keys = list(q['criteria'])
                answers[name] = {'type': 'choice', 'choice': keys[0],
                                 'probabilities': {k: float(i == 0) for i, k in enumerate(keys)}}
            elif q['type'] == 'noul':
                answers[name] = {'type': 'noul', 'noul': 0.1}
            else:
                answers[name] = {'type': 'score', 'score': 0.6,
                                 'legend': {str(i): v for i, v in enumerate(q['criteria'])},
                                 'probabilities': {'0': 0.4, '1': 0.6}}
        for answer in answers.values():
            answer['answer_confidence'] = 0.9
        return {'answers': answers}


def test_default_call_and_real_source_flow_without_sdk_import():
    loaded = []
    def loader(model, **kwargs):
        loaded.append((model, kwargs))
        return Agent()
    before = sys.modules.get('laya_mlx')
    report = run_check(inspection_provider=plumbing_provider, loader=loader)
    assert sys.modules.get('laya_mlx') is before
    assert report['scope'] == 'single_checkpoint_readiness'
    assert report['phase20'] == 'pending_real_matrix_and_independent_verification'
    assert len(loaded) == 2  # a fresh invocation owns its own object
    call = report['calls'][0]
    assert set(call['raw']['answers']) == {'fruit', 'mentioned', 'size'}
    assert call['decisions']['fruit']['answer'] == 'apple'
    assert call['decisions']['size']['answer'] == 'large'
    assert call['rejected']['fruit']['decided'] is False
    assert call['enriched']['answers']['mentioned']['distance_from_boundary'] == 0.4
    assert call['observed']['attributes']['model_id'] == 'observed-checkpoint'
    assert call['requested']['model'] != call['observed']['attributes']['model_id']
    assert report['flow']['status'] == 'context'
    assert report['flow']['context']['code'] == 'export function double(value: number) { return value * 2; }'
    json.dumps(report, allow_nan=False)


def test_matrix_reuses_original_after_intervening_settings():
    loads = []
    def loader(model, **kwargs):
        loads.append((model, deepcopy(kwargs)))
        return Agent()
    report = run_check(inspection_provider=plumbing_provider, loader=loader, second_model='user/supplied', temperatures=[0.2, 0.3])
    assert len(loads) == 7  # six configurations plus fresh registry
    assert all(report['reuse'].values())
    assert len(report['calls']) == 9  # A/B/A, A/T1/T2/T1, B/T1/T2, fresh A


def test_invalid_raw_is_retained_for_diagnosis():
    class Bad(Agent):
        def predict(self, *args, **kwargs):
            return {'answers': {}}
    report = run_check(inspection_provider=plumbing_provider, loader=lambda *a, **k: Bad())
    assert report['status'] == 'failed'
    assert report['calls'][0]['raw'] == {'answers': {}}
    assert 'invalid answer type' in report['error']


@pytest.mark.parametrize('kwargs', [dict(second_model=RunConfig().model), dict(temperatures=[0.1]), dict(temperatures=[0.1, 0.1])])
def test_invalid_matrix_fails_before_loading(kwargs):
    with pytest.raises(ValueError):
        run_check(inspection_provider=plumbing_provider, loader=lambda *a, **k: pytest.fail('loaded'), **kwargs)


def test_cli_requires_explicit_real_and_supported_environment(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr('laya_context_router.live_check.platform.system', lambda: 'Linux')
    monkeypatch.setattr('laya_context_router.live_check.verified_provider', plumbing_provider)
    monkeypatch.setattr('laya_context_router.live_check.real_loader', lambda *a, **k: pytest.fail('real loader touched'))
    assert main(['--output', str(tmp_path / 'report.json')]) == 2
    assert not (tmp_path / 'report.json').exists()
    assert main(['--real', '--output', str(tmp_path / 'report.json')]) == 2
    assert 'BLOCKED' in capsys.readouterr().err


def test_policy_rejected_selection_is_valid_noop():
    class Uncertain(Agent):
        def predict(self, text, questions, **kwargs):
            raw = super().predict(text, questions, **kwargs)
            for answer in raw['answers'].values():
                answer['answer_confidence'] = 0.1
            return raw
    report = run_check(inspection_provider=plumbing_provider, loader=lambda *a, **k: Uncertain())
    assert report['status'] == 'passed_preparation_probe'
    assert report['flow'] == {'status': 'noop', 'reason': 'method_undecided', 'context': None}


def test_helper_error_is_failed_probe(monkeypatch):
    monkeypatch.setattr('laya_context_router.live_check.run_flow', lambda *a, **k: {'status': 'noop', 'reason': 'extractor_error', 'context': None})
    report = run_check(inspection_provider=plumbing_provider, loader=lambda *a, **k: Agent())
    assert report['status'] == 'failed'
    assert 'extractor_error' in report['error']


def test_cli_opt_in_writes_new_evidence_without_real_import(tmp_path, monkeypatch):
    monkeypatch.setattr('laya_context_router.live_check.platform.system', lambda: 'Darwin')
    monkeypatch.setattr('laya_context_router.live_check.platform.machine', lambda: 'arm64')
    monkeypatch.setattr('laya_context_router.live_check.verified_provider', plumbing_provider)
    monkeypatch.setattr('laya_context_router.live_check.real_loader', lambda *a, **k: Agent())
    path = tmp_path / 'result.json'
    assert main(['--real', '--output', str(path)]) == 0
    assert json.loads(path.read_text())['status'] == 'passed_preparation_probe'
    previous = path.read_bytes()
    assert main(['--real', '--output', str(path)]) == 2
    assert path.read_bytes() == previous


def test_non_json_raw_fails_with_serializable_bounded_diagnostic():
    class Bad(Agent):
        def predict(self, *a, **k):
            return {'answers': {}, 'invalid': {1, 2}}
    report = run_check(inspection_provider=plumbing_provider, loader=lambda *a, **k: Bad())
    assert report['status'] == 'failed'
    assert 'raw' not in report['calls'][0]
    assert 'Non-JSON response' in report['calls'][0]['raw_capture_limitation']
    json.dumps(report, allow_nan=False)


def test_processing_checks_are_explicit_runtime_failures():
    from laya_context_router.live_check import check_processing
    raw = Agent().predict('', {'mentioned': {'type': 'noul'}})
    with pytest.raises(ValueError, match='independently computed'):
        check_processing(raw, {'answers': {'mentioned': {'distance_from_boundary': 9}}}, {}, {})
