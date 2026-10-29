import json
import pytest
from laya_context_router.answers.conditions import OPS, resolve_field, evaluate_conditions
from laya_context_router.answers.rules import RulesConfig, accepts

@pytest.mark.parametrize('op,value,expected',[
    ('gt',0.4,False),('gt',0.5,False),('gt',0.6,True),
    ('gte',0.4,False),('gte',0.5,True),('gte',0.6,True),
    ('lt',0.4,True),('lt',0.5,False),('lt',0.6,False),
    ('lte',0.4,True),('lte',0.5,True),('lte',0.6,False),
    ('eq',0.4,False),('eq',0.5,True),('eq',0.6,False),
])
def test_all_operators(op,value,expected):
    assert OPS[op](value,0.5) is expected
    assert evaluate_conditions({'x':value},[{'field':'x','op':op,'value':0.5}]) == (expected,None if expected else 'below_threshold:x')


def test_nested_missing_null_and_legacy_eq():
    data={'action':{'probability':0.8},'null':None,'scalar':2}
    assert resolve_field(data,'action.probability')==0.8
    for path in ['absent','null','scalar.deep','absent.deep']:
        assert resolve_field(data,path) is None
        assert evaluate_conditions(data,[{'field':path,'op':'gte','value':0.5}]) == (False,f'field_missing:{path}')
        assert evaluate_conditions(data,[{'field':path,'op':'eq','value':None}]) == (True,None)
    assert evaluate_conditions(data,[]) == (True,None)


def test_shared_type_conditions_first_failure_and_tuple_unpacking(tmp_path):
    common=[{'field':'answer_confidence','op':'gte','value':0.5}]
    specific=[{'field':'probability_gap','op':'gte','value':0.1}]
    data={'name':'policy-not-question','conditions':common,'conditions_by_type':{'choice':specific}}
    path=tmp_path/'rules.json'; path.write_text(json.dumps(data))
    rules=RulesConfig.from_file(path)
    assert rules.conditions_for('choice')==common+specific
    assert rules.conditions_for('noul')==common
    assert accepts({'type':'choice','answer_confidence':0.9,'probability_gap':0.2},rules)==(True,None)
    decided,reason=accepts({'type':'choice','answer_confidence':0.4,'probability_gap':0.01},rules)
    assert decided is False and reason=='below_threshold:answer_confidence'
    assert bool((decided,reason)) is True  # why callers must unpack the tuple
    assert accepts({'type':'choice','answer_confidence':0.9,'probability_gap':0.01},rules)==(False,'below_threshold:probability_gap')
    assert accepts({'type':'noul','answer_confidence':0.9},rules)==(True,None)
    assert RulesConfig.from_dict({'name':'empty','conditions':[]}).conditions_for('score')==[]


@pytest.mark.parametrize('data',[
    {},{'name':'x'}, {'conditions':[]}, {'name':'x','conditions':None},
    {'name':'x','conditions':[{}]},
    {'name':'x','conditions':[{'field':'x','op':'nope','value':1}]},
    {'name':'x','conditions':[{'field':3,'op':'eq','value':1}]},
    {'name':'x','conditions':[],'conditions_by_type':[]},
    {'name':'x','conditions':[],'conditions_by_type':{'choice':[{'field':'x','op':'eq'}]}},
    {'name':'x','conditions':[],'conditions_by_type':{'choice':None}},
    {'name':'x','conditions':[],'conditions_by_type':{'bad':[]}},
    {'name':'x','conditions':[{'field':'x','op':'gt','value':float('nan')}]},
])
def test_malformed_policy_rejected(data):
    with pytest.raises(ValueError): RulesConfig.from_dict(data)


@pytest.mark.parametrize('op',[[],{},['eq'],{'operator':'eq'}])
@pytest.mark.parametrize('scope',['common','choice'])
def test_unhashable_condition_operator_rejected(op,scope):
    conditions=[{'field':'x','op':op,'value':1}]
    data={'name':'policy','conditions':conditions if scope=='common' else []}
    if scope=='choice': data['conditions_by_type']={'choice':conditions}
    with pytest.raises(ValueError,match='unknown condition operator'):
        RulesConfig.from_dict(data)


def test_failed_upper_bound_legacy_reason():
    assert evaluate_conditions({'x':0.9},[{'field':'x','op':'lte','value':0.2}])==(False,'below_threshold:x')
