"""Offline source-to-context example. Only Laya SDK calls are controlled mocks."""
from copy import deepcopy
import json
from pathlib import Path

from laya_context_router.building_blocks.typescript import outline
from laya_context_router.flows.file_method_context import run
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry

root = Path(__file__).resolve().parents[1]
source = root / 'tests/fixtures/typescript/basic.ts'
# Explicit fixture candidate and raw response; no inference from the prompt.
source_outline = outline(source)
chosen = source_outline['callables'][0]['id']
ids = [c['id'] for c in source_outline['callables']] + ['none_or_unclear']
raw = {'answers': {
    'method': {'type': 'choice', 'choice': chosen, 'answer_confidence': 0.95,
               'probabilities': {key: 0.9 if key == chosen else 0.1 / (len(ids)-1) for key in ids}},
    'multiple_relevant': {'type': 'noul', 'noul': 0.1, 'answer_confidence': 0.95}}}


class MockAgent:
    def predict(self, text, questions):
        assert text == 'Explain `tests/fixtures/typescript/basic.ts`: how does greet work?'
        assert list(questions['method']['criteria']) == ids
        return deepcopy(raw)


result = run('Explain `tests/fixtures/typescript/basic.ts`: how does greet work?',
             cwd=root, repository_root=root, config=RunConfig(),
             registry=AgentRegistry(loader=lambda model: MockAgent()))
print(json.dumps(result, ensure_ascii=False, indent=2))
