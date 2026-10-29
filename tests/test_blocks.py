import copy
import json
from pathlib import Path
import pytest
from laya_context_router.blocks import QuestionBlock
from laya_context_router.answers.rules import load_named_rules
from laya_context_router.building_blocks.questions.ticket_triage.block import run, BLOCK_DIR
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_interpret import REQUEST, RAW


def write_block(path,names=('department',)):
    definitions=[{'name':name,**REQUEST['questions'][name]} for name in names]
    path.mkdir(exist_ok=True)
    (path/'questions.json').write_text(json.dumps(definitions))
    policies={'rules_by_question':{name:{'name':'policy-'+name,'conditions':[]} for name in names}}
    (path/'rules.json').write_text(json.dumps(policies))
    return policies


def test_single_question_same_envelope(tmp_path):
    write_block(tmp_path)
    block=QuestionBlock(tmp_path)
    raw={**RAW,'answers':{'department':RAW['answers']['department']}}
    class Fake:
        def predict(self,text,questions):
            assert text==REQUEST['text'] and questions=={'department':REQUEST['questions']['department']}
            return copy.deepcopy(raw)
    registry=AgentRegistry(loader=lambda model:Fake())
    assert block.run(REQUEST['text'],config=RunConfig(),registry=registry)=={'department':{'answer':'billing','decided':True,'reason':None}}


def test_two_question_example_exact_sequence_settings_reuse_and_mixed_results():
    names=['department','churn_risk']
    questions={name:REQUEST['questions'][name] for name in names}
    first={**RAW,'answers':{name:copy.deepcopy(RAW['answers'][name]) for name in names}}
    second=copy.deepcopy(first)
    second['answers']['department'].update(choice='technical',answer_confidence=0.8,probabilities={'billing':0.1,'technical':0.8,'sales':0.1})
    second['answers']['churn_risk'].update(noul=0.8,answer_confidence=0.8)
    original=copy.deepcopy([first,second]); responses=[first,second]; loads=[]; calls=[]
    class Fake:
        def predict(self,text,payload,**kwargs):
            assert (text,payload,kwargs)==(REQUEST['text'],questions,{'lang':'fr'})
            assert not any(key in json.dumps(payload) for key in ['rules_by_question','expected','conditions'])
            calls.append((text,copy.deepcopy(payload),kwargs))
            return copy.deepcopy(responses.pop(0))
    agent=Fake()
    def loader(model,**kwargs):
        assert (model,kwargs)==('mock-A',{'lang_temperatures':{'fr':{'temperature':[0.2]*3}}})
        loads.append(model); return agent
    registry=AgentRegistry(loader=loader); config=RunConfig('mock-A',0.2,'fr')
    assert run(REQUEST['text'],config=config,registry=registry)=={'department':{'answer':'billing','decided':True,'reason':None},'churn_risk':{'answer':'undecided','decided':False,'reason':'below_threshold:distance_from_boundary'}}
    assert run(REQUEST['text'],config=config,registry=registry)=={'department':{'answer':'undecided','decided':False,'reason':'below_threshold:answer_confidence'},'churn_risk':{'answer':'yes','decided':True,'reason':None}}
    assert loads==['mock-A'] and len(calls)==2 and responses==[]
    assert [first,second]==original
    assert {p.name for p in BLOCK_DIR.iterdir() if p.is_file()}=={'questions.json','rules.json','block.py','README.md'}


@pytest.mark.parametrize('data',[
    {}, {'rules_by_question':[]}, {'department':{'name':'x','conditions':[]}},
    {'rules_by_question':{}},
    {'rules_by_question':{'other':{'name':'x','conditions':[]}}},
    {'rules_by_question':{'department':{'name':'x'}}},
])
def test_invalid_named_policy_envelope(tmp_path,data):
    path=tmp_path/'rules.json';path.write_text(json.dumps(data))
    with pytest.raises(ValueError):load_named_rules(path,['department'])


@pytest.mark.parametrize('text',[
    '{"rules_by_question":{},"rules_by_question":{}}',
    '{"rules_by_question":{"department":{"name":"x","conditions":[]},"department":{"name":"y","conditions":[]}}}',
    '{"rules_by_question":{"department":{"name":"x","name":"y","conditions":[]}}}',
])
def test_duplicate_rule_json_keys_rejected(tmp_path,text):
    path=tmp_path/'r.json';path.write_text(text)
    with pytest.raises(ValueError,match='duplicate'): load_named_rules(path,['department'])


def test_duplicate_question_json_keys_rejected(tmp_path):
    write_block(tmp_path)
    (tmp_path/'questions.json').write_text('[{"name":"department","name":"other","type":"noul","instructions":"Is it?"}]')
    with pytest.raises(ValueError,match='duplicate'):QuestionBlock(tmp_path)


def test_policy_inner_name_not_binding_and_empty_block_rejected(tmp_path):
    write_block(tmp_path)
    assert load_named_rules(tmp_path/'rules.json',['department'])['department'].name=='policy-department'
    (tmp_path/'questions.json').write_text('[]')
    with pytest.raises(ValueError,match='empty'):QuestionBlock(tmp_path)


def test_block_raw_validation_and_sdk_errors_propagate(tmp_path):
    from laya_context_router.laya.predict import ResponseError
    write_block(tmp_path)
    block=QuestionBlock(tmp_path)
    class Invalid:
        def predict(self,*args): return {'answers':{}}
    with pytest.raises(ResponseError):
        block.run('ticket',config=RunConfig(),registry=AgentRegistry(loader=lambda model:Invalid()))
    def fail(model): raise RuntimeError('planned load error')
    with pytest.raises(RuntimeError,match='planned load error'):
        block.run('ticket',config=RunConfig(),registry=AgentRegistry(loader=fail))
