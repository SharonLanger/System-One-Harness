"""Real prompt flow and blocks with a scripted SDK boundary."""
import pytest

from flows.first_method_context import run
from hooks.contracts import Context, Noop
from laya.config import RunConfig
from tests.support.fake_laya import ScriptedLaya, action_answer, method_answer, choice_response
from tests.support.recording_logger import RecordingLogger


@pytest.mark.parametrize('second,expected', [
    (method_answer, Context),
    (lambda text, questions: {'answers': {
        **choice_response('method', 'none_or_unclear', questions['method']['criteria']),
        'multiple_relevant': {'type': 'noul', 'noul': 0.1, 'answer_confidence': 0.95}}}, Noop),
])
def test_real_flow_blocks_and_extractor_with_fake_laya(tmp_path, monkeypatch, second, expected):
    import log_utils
    log_path = tmp_path / 'should-not-be-written.jsonl'
    monkeypatch.setattr(log_utils, 'LOG_PATH', log_path)
    source = tmp_path / 'sample.ts'
    source.write_text('export function calculateTotal(value: number) { return value + 1; }\n')
    fake = ScriptedLaya(action_answer, second)
    logger = RecordingLogger()
    with logger.capture_shared():
        result = run('Explain `sample.ts`: calculateTotal', project_root=tmp_path,
                     config=RunConfig(model='offline-scripted'), registry=fake.registry(), logger=logger)
    assert isinstance(result, expected)
    if isinstance(result, Context):
        assert 'calculateTotal' in result.text and 'value + 1' in result.text
    else:
        assert result.reason == 'no_single_match'
    assert len(fake.calls) == 2
    fake.assert_complete()
    assert not log_path.exists()
