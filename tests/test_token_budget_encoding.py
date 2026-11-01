"""Rendering and normalization against a mocked encoding boundary, not real token IDs."""
import json
import pytest
from laya_context_router.laya import budget_adapters as api
from token_budget_support import tokenizer

@pytest.mark.parametrize('state',['','hello','  hello\n\tworld','literal <mask>',
    'export async function fetchUser(id: string): Promise<User | null> { return api.get(id); }',
    'x?.foo?.bar ?? null; function λ<T>(t: T): T { return t; }',
    {'code':'const x = 1;','ü':[True,None]},[{'role':'user','content':'hello'}]])
def test_state_normalization_delegates_exact_rendered_text(state):
    expected=(state if isinstance(state,str) else json.dumps(state,ensure_ascii=False)).replace('<mask>',' ')
    tok=tokenizer(overrides={expected:[101,102]})
    assert api.encode_state(tok,state)==[101,102]
    assert tok.calls==[expected]


def test_component_rendering_order_and_mask_sanitization():
    expected=['choice question: Pick   now',' b: B',' a: A']
    tok=tokenizer(overrides={value:[100+i] for i,value in enumerate(expected)})
    parts=api.encode_question(tok,{'type':'choice','instructions':'Pick <mask> now','criteria':{'a':'A','b':'B'},'option_order':[1,0]})
    assert tok.calls==expected
    assert parts['instruction_ids']==[100] and parts['option_ids']==[[101],[102]]
    assert parts['option_keys']==['b','a'] and parts['option_indices']==[1,0]


def test_structured_score_and_boolean_rendering():
    tok=tokenizer()
    api.encode_question(tok,{'type':'score','instructions':'Rate','criteria':['bad','good']})
    assert tok.calls==['score question: Rate',' level 0: bad',' level 1: good']
    tok.calls.clear()
    api.encode_question(tok,{'type':'noul','instructions':['True?'],'criteria':{False:{'desc':'no'},True:['yes']},'labels':{'false':' NO ','true':' YES '}})
    assert tok.calls==['noul question: ["True?"]',' NO: {"desc": "no"}',' YES: ["yes"]']


def test_invalid_order_and_labels_keep_validation():
    q={'type':'choice','instructions':'Pick','criteria':{'a':'A','b':'B'}}
    for order in ([0,0],[True,1],[2,0]):
        with pytest.raises(ValueError):api.encode_question(tokenizer(),dict(q,option_order=order))
    with pytest.raises(ValueError):api.encode_question(tokenizer(),dict(q,labels={'false':'no','true':'yes'}))
