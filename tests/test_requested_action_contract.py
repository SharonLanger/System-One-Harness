"""Overrides, custom preparation, errors, and registry reuse for the new block."""
from copy import deepcopy
from unittest.mock import Mock
import pytest
from test_requested_action_block import Harness, response, LABELS
from laya_context_router.block_runtime import Catalog, PreparedInput, SkipBlock, BlockInputError, BlockConfigurationError, BlockExecutionError
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from laya_context_router.laya.predict import ResponseError
from laya_context_router.questions.models import Question
from laya_context_router.block_runtime.catalog import TypedRule


def test_T23_T24_rules_same_response():
    catalog=Catalog();before=catalog.rule('requested_action_default').conditions
    for name,threshold in [('strict',.9),('loose',.1)]:
        catalog._rules[name]=TypedRule.from_dict({'name':name,'question_type':'choice','conditions':[{'field':'answer_confidence','op':'gte','value':threshold}]})
    h=Harness();raw=deepcopy(h.raw);overrides={'requested_action':'strict'}
    assert h.run(catalog=catalog,rule_overrides=overrides).data=={'action':'undecided'}
    assert h.run(catalog=catalog,rule_overrides={'requested_action':'loose'}).data=={'action':'explain'}
    assert overrides=={'requested_action':'strict'} and h.raw==raw and len(h.calls)==2
    assert catalog.rule('requested_action_default').conditions==before


@pytest.mark.parametrize('kwargs',[
 {'rule_overrides':{'requested_action':'multiple_methods_default'}},
 {'rule_overrides':{'requested_action':'missing'}}, {'rule_overrides':{'unknown':'requested_action_default'}},
 {'question_overrides':{'requested_action':'missing'}}, {'question_overrides':{'unknown':'requested_action'}},
 {'question_overrides':{'requested_action':{'type':'noul','instructions':'x'}}},
 *[{'question_overrides':{'requested_action':{'type':'choice','instructions':'x','criteria':criteria}}} for criteria in
   ({'explain':'x','generate_tests':'y'}, {'explain':'x','generate_tests':'y','modify_code':'z','extra':'q'}, {'explain':'x','generate_tests':'y','changed':'z'}, [], {'explain':1})]])
def test_T25_T26_T29_T30_T31_invalid_overrides(kwargs):
    h=Harness()
    with pytest.raises((BlockInputError,BlockConfigurationError)):h.run(**kwargs)
    assert not h.loads and not h.calls


def test_T27_T28_T32_T35_question_customization_and_order():
    q=Catalog().question('requested_action');q['instructions']='Changed request'
    q['criteria']=dict(reversed(list(q['criteria'].items())))
    h=Harness(response('modify_code')); saved=deepcopy(q)
    r=h.run(question_overrides={'requested_action':q})
    assert r.data=={'action':'modify_code'} and h.calls[-1][1]['requested_action']==q
    catalog=Catalog();catalog._questions['alternate']=Question.from_dict({'name':'alternate',**q})
    assert h.run(catalog=catalog,question_overrides={'requested_action':'alternate'}).data==r.data
    assert h.calls[-1][1]['requested_action']==q
    def prepare(value,questions):
        value['prompt']='mutated copy';questions['requested_action']['instructions']='Prepared'
        return PreparedInput('explicit custom text',questions,{'unused':True})
    data={'prompt':'original'};h.run(data,prepare_input=prepare)
    assert h.calls[-1][0]=='explicit custom text' and data=={'prompt':'original'} and q==saved


@pytest.mark.parametrize('change',['keys','type','labels','blank'])
def test_T33_bad_preparation(change):
    h=Harness()
    def prepare(value,q):
        if change=='keys':q['extra']=deepcopy(q['requested_action'])
        if change=='type':q['requested_action']={'type':'noul','instructions':'x'}
        if change=='labels':q['requested_action']['criteria']['extra']='x'
        return PreparedInput(' \n' if change=='blank' else 'x',q)
    with pytest.raises(BlockInputError):h.run(prepare_input=prepare)
    assert not h.loads and not h.calls


def test_T34_skip_and_T10_reducer_validation(monkeypatch):
    h=Harness()
    def skip(*args):raise SkipBlock('caller_skip')
    r=h.run(prepare_input=skip)
    assert (r.status,r.reason,r.decisions,r.data)==('skipped','caller_skip',{}, {'action':'undecided'})
    assert not h.loads and not h.calls
    from laya_context_router.building_blocks.questions.requested_action import block
    monkeypatch.setattr(block,'reduce',lambda *_:{'action':'unexpected'})
    with pytest.raises(BlockExecutionError):h.run()


@pytest.mark.parametrize('change',['missing_answer','type','choice','missing_probability','extra_probability','sum','nan','infinity'])
def test_T36_invalid_raw(change):
    raw=response();a=raw['answers']['requested_action']
    if change=='missing_answer':raw['answers'].clear()
    if change=='type':a['type']='noul'
    if change=='choice':a['choice']='other'
    if change=='missing_probability':del a['probabilities']['explain']
    if change=='extra_probability':a['probabilities']['extra']=0
    if change=='sum':a['probabilities']['explain']=.2
    if change=='nan':a['probabilities']['explain']=float('nan')
    if change=='infinity':a['answer_confidence']=float('inf')
    h=Harness(raw)
    with pytest.raises(ResponseError):h.run()
    assert len(h.calls)==1


@pytest.mark.parametrize('stage,error',[('load',RuntimeError('load')),('predict',RuntimeError('predict')),('predict',TimeoutError('deadline'))])
def test_T37_T40_errors_once_and_failed_load_not_cached(stage,error):
    h=Harness(error)
    loader=Mock(side_effect=error)
    if stage=='load':h.registry=AgentRegistry(loader=loader)
    for _ in range(2):
        with pytest.raises(type(error)) as caught:h.run()
        assert caught.value is error
    assert (loader.call_count if stage=='load' else len(h.calls))==2


def test_T38_T39_T40_registry_config_isolation():
    h=Harness()
    configs=[RunConfig(model='A'),RunConfig(model='A'),RunConfig(model='B',temperature=.2,lang='he'),RunConfig(model='A',temperature=.3)]
    for c in configs:h.run(config=c)
    assert h.loads==[('A',{'lang_temperatures':{'en':{'temperature':[1.0]*3}}}),('B',{'lang_temperatures':{'he':{'temperature':[.2]*3}}}),('A',{'lang_temperatures':{'en':{'temperature':[.3]*3}}})]
    assert h.calls[2][2]=={'lang':'he'}
    h.registry=AgentRegistry(loader=h.load);h.run(config=configs[0]);assert len(h.loads)==4

