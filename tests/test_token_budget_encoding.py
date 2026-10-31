import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from tokenizers import Tokenizer
from token_budget_support import fixture_paths

CORPUS = [
    '', 'hello', ' hello', '  hello\n\tworld',
    'Explain how this function works.',
    'export async function fetchUser(id: string): Promise<User | null> {\n return await api.get(`/users/${id}`);\n}',
    '// generic TypeScript comment\nconst x: Record<string, number[]> = {};',
    'x?.foo?.bar ?? null; function λ<T>(t: T): T { return t; }',
    '[MASK] <mask> [CLS] [SEP]', 'foo_bar XMLHttpRequest HTTPResponse200 😀',
]


def capability():
    assert importlib.util.find_spec('laya_context_router.laya.budget_adapters') is not None, 'missing exact encoding capability'
    from laya_context_router.laya import budget_adapters
    return budget_adapters


@pytest.mark.parametrize('kind', ['typed', 'code'])
@pytest.mark.parametrize('text', CORPUS)
def test_exact_unrestricted_ids(kind, text):
    api = capability()
    vocab, config = fixture_paths(kind)
    tok = api.ExactTokenizer(vocab, config)
    expected = Tokenizer.from_file(str(vocab))
    expected.no_padding(); expected.no_truncation()
    assert tok.encode(text) == expected.encode(text, add_special_tokens=False).ids
    with ThreadPoolExecutor(4) as pool:
        assert all(v == tok.encode(text) for v in pool.map(tok.encode, [text] * 12))


@pytest.mark.parametrize('state', ['literal <mask>', {'code': 'const x = 1;', 'ü': [True, None]}, [{'role': 'user', 'content': 'hello'}]])
def test_state_normalization(state):
    api = capability()
    tok = api.ExactTokenizer(*fixture_paths())
    expected = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
    assert api.encode_state(tok, state) == tok.encode(expected.replace(tok.mask_token, ' '))


def test_component_rendering_and_mask_sanitization():
    api = capability(); tok = api.ExactTokenizer(*fixture_paths())
    q = {'type': 'choice', 'instructions': 'Pick '+tok.mask_token+' now', 'criteria': {'a': 'A', 'b': 'B'}, 'option_order': [1, 0]}
    parts = api.encode_question(tok, q)
    assert parts['instruction_ids'] == tok.encode('choice question: Pick   now')
    assert parts['option_keys'] == ['b', 'a']
    assert parts['option_ids'] == [tok.encode(' b: B'), tok.encode(' a: A')]
    score = api.encode_question(tok, {'type':'score','instructions':'Rate','criteria':['bad','good']})
    assert score['option_ids'] == [tok.encode(' level 0: bad'),tok.encode(' level 1: good')]
    noul = api.encode_question(tok, {'type':'noul','instructions':'True?', 'criteria': {False:{'desc':'no'},True:['yes']}, 'labels': {'false':' NO ', 'true':' YES '}})
    assert noul['option_ids'] == [tok.encode(' NO: {"desc": "no"}'),tok.encode(' YES: ["yes"]')]


def test_two_configurations_and_validation():
    api=capability()
    a=api.ExactTokenizer(*fixture_paths('typed'));b=api.ExactTokenizer(*fixture_paths('code'))
    assert a.fingerprints['tokenizer_sha256']==b.fingerprints['tokenizer_sha256']
    assert a.fingerprints['config_sha256']!=b.fingerprints['config_sha256']
    q={'type':'choice','instructions':'Pick','criteria':{'a':'A','b':'B'}}
    for order in ([0,0],[True,1],[2,0]):
        with pytest.raises(ValueError): api.encode_question(a,dict(q,option_order=order))
    with pytest.raises(ValueError): api.encode_question(a,dict(q,labels={'false':'no','true':'yes'}))
