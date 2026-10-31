"""Explicit synthetic provider for examples/tests, never application configuration.

These controlled reports test transport, copying and decision logic. They are not
real-tokenizer qualification; the separate pinned SDK suite provides that evidence.
This file is outside the installed laya_context_router package.
"""
from types import SimpleNamespace
import inspect
from laya_context_router.laya.budget import make_report


def plumbing_provider(agent, config):
    """Opt-in controlled capability; no SDK import, tokenization or inference."""
    def inspect_request(state, questions, *, request_id=None):
        report = make_report(config.model, request_id=request_id)
        report.update(inspection_status='complete',
                      tokenizer={'evidence':'controlled_plumbing_only'},
                      limits={'provenance':'controlled_plumbing_only'},
                      questions=[{'question_id': name, 'evidence':'controlled_plumbing_only'} for name in questions],
                      message='Synthetic transport fixture; token fit is not measured')
        return report
    return SimpleNamespace(inspect=inspect_request)


PLUMBING_SOURCE = ('from types import SimpleNamespace\n'
                   'from laya_context_router.laya.budget import make_report\n'
                   + inspect.getsource(plumbing_provider))
# Used only in isolated fake-SDK subprocesses that intentionally replace the
# application boundary. Production code never reads this fixture or a bypass flag.
INSTALL_TEST_PROVIDER_SOURCE = (PLUMBING_SOURCE + '\n'
    'import laya_context_router.laya.budget_profiles as _test_profiles\n'
    '_test_profiles.verified_provider = plumbing_provider\n')
