"""Offline qualification fixtures; fail closed when explicitly prepared assets are absent."""
from pathlib import Path
import hashlib
import json

FIXTURES = Path(__file__).parent / 'fixtures/token-budget'
ROOT = Path(__file__).resolve().parents[1]


def fixture_paths(kind='typed'):
    manifest = json.loads((FIXTURES / 'manifest.json').read_text())
    vocab = ROOT / '.token-budget-fixtures/tokenizer.json'
    assert vocab.is_file(), 'Run python scripts/prepare_token_budget_fixtures.py --download explicitly before tests'
    assert hashlib.sha256(vocab.read_bytes()).hexdigest() == manifest['tokenizer']['sha256']
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == digest, name
    return vocab, FIXTURES / kind / 'tokenizer_config.json'


def tokenizer(kind='typed'):
    from laya_context_router.laya.budget_adapters import ExactTokenizer
    return ExactTokenizer(*fixture_paths(kind))
