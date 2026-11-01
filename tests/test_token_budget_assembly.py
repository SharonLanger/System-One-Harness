"""Hand-specified mock-token assembly expectations; not upstream SDK parity."""
from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from laya_context_router.laya import budget_adapters as api
from token_budget_support import tokenizer,BASE

@pytest.mark.parametrize('state',['state',{'content':'state'},[{'content':'state'}]])
@pytest.mark.parametrize('max_len',[12,14,15])
def test_marker_positions_and_state_retention_with_scripted_ids(state,max_len):
    q={'type':'choice','instructions':'Pick','criteria':{'a':'A','b':'B'}}
    rendered=state if isinstance(state,str) else json.dumps(state,ensure_ascii=False)
    tok=tokenizer(overrides={'choice question: Pick':[10,11],' a: A':[20,21],' b: B':[30],rendered:[40,41,42]})
    head=[0,10,11,1,3,20,21,3,30,1]
    kept=([42] if isinstance(state,list) else [40]) if max_len==12 else [40,41,42]
    expected={'ids':head+kept+[1],'markers':[4,7]}
    assert api.assemble_sequence(tok,state,q,max_len=max_len,head_max_len=256)==expected
    with ThreadPoolExecutor(4) as pool:
        assert all(value==expected for value in pool.map(lambda _:api.assemble_sequence(tok,state,q,max_len=max_len,head_max_len=256),range(8)))


def test_final_slice_removes_out_of_range_marker():
    q={'type':'choice','instructions':'Pick','criteria':{'a':'A','b':'B'}}
    tok=tokenizer(overrides={'choice question: Pick':[10,11],' a: A':[20,21],' b: B':[30],'state':[]})
    assert api.assemble_sequence(tok,'state',q,max_len=7,head_max_len=256)=={'ids':[0,10,11,1,3,20,21],'markers':[4]}
