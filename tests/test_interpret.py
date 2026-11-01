import copy
import json
from pathlib import Path
import pytest
from answers.interpret import extract_answer, interpret
from answers.rules import RulesConfig
from laya.predict import predict, ResponseError
from test_predict import Agent

ROOT=Path(__file__).parent/'fixtures/laya'
REQUEST=json.loads((ROOT/'captured-request.json').read_text())
RAW=json.loads((ROOT/'captured-raw.json').read_text())

def policies(questions):
    return {name:RulesConfig.from_dict({'name':name,'conditions':[]}) for name in questions}

@pytest.mark.parametrize('prediction,answer',[
    ({'type':'choice','choice':'none_or_unclear'},'none_or_unclear'),
    ({'type':'noul','noul':0.49999},'no'),({'type':'noul','noul':0.5},'yes'),({'type':'noul','noul':0.50001},'yes'),
    *[({'type':'score','score':value,'legend':{'0':'zero','1':'one','2':'two','3':'three'}},answer) for value,answer in [(1.5,'two'),(2.5,'two'),(-8,'zero'),(9,'three')]],
])
def test_legacy_extract_exact(prediction,answer):
    assert extract_answer(prediction)==answer


def test_captured_multiquestion_full_pipeline_no_ground_truth():
    raw=predict(REQUEST['text'],REQUEST['questions'],model=REQUEST['model'],loader=lambda model:Agent(RAW))
    original=copy.deepcopy(raw)
    decisions=interpret(raw,REQUEST['questions'],policies(REQUEST['questions']))
    assert {name:entry['answer'] for name,entry in decisions.items()}=={'department':'billing','urgency':'medium — issue needs resolving within a few days','churn_risk':'yes','sentiment':'negative','contains_threat':'yes'}
    assert all(entry['decided'] and entry['reason'] is None for entry in decisions.values())
    assert raw==original
    assert decisions['urgency']['answer']!='high — customer is blocked or very frustrated'


def test_policy_rejection_and_rounding_boundary():
    questions={'q':{'type':'noul','instructions':'Is it?'}}
    rules={'q':RulesConfig.from_dict({'name':'not-q','conditions':[{'field':'distance_from_boundary','op':'gte','value':0.1}]})}
    for value,accepted in [(0.59994,False),(0.59996,True),(0.60006,True)]:
        got=interpret({'answers':{'q':{'type':'noul','noul':value}}},questions,rules)['q']
        assert got=={'answer':'yes' if accepted else 'undecided','decided':accepted,'reason':None if accepted else 'below_threshold:distance_from_boundary'}


def test_accepted_abstention_distinct_from_policy_rejection():
    q={'q':{'type':'choice','instructions':'Choose','criteria':{'none_or_unclear':'none','x':'x'}}}
    raw={'answers':{'q':{'type':'choice','choice':'none_or_unclear','probabilities':{'none_or_unclear':0.9,'x':0.1}}}}
    assert interpret(raw,q,policies(q))['q']=={'answer':'none_or_unclear','decided':True,'reason':None}

@pytest.mark.parametrize('change',[
    lambda raw:raw.pop('answers'),lambda raw:raw.update(answers=[]),
    lambda raw:raw['answers'].pop('department'),
    lambda raw:raw['answers']['department'].update(type='noul'),
    lambda raw:raw['answers']['department'].update(choice='other'),
    lambda raw:raw['answers']['department'].update(probabilities={'billing':1}),
    lambda raw:raw['answers']['urgency'].update(score=float('nan')),
    lambda raw:raw['answers']['urgency'].update(score=True),
    lambda raw:raw['answers']['urgency'].update(legend={'1':'one'}),
    lambda raw:raw['answers']['urgency']['legend'].update({'0':'wrong label'}),
    lambda raw:raw['answers']['churn_risk'].update(noul=1.1),
    lambda raw:raw['answers']['churn_risk'].update(noul='0.5'),
    lambda raw:raw['answers']['department'].update(answer_confidence=float('inf')),
])
def test_invalid_predictions_never_accepted(change):
    raw=copy.deepcopy(RAW); change(raw); original=copy.deepcopy(raw)
    got=interpret(raw,REQUEST['questions'],policies(REQUEST['questions']))
    assert any(not d['decided'] and d['reason'].startswith('invalid_prediction:') for d in got.values())
    # JSON preserves NaN literals for this equality check without treating them as valid data.
    assert json.dumps(raw,sort_keys=True)==json.dumps(original,sort_keys=True)
    with pytest.raises(ResponseError): predict('x',REQUEST['questions'],loader=lambda model:Agent(raw))


def test_requested_questions_all_returned_extra_ignored_missing_policy_errors():
    q={'q':{'type':'noul','instructions':'Is it?'}}
    assert interpret({'answers':{'q':{'type':'noul','noul':0},'extra':{'type':'noul','noul':1}}},q,policies(q))=={'q':{'answer':'no','decided':True,'reason':None}}
    assert list(interpret({'answers':{}},q,policies(q)))==['q']
    with pytest.raises(ValueError,match='policies'): interpret(RAW,q,{})


def test_score_legend_schema_and_clamping():
    q={'q':{'type':'score','instructions':'Score','criteria':['low','high']}}
    for score,expected in [(-2,'low'),(4,'high')]:
        raw={'answers':{'q':{'type':'score','score':score,'legend':{'0':'low','1':'high'},'probabilities':{'0':0.1,'1':0.9}}}}
        assert interpret(raw,q,policies(q))['q']['answer']==expected
