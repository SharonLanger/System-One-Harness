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


def sdk():
    """Load unmodified pinned host helpers without the neural runtime package."""
    import ast
    import importlib.util
    import sys
    import types
    from typing import Dict
    package_name = '_budget_qualification_sdk'
    if package_name + '.common' in sys.modules:
        return sys.modules[package_name + '.common'], sys.modules[package_name + '.prepared'], sys.modules[package_name + '.tokenizer'], sys.modules[package_name].normalize
    package = types.ModuleType(package_name)
    package.__path__ = [str(FIXTURES / 'sdk')]
    sys.modules[package_name] = package
    modules = []
    for name in ('common', 'prepared', 'tokenizer'):
        spec = importlib.util.spec_from_file_location(package_name + '.' + name, FIXTURES / 'sdk' / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    tree = ast.parse((FIXTURES / 'sdk/runtime.py').read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_to_internal')
    fn.decorator_list = []
    namespace = {'json': json, 'Dict': Dict}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), '<pinned SDK normalizer>', 'exec'), namespace)
    package.normalize = namespace['_to_internal']
    return *modules, package.normalize


def sdk_tokenizer(kind='typed'):
    # SDK requires co-located files. Prepare a temporary directory without copying
    # the large vocabulary: the pinned wrapper reads this verified symlink.
    import tempfile
    _, _, module, _ = sdk()
    vocab, config = fixture_paths(kind)
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        (folder / 'tokenizer.json').symlink_to(vocab)
        (folder / 'tokenizer_config.json').symlink_to(config)
        return module.Tokenizer(folder)
