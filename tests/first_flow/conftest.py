"""Offline flow harness: fixed public block answers, real source utilities."""
from copy import deepcopy
from pathlib import Path
import shutil
from types import SimpleNamespace
import pytest

from block_runtime import BlockResult
from building_blocks import typescript as ts
from building_blocks.questions.requested_action import block as action
from building_blocks.questions.method_selection_v2 import block as selection
from flows import first_method_context as flow
from hooks.dispatcher import ingest_common
from hooks.user_prompt_submit.dispatcher import PromptRequest
from laya.config import RunConfig

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures'
SELECTED = 'src/billing/invoice-service.ts'
METHOD = 'calculateInvoiceTotalWithAdjustment'
PROMPT = f'Explain `{SELECTED}`: {METHOD}'


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    import log_utils
    from laya import predict, registry
    def forbidden(*args, **kwargs):
        raise AssertionError('real model/tokenizer boundary must not run')
    monkeypatch.setattr(log_utils, 'LOG_PATH', tmp_path / 'debug.jsonl')
    monkeypatch.setattr(predict, 'real_loader', forbidden)
    monkeypatch.setattr(predict, 'predict', forbidden)
    monkeypatch.setattr(registry, 'real_loader', forbidden)
    monkeypatch.setattr(registry.AgentRegistry, 'get_agent', forbidden)


class Harness:
    def __init__(self, root, monkeypatch):
        self.root = root
        self.path = root / SELECTED
        self.calls, self.logs = [], []
        self.config = RunConfig(model='offline-fixed-blocks')
        self.registry = object()
        self.action_result = BlockResult('completed', None, {}, {'action': 'explain'})
        self.choose(METHOD)
        monkeypatch.setattr(action, 'run', self.action)
        monkeypatch.setattr(selection, 'run', self.selection)

    def choose(self, name, *, path=None, index=0):
        self.path = path or self.path
        self.outline = ts.outline(self.path)
        self.candidate = [c for c in self.outline['callables'] if c['name'] == name][index]
        self.selection_result = BlockResult('completed', None, {}, {
            'selected_id': self.candidate['id'], 'reason': None,
            'candidate_map': {c['id']: {**deepcopy(c), 'path': self.outline['path'],
                                     'source_hash': self.outline['source_hash']}
                              for c in self.outline['callables']},
            'label_map': {f'fixed-{i}': c['id'] for i, c in enumerate(self.outline['callables'])}})

    def action(self, data, **kwargs):
        self.calls.append(('action', deepcopy(data), kwargs))
        if isinstance(self.action_result, Exception):
            raise self.action_result
        return self.action_result

    def selection(self, data, **kwargs):
        self.calls.append(('selection', deepcopy(data), kwargs))
        if isinstance(self.selection_result, Exception):
            raise self.selection_result
        return self.selection_result

    def logger(self, level, event, **details):
        self.logs.append((level, event, deepcopy(details)))

    def run(self, prompt=PROMPT, **kwargs):
        return flow.run(prompt, project_root=kwargs.pop('project_root', self.root),
                        config=self.config, registry=self.registry,
                        logger=kwargs.pop('logger', self.logger), **kwargs)

    def request(self, prompt=PROMPT, **kwargs):
        args = SimpleNamespace(repository_root=str(self.root), real=True, config=None,
                               max_context_chars=8000)
        for key, value in kwargs.items():
            setattr(args, key, value)
        event = {'hook_event_name': 'UserPromptSubmit', 'session_id': 'offline-session',
                 'cwd': str(self.root), 'transcript_path': 'unused.jsonl', 'prompt': prompt}
        return PromptRequest(prompt, ingest_common(event, 'offline-invocation'), args)

    def prepared(self):
        return [d for _, event, d in self.logs if event == 'enrichment_prepared']


@pytest.fixture
def h(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    shutil.copytree(FIXTURES / 'first_flow_project', root)
    return Harness(root, monkeypatch)


@pytest.fixture
def golden():
    return (FIXTURES / 'first_flow_expected' / 'invoice-context.txt').read_text().removesuffix('\n')
