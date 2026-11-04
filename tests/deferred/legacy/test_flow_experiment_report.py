import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

from copy import deepcopy
import importlib
import json
import pytest
from block_runtime import Block, Catalog, PreparedInput
from building_blocks.questions.method_selection_v2.block import run as select
from building_blocks.typescript import outline, extract_callable
from flows import first_method_context as flow
from laya.config import RunConfig
from laya.registry import AgentRegistry
from test_method_selection import questions_for, raw_for

A = RunConfig("mock-A", 0.2, "fr")

@pytest.mark.parametrize('invalid_rule', [False, True])
def test_G13_existing_offline_experiment_preserves_summary_and_rule_error(tmp_path, monkeypatch, invalid_rule):
    from pathlib import Path
    from test_v2_blocks import source
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'experiments'))
    experiment = importlib.import_module('block_method_selection')
    data = source(); questions = questions_for(data)
    payload = tmp_path / 'input.json'
    payload.write_text(json.dumps({'text':'Explain sum','source_outline':data,'config':{'model':A.model}}))
    class Agent:
        def predict(self, text, submitted, **kwargs):
            assert text == 'Explain sum' and submitted == questions
            return raw_for(questions, 'sum@1:1')
    loads = []
    def loader(*args, **kwargs):
        loads.append(args)
        return Agent()
    if invalid_rule:
        # The legacy experiment has no CLI rule flag. Inject the new public call
        # at its existing block boundary to exercise its unchanged error report.
        def invalid(text, source_outline, **kwargs):
            return select({'text':text,'source_outline':source_outline},
                          rule_overrides={'method':'missing_policy'}, **kwargs)
        monkeypatch.setattr(experiment,'run_block',invalid)
    output = tmp_path / 'reports'
    code = experiment.run(input_path=payload,loader=loader,output_root=output,printer=lambda _:None)
    details_path, = output.rglob('details.json')
    details = json.loads(details_path.read_text())
    summary = (details_path.parent / 'summary.md').read_text()
    assert code == int(invalid_rule)
    if invalid_rule:
        assert details['run']['status'] == 'failed' and details['error']['stage'] == 'block'
        assert 'missing_policy' in details['error']['message'] and 'missing_policy' in summary
        assert not loads and details['result'] is None
    else:
        assert details['run']['status'] == 'success' and details['error'] is None
        assert details['result']['selected_id'] == data['callables'][0]['id']
        assert details['result']['decisions']['method']['answer'] == 'sum@1:1'
        assert 'Outcome: **selected**' in summary and 'Selected candidate: **sum**' in summary
        assert data['source_hash'] in summary and len(loads) == 1
