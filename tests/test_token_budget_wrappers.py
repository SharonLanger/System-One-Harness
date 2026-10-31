"""Wrapper capability forwarding; controlled fixtures are not tokenizer evidence."""
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))
from support import ObservingRegistry
from block_method_selection import CapturingRegistry

@pytest.mark.parametrize('wrapper', [lambda r: ObservingRegistry(r), lambda r: CapturingRegistry(r,{})])
def test_observation_wrapper_preserves_actual_inspector(wrapper):
    token=object(); config=object(); seen=[]
    original=SimpleNamespace(get_inspector=lambda c:(seen.append(c),token)[1])
    wrapped=wrapper(original)
    assert hasattr(wrapped,'get_inspector'), 'missing inspection forwarding'
    assert wrapped.get_inspector(config) is token
    assert seen == [config]

def test_live_check_accepts_explicit_inspection_provider():
    import inspect
    from laya_context_router.live_check import run_check
    assert 'inspection_provider' in inspect.signature(run_check).parameters
