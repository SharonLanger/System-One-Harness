from concurrent.futures import ThreadPoolExecutor
import pytest
from laya_context_router.laya import budget_adapters as api
from token_budget_support import sdk, sdk_tokenizer, tokenizer

BASE={'type':'choice','instructions':'Choose the relevant function.','criteria':{'yes':'Relevant.','no':'Not relevant.'}}
CASES=[
    (BASE, 'A short state.'),
    (dict(BASE, instructions='Review this function carefully. '*100), 'A short state.'),
    (dict(BASE, criteria={'first':'Description '*80,'second':'Short.'}), 'A short state.'),
    (dict(BASE, criteria={f'candidate_{i}':'A relevant TypeScript implementation of the requested function.' for i in range(30)}), ''),
    (dict(BASE, criteria={f'candidate_{i}':'Unique function.' for i in range(300)}), ''),
    (dict(BASE, option_order=[1,0]), {'source':'export function f<T>(x:T):T{return x;}'}),
    ({'type':'score','instructions':'Rate','criteria':['bad','good'],'option_order':[1,0]}, [{'role':'user','content':'hello '*1500}]),
    ({'type':'noul','instructions':'True?', 'criteria':{False:{'desc':'no'},True:['yes']}, 'labels':{'false':' NO ','true':' YES '}}, 'prefix <mask> tail'),
]


@pytest.mark.parametrize('kind,max_len,head', [('typed',1024,256),('code',512,192)])
@pytest.mark.parametrize('question,state', CASES)
def test_independent_direct_cached_and_adapter_parity(kind,max_len,head,question,state):
    assert hasattr(api,'assemble_sequence'), 'missing qualified assembler'
    tok=tokenizer(kind); reference=sdk_tokenizer(kind)
    common,prepared,_,normalize=sdk()
    internal=normalize(question)
    assert api.normalize_question(question)==internal
    kwargs={'option_order':internal.get('option_order'),'truncate_left':isinstance(state,list)}
    expected=common.build_sequence(reference,state,internal,max_len,head,**kwargs)
    cache=prepared.PrefixCache()
    for _ in range(3):
        assert cache.build_sequence(reference,state,internal,max_len,head,**kwargs)==expected
        result=api.assemble_sequence(tok,state,question,max_len=max_len,head_max_len=head)
        assert (result['ids'],result['markers'])==expected
    with ThreadPoolExecutor(4) as pool:
        outputs=list(pool.map(lambda _:api.assemble_sequence(tok,state,question,max_len=max_len,head_max_len=head),range(12)))
    assert all((r['ids'],r['markers'])==expected for r in outputs)


def test_upstream_question_cache_scope_matches_repeated_calls():
    assert hasattr(api,'assemble_sequence'), 'missing qualified assembler'
    common,_,_,normalize=sdk(); tok=sdk_tokenizer()
    @common._reuse_question_tokens
    def repeat():
        return [common.build_sequence(tok,'hello',normalize(BASE),1024,256) for _ in range(5)]
    assert all(r==repeat()[0] for r in repeat())
