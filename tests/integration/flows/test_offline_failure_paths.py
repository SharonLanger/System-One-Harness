"""Real flow/block error handling with only external Laya responses scripted."""
import pytest
from flows.first_method_context import run
from hooks.contracts import Failure, Noop
from laya.config import RunConfig
from tests.support.fake_laya import ScriptedLaya
from tests.support.offline_scenarios import PROMPT, SOURCE, scenario_steps
from tests.support.recording_logger import RecordingLogger


@pytest.mark.parametrize('scenario,outcome', [
    ('unsupported', Noop), ('ambiguous', Noop), ('invalid', Failure),
    ('failure', Failure), ('missing', Noop), ('empty', Noop),
    ('no_candidates', Noop), ('source_removed', Failure), ('budget', Noop),
])
def test_real_flow_failure_paths(tmp_path, scenario, outcome):
    source = tmp_path / 'sample.ts'
    source.write_text('export const value = 1;\n' if scenario == 'no_candidates' else SOURCE)
    prompt = '' if scenario == 'empty' else PROMPT.replace('sample.ts', 'missing.ts') if scenario == 'missing' else PROMPT
    fake = ScriptedLaya(*scenario_steps(scenario, source))
    logger = RecordingLogger()
    with logger.capture_shared():
        result = run(prompt, project_root=tmp_path, config=RunConfig(model='offline-scripted'),
                     registry=fake.registry(), logger=logger,
                     max_context_chars=1 if scenario == 'budget' else 8000)
    assert isinstance(result, outcome), result
    if isinstance(result, Noop):
        assert result.reason == {'unsupported': 'modify_code', 'ambiguous': 'no_single_match',
            'missing': 'missing', 'empty': 'ineligible_request', 'no_candidates': 'no_candidates',
            'budget': 'output_budget_exceeded'}[scenario]
    else:
        assert result.stage == ('extraction' if scenario == 'source_removed' else 'requested_action')
    fake.assert_complete()
    assert not [r for r in logger.records if r['event'] == 'enrichment_prepared']
