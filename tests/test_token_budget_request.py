import json
import pytest
from laya_context_router.laya import budget_adapters as api
from token_budget_support import tokenizer
from token_budget_support import BASE


def inspect(state,questions=None,max_len=1024,head=256):
    assert hasattr(api,'inspect_request'), 'missing complete-request accounting'
    return api.inspect_request(tokenizer(),state,questions or {'q':BASE},model='fixture',max_len=max_len,head_max_len=head,request_id='r')


@pytest.mark.parametrize('max_len,head',[(1024,256),(512,192)])
@pytest.mark.parametrize('delta',[-1,0,1])
def test_state_exact_boundary(max_len,head,delta):
    tok=tokenizer(); h=api.inspect_head(tok,BASE,head_max_len=head)
    room=max_len-len(h['ids'])-1
    r=inspect(' hello'*(room+delta),max_len=max_len,head=head)
    q=r['questions'][0]
    assert q['state']=={'required_tokens':room+delta,'allowance':room,'retained_tokens':min(room,room+delta),'direction':'right'}
    boundaries={v['boundary'] for v in r['violations']}
    assert boundaries==({'state','full_request'} if delta>0 else set())
    assert q['final_sequence_tokens']==min(max_len,max_len+delta)
    assert json.loads(json.dumps(r,allow_nan=False))==r


def test_list_state_keeps_newest_mock_tokens():
    state=[{'role':'user','content':'old '*1500},{'role':'user','content':'newest intent'}]
    r=inspect(state); q=r['questions'][0]
    assert q['state']['direction']=='left'
    tok=tokenizer();result=api.assemble_sequence(tok,state,BASE,max_len=1024,head_max_len=256)
    raw=api.encode_state(tok,state);room=q['state']['allowance']
    assert result['ids'][-room-1:-1]==raw[-room:]


def test_all_questions_measured_without_inference():
    questions={'fits':BASE,'option':dict(BASE,criteria={'a':'Description '*80,'b':'Short.'}),'instruction':dict(BASE,instructions='word '*500)}
    r=inspect('hello',questions)
    assert [q['question_id'] for q in r['questions']]==list(questions)
    assert {v['question_id'] for v in r['violations']}=={'option','instruction'}
    assert r['request_inference_started'] is False and r['inspection_status']=='complete'
    assert r['questions'][0]['state']['allowance']!=r['questions'][2]['state']['allowance']
    assert all('ids' not in q for q in r['questions'])


def test_empty_state_head_overflow_and_final_retention():
    q=dict(BASE,criteria={f'candidate_{i}':'Unique function.' for i in range(300)})
    r=inspect('',{'q':q});m=r['questions'][0]
    assert m['state']['required_tokens']==m['state']['retained_tokens']==0
    assert m['markers']['retained']<m['markers']['required']==300
    assert {'full_request','final_sequence','option_markers'}<={v['boundary'] for v in r['violations']}
    assert m['options'][-1]['final_retained_text_tokens']==0
    assert m['final_sequence_tokens']==1024


def test_full_requirement_not_hidden_by_prior_trimming():
    q=dict(BASE,instructions='word '*1500)
    r=inspect('',{'q':q});m=r['questions'][0]
    assert m['untrimmed_sequence_tokens']>1024>m['final_sequence_tokens']
    assert {v['boundary'] for v in r['violations']}=={'instructions','full_request'}
    assert 'total_dropped' not in m


def test_final_sequence_exact_boundaries():
    # Qualified head construction alone can exceed a small chosen sequence cap.
    tok=tokenizer();q=dict(BASE,criteria={f'c{i}':'word word' for i in range(20)})
    h=api.inspect_head(tok,q,head_max_len=64)
    length=len(h['ids'])+1
    for max_len in (length-1,length,length+1):
        r=inspect('',{'q':q},max_len=max_len,head=64)
        assert any(v['boundary']=='final_sequence' for v in r['violations'])==(max_len<length)
