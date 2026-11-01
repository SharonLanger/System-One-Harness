import pytest
from laya import budget_adapters as api
from token_budget_support import tokenizer
from token_budget_support import BASE


def inspect(q, head=256):
    assert hasattr(api,'inspect_head'), 'missing head accounting capability'
    return api.inspect_head(tokenizer(),q,head_max_len=head,question_id='q')


def description_at(tok,target):
    return next('word '*n for n in range(400) if len(tok.encode(' a: '+'word '*n))==target)


@pytest.mark.parametrize('length',[47,48,49])
def test_first_option_cap(length):
    tok=tokenizer();q=dict(BASE,criteria={'a':description_at(tok,length),'b':'Short.'})
    r=inspect(q); o=r['measurement']['options'][0]
    assert o['required_text_tokens']==length
    assert o['after_initial_cap_text_tokens']==min(length,48)
    assert [v['boundary'] for v in r['violations']]==(['option_text'] if length>48 else [])
    if r['violations']:
        v=r['violations'][0]
        assert (v['incoming'],v['limit'],v['retained'],v['unit'],v['option_key'])==(49,48,48,'option_text_tokens','a')


@pytest.mark.parametrize('length',[22,23,24])
def test_shared_head_span_boundary(length):
    tok=tokenizer();desc=description_at(tok,length)
    r=inspect(dict(BASE,criteria={'a':desc,'b':desc}),head=64)
    options=r['measurement']['options']
    assert all(o['after_shared_head_text_tokens']==min(length,23) for o in options)
    losses=[v for v in r['violations'] if v['boundary']=='shared_head_option']
    assert len(losses)==(2 if length>23 else 0)
    if losses: assert all((v['incoming'],v['limit'],v['retained'],v['unit'])==(25,24,24,'marker_inclusive_tokens') for v in losses)


@pytest.mark.parametrize('head',[192,256])
@pytest.mark.parametrize('delta',[-1,0,1])
def test_instruction_boundary(head,delta):
    tok=tokenizer();parts=api.encode_question(tok,BASE)
    limit=head-sum(1+len(x) for x in parts['option_ids'])
    q=next(dict(BASE,instructions='word '*n) for n in range(400) if len(tok.encode('choice question: '+'word '*n))==limit+delta)
    r=inspect(q,head)
    assert r['measurement']['instructions']=={'required_tokens':limit+delta,'limit':limit,'retained_tokens':min(limit+delta,limit)}
    assert any(v['boundary']=='instructions' for v in r['violations'])==(delta>0)


def test_scripted_83_token_option_in_105_token_request_and_no_double_count():
    q=dict(BASE,criteria={'first':'Description '*80,'second':'Short.'})
    tok=tokenizer(overrides={'choice question: Choose the relevant function.':range(8), ' first: '+'Description '*80:range(83), ' second: Short.':range(3), 'A short state.':range(5)})
    r=api.inspect_head(tok,q,head_max_len=256,question_id='q')
    assert r['measurement']['options'][0]['required_text_tokens']==83
    assert r['measurement']['untrimmed_head_tokens']+len(api.encode_state(tok,'A short state.'))+1==105
    assert r['violations'][0]['incoming']-r['violations'][0]['retained']==35
    crowded=inspect(dict(BASE,criteria={f'c{i}':'Description '*80 for i in range(30)}))
    first=crowded['measurement']['options'][0]
    assert first['required_text_tokens']>48
    assert first['after_initial_cap_text_tokens']==48
    assert first['after_shared_head_text_tokens']==7
    assert 'total_dropped' not in crowded['measurement']
    losses=[v for v in crowded['violations'] if v['option_index']==0]
    assert losses[0]['incoming']==first['required_text_tokens']
    assert losses[1]['incoming']==49


def test_assembled_head_may_exceed_allocation_without_artificial_violation():
    tok=tokenizer();q=dict(BASE,instructions='word '*500)
    r=inspect(q)
    assert len(r['ids'])==259
    assert not any(v['boundary']=='head_length' for v in r['violations'])
