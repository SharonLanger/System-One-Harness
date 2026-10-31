import importlib.util
import json


def test_report_contract():
    assert importlib.util.find_spec('laya_context_router.laya.budget') is not None, 'missing report capability'
    from laya_context_router.laya.budget import InputBudgetError, InputTokenBudgetExceeded, InspectionUnavailable, InspectionFailed, make_report
    report = make_report('model', request_id='r1')
    assert report['questions'] is None and report['limits'] is None
    assert report['request_inference_started'] is False
    for cls, code in [(InputTokenBudgetExceeded, 'INPUT_TOKEN_BUDGET_EXCEEDED'), (InspectionUnavailable, 'TOKEN_BUDGET_INSPECTION_UNAVAILABLE'), (InspectionFailed, 'TOKEN_BUDGET_INSPECTION_FAILED')]:
        error = cls(report, 'first actionable boundary')
        assert isinstance(error, InputBudgetError)
        assert error.report['code'] == code
        assert 'r1' in str(error) and 'first actionable boundary' in str(error)
        assert json.loads(json.dumps(error.report, allow_nan=False)) == error.report
        copy = error.report
        copy['model']['requested_id'] = 'changed'
        report['hint'] = 'changed'
        assert error.report['model']['requested_id'] == 'model'
        assert error.report['hint'] != 'changed'
        report['hint'] = 'guidance'


def test_report_refuses_non_json_values():
    assert importlib.util.find_spec('laya_context_router.laya.budget') is not None, 'missing report capability'
    from laya_context_router.laya.budget import InspectionFailed, make_report
    import pytest
    for value in (float('nan'), object()):
        report = make_report('model')
        report['bad'] = value
        with pytest.raises((ValueError, TypeError)):
            InspectionFailed(report, 'bad report')
