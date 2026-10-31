from examples._plumbing_inspection import plumbing_provider
import copy
import json
import pytest
from laya_context_router.questions.models import Question, ChoiceQuestion, NoulQuestion, ScoreQuestion
from laya_context_router.questions.load import load_questions
from laya_context_router.laya.predict import predict
from test_predict import Agent, REQUEST, RAW

DEFINITIONS=[
    {'name':'fruit','type':'choice','instructions':'Which fruit?','criteria':{'apple':'red','pear':'green'}},
    {'name':'certain','type':'noul','instructions':'Is it certain?'},
    {'name':'rank','type':'score','instructions':'How much?','criteria':['low','medium','high']},
]

@pytest.mark.parametrize('definition,kind',list(zip(DEFINITIONS,[ChoiceQuestion,NoulQuestion,ScoreQuestion])))
def test_typed_roundtrip_exact_payload(definition,kind):
    q=Question.from_dict(definition)
    assert isinstance(q,kind)
    assert q.to_dict()==definition
    expected=copy.deepcopy(definition); del expected['name']
    assert q.to_predict_dict()==expected
    assert not hasattr(q,'evaluate')


def test_single_list_loader_and_order(tmp_path):
    path=tmp_path/'q.json'; path.write_text(json.dumps(DEFINITIONS))
    questions=load_questions(path)
    assert list(questions)==['fruit','certain','rank']
    assert list(questions['fruit'].criteria)==['apple','pear']
    assert questions['rank'].criteria==['low','medium','high']
    path.write_text(json.dumps(DEFINITIONS[0]))
    assert list(load_questions(path))==['fruit']
    path.write_text('[]'); assert load_questions(path)=={}


@pytest.mark.parametrize('definition',[
    {}, {'name':'q','type':'other','instructions':'x'},
    {'name':'','type':'noul','instructions':'x'},
    {'name':'q','type':'noul','instructions':None},
    {'name':'q','type':'choice','instructions':'x'},
    {'name':'q','type':'choice','instructions':'x','criteria':[]},
    {'name':'q','type':'choice','instructions':'x','criteria':{}},
    {'name':'q','type':'choice','instructions':'x','criteria':{'x':7}},
    {'name':'q','type':'score','instructions':'x','criteria':{}},
    {'name':'q','type':'score','instructions':'x','criteria':[]},
    {'name':'q','type':'score','instructions':'x','criteria':[True]},
])
def test_invalid_definition(definition):
    with pytest.raises(ValueError): Question.from_dict(definition)


def test_duplicate_missing_and_malformed_file(tmp_path):
    p=tmp_path/'q.json'
    with pytest.raises(FileNotFoundError): load_questions(p)
    p.write_text('{')
    with pytest.raises(ValueError): load_questions(p)
    p.write_text(json.dumps([DEFINITIONS[0],DEFINITIONS[0]]))
    with pytest.raises(ValueError,match='duplicate'): load_questions(p)
    p.write_text('42')
    with pytest.raises(ValueError): load_questions(p)


@pytest.mark.parametrize('definition', [DEFINITIONS[0],DEFINITIONS[2]])
def test_independent_mutable_criteria(definition):
    original=copy.deepcopy(definition)
    a,b=Question.from_dict(definition),Question.from_dict(definition)
    if isinstance(a.criteria,dict): a.criteria['new']='candidate'
    else: a.criteria.append('new')
    assert b.to_dict()==original and definition==original
    out=b.to_predict_dict(); out['criteria'].clear()
    assert b.to_dict()==original


def test_json_loaded_same_request_result(tmp_path):
    definition={'name':'department',**REQUEST['questions']['department']}
    path=tmp_path/'q.json'; path.write_text(json.dumps([definition]))
    payload={name:q.to_predict_dict() for name,q in load_questions(path).items()}
    assert payload==REQUEST['questions']
    agent=Agent()
    assert predict(REQUEST['text'],payload,inspection_provider=plumbing_provider, loader=lambda model:agent)==RAW
    assert agent.calls==[((REQUEST['text'],REQUEST['questions']),{})]
    assert RAW['answers']['department']['choice']=='billing'
