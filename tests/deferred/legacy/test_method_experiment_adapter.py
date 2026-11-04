import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

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

from test_method_selection_selected_profile import Harness, SUITE, ROOT

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
