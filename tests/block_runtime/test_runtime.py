from laya_context_router.block_runtime import Block, Catalog, PreparedInput


def test_packaged_defaults_match_existing_policies():
    catalog = Catalog()
    rule = catalog.rule('method_selection_default')
    assert [c['value'] for c in rule.conditions] == [0.5, 0.15]
    assert catalog.rule('multiple_methods_default').conditions == [
        {'field': 'answer_confidence', 'op': 'gte', 'value': 0.5}]

import json
from copy import deepcopy
from pathlib import Path
import pytest
from laya_context_router.block_runtime import (BlockConfigurationError, BlockInputError,
    BlockExecutionError, SkipBlock)
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from laya_context_router.laya.predict import ResponseError


def catalog_at(tmp_path, rules=None, questions=None):
    for folder, values in [('rules', rules or []), ('questions', questions or [])]:
        (tmp_path/folder).mkdir(exist_ok=True)
        for i, value in enumerate(values):
            (tmp_path/folder/f'{i}.json').write_text(json.dumps(value))
    return Catalog(tmp_path)


def rule(kind='choice', conditions=None, name='accept'):
    return {'name':name, 'question_type':kind, 'conditions':[] if conditions is None else conditions}


def question(kind='choice'):
    body={'type':kind,'instructions':'Pick.'}
    if kind=='choice': body['criteria']={'a':'Alpha','b':'Beta','c':'Gamma'}
    if kind=='score': body['criteria']=['low','medium','high']
    return body


def raw(kind='choice'):
    if kind=='choice': return {'type':kind,'choice':'b','probabilities':{'a':.7,'b':.2,'c':.1},'answer_confidence':.8}
    if kind=='noul': return {'type':kind,'noul':.8,'answer_confidence':.8}
    return {'type':kind,'score':1.6,'legend':{'0':'low','1':'medium','2':'high'},'probabilities':{'0':.1,'1':.2,'2':.7}}


def make_block(tmp_path, kind='choice', rules=None, **kwargs):
    catalog=catalog_at(tmp_path, rules or [rule(kind)])
    return Block({'name':'tiny','questions':{'local':{'definition':question(kind),'rule_ref':'accept'}}},
        catalog=catalog, validate_input=lambda value: value if isinstance(value,dict) and isinstance(value.get('text'),str) else (_ for _ in ()).throw(ValueError('text required')),
        prepare_input=kwargs.pop('preparer',lambda value,questions: PreparedInput(value['text'],questions)),
        reduce=kwargs.pop('reducer',lambda decisions,state: decisions), validate_output=kwargs.pop('output',lambda value:value), **kwargs)


def execute(block, response=None, **kwargs):
    calls=[]
    class Agent:
        def predict(self,text,questions,**options):
            calls.append((text,deepcopy(questions),options))
            return {'answers':{'local':deepcopy(response or raw())}}
    registry=AgentRegistry(loader=lambda model,**options: Agent())
    return block.run({'text':'  original  '},config=RunConfig(model='fake'),registry=registry,**kwargs),calls


@pytest.mark.parametrize('kind,answer',[('choice','b'),('noul','yes'),('score','high')])
def test_supported_types_extract_sdk_answer_without_argmax(tmp_path,kind,answer):
    result,calls=execute(make_block(tmp_path,kind),raw(kind))
    assert result.status=='completed' and result.decisions['local']['answer']==answer
    assert len(calls)==1 and calls[0][0]=='  original  '


@pytest.mark.parametrize('expected,actual',[(a,b) for a in ['choice','noul','score'] for b in ['choice','noul','score'] if a!=b])
def test_all_wrong_type_rules_fail_at_declaration(tmp_path,expected,actual):
    with pytest.raises(BlockConfigurationError,match='rule_type_mismatch'):
        make_block(tmp_path,expected,rules=[rule(actual)])


@pytest.mark.parametrize('kind,field',[('choice','distance_from_boundary'),('noul','probability_gap'),('score','distance_from_boundary')])
def test_wrong_metric_rejected(tmp_path,kind,field):
    with pytest.raises(BlockConfigurationError,match='unsupported metric'):
        catalog_at(tmp_path,[rule(kind,[{'field':field,'op':'gte','value':.5}])])


@pytest.mark.parametrize('value',[None,'0.5',True,float('inf'),float('nan')])
def test_invalid_threshold_rejected(tmp_path,value):
    with pytest.raises(BlockConfigurationError):
        catalog_at(tmp_path,[rule(conditions=[{'field':'confidence','op':'gte','value':value}])])


def test_whole_rule_override_and_next_default_are_isolated(tmp_path):
    strict=rule(conditions=[{'field':'probability_gap','op':'gte','value':.6}])
    permissive=rule(name='permissive',conditions=[{'field':'answer_confidence','op':'gte','value':.8}])
    block=make_block(tmp_path,rules=[strict,permissive])
    first,calls=execute(block,rule_overrides={'local':'permissive'})
    second,more=execute(block)
    assert first.decisions['local']['answer']=='b'
    assert second.decisions['local']['reason']=='below_threshold:probability_gap'
    assert calls[0][1]==more[0][1]


@pytest.mark.parametrize('field,threshold,reason',[('probability_gap',.5,None),('probability_gap',.5001,'below_threshold:probability_gap'),('action.act_probability',.1,'field_missing:action.act_probability')])
def test_metrics_boundaries_and_missing_field(tmp_path,field,threshold,reason):
    block=make_block(tmp_path,rules=[rule(conditions=[{'field':field,'op':'gte','value':threshold}])])
    result,_=execute(block)
    assert result.decisions['local']['reason']==reason


@pytest.mark.parametrize('override',[{'unknown':'accept'}, {'local':'missing'}, {'local':'../accept'}])
def test_bad_rule_override_never_predicts(tmp_path,override):
    block=make_block(tmp_path)
    with pytest.raises(BlockConfigurationError): execute(block,rule_overrides=override)


@pytest.mark.parametrize('override',[{'unknown':question()},{'local':question('noul')},{'local':{'type':'choice','instructions':'missing criteria'}}])
def test_bad_question_override_rejected(tmp_path,override):
    with pytest.raises(BlockConfigurationError): execute(make_block(tmp_path),question_overrides=override)


@pytest.mark.parametrize('prepared',[None,{},PreparedInput(1,{}),PreparedInput('x',{}),PreparedInput('x',{'local':question('noul')}),PreparedInput('x',{'local':{'type':'choice','instructions':'x'}})])
def test_prepared_contract_rejects_before_predict(tmp_path,prepared):
    with pytest.raises(BlockInputError): execute(make_block(tmp_path,preparer=lambda *_:prepared))


def test_skip_preserves_state_and_utility_error_cause(tmp_path):
    def skip(*_): raise SkipBlock('empty',{'extra':1})
    block=make_block(tmp_path,preparer=skip,reducer=lambda decisions,state:state)
    result,calls=execute(block)
    assert result.status=='skipped' and result.decisions=={} and result.data=={'extra':1,'reason':'empty'} and not calls
    def broken(*_): raise RuntimeError('utility')
    block.prepare_input=broken
    with pytest.raises(BlockExecutionError) as caught: execute(block)
    assert isinstance(caught.value.__cause__,RuntimeError)


@pytest.mark.parametrize('response',[{}, {'type':'noul','noul':.5}, {**raw(),'probabilities':{'a':.7,'b':.2,'c':.2}}, {**raw(),'answer_confidence':float('nan')}])
def test_invalid_raw_preserves_response_error(tmp_path,response):
    # Empty dict must be delivered directly, not replaced by the convenience fake.
    block=make_block(tmp_path)
    class Agent:
        def predict(self,*args,**kwargs): return {'answers':{'local':response}}
    with pytest.raises(ResponseError):
        block.run({'text':'x'},config=RunConfig(model='fake'),registry=AgentRegistry(loader=lambda *a,**k:Agent()))


def test_enrichment_once_each_and_raw_is_unchanged(tmp_path,monkeypatch):
    import laya_context_router.block_runtime.runtime as runtime
    original=runtime.enrich_prediction
    observed=[]
    def spy(prediction):
        enriched=original(prediction); observed.append(enriched); return enriched
    monkeypatch.setattr(runtime,'enrich_prediction',spy)
    source=raw(); saved=deepcopy(source)
    execute(make_block(tmp_path),source)
    assert len(observed)==1 and observed[0]['probability_gap']==.5
    assert source==saved


@pytest.mark.parametrize('name',['../bad','/absolute','bad/name','',None])
def test_catalog_names_cannot_be_paths(tmp_path,name):
    catalog=catalog_at(tmp_path)
    with pytest.raises(BlockConfigurationError): catalog.rule(name)


def test_catalog_duplicate_and_json_duplicate_rejected(tmp_path):
    with pytest.raises(BlockConfigurationError,match='duplicate catalog name'):
        catalog_at(tmp_path,[rule(),rule()])
    (tmp_path/'rules'/'1.json').unlink()
    (tmp_path/'rules'/'0.json').write_text('{"name":"a","name":"b"}')
    with pytest.raises(BlockConfigurationError,match='duplicate JSON key'): Catalog(tmp_path)


def test_catalog_objects_are_copied_and_cwd_independent(tmp_path,monkeypatch):
    catalog=Catalog(); item=catalog.question('department'); item['criteria'].clear()
    rule_copy=catalog.rule('ticket_department_default'); rule_copy.conditions.clear()
    monkeypatch.chdir(tmp_path)
    assert len(catalog.question('department')['criteria'])==3
    assert len(Catalog().rule('ticket_department_default').conditions)==2


def test_two_question_binding_partial_override_and_independence(tmp_path):
    catalog=catalog_at(tmp_path,[rule(),rule(name='strict',conditions=[{'field':'answer_confidence','op':'gte','value':.9}])],
        [{'name':'shared',**question()}])
    block=Block({'name':'two','questions':{name:{'question_ref':'shared','rule_ref':'accept'} for name in ('first','second')}},
        catalog=catalog,validate_input=lambda value:value,prepare_input=lambda value,q:PreparedInput(value['text'],q),
        reduce=lambda d,s:d,validate_output=lambda d:d)
    calls=[]
    class Agent:
        def predict(self,text,questions,**kwargs):
            calls.append(deepcopy(questions))
            questions['first']['criteria'].clear()
            return {'answers':{'first':raw(),'second':raw(),'extra':raw()}}
    registry=AgentRegistry(loader=lambda *a,**k:Agent())
    kwargs={'config':RunConfig(model='x'),'registry':registry}
    result=block.run({'text':''},rule_overrides={'first':'strict'},**kwargs)
    assert not result.decisions['first']['decided'] and result.decisions['second']['decided']
    assert set(result.decisions)=={'first','second'} and len(calls)==1
    again=block.run({'text':''},rule_overrides={},question_overrides={},**kwargs)
    assert all(d['decided'] for d in again.decisions.values()) and calls[0]==calls[1]


def test_question_override_shared_and_inline_payloads(tmp_path):
    block=make_block(tmp_path)
    block.catalog._questions['shared']=__import__('laya_context_router.questions.models',fromlist=['Question']).Question.from_dict({'name':'shared',**question()})
    _,calls=execute(block,question_overrides={'local':'shared'})
    custom={**question(),'instructions':'Different request'}
    _,changed=execute(block,question_overrides={'local':custom})
    assert calls[0][1]['local']['instructions']=='Pick.'
    assert changed[0][1]['local']['instructions']=='Different request'
    assert set(changed[0][1]['local'])=={'type','instructions','criteria'}


@pytest.mark.parametrize('value,expected',[(.4999,'no'),(.5,'yes'),(.5001,'yes')])
def test_noul_boundary(tmp_path,value,expected):
    result,_=execute(make_block(tmp_path,'noul'),{**raw('noul'),'noul':value})
    assert result.decisions['local']['answer']==expected


@pytest.mark.parametrize('score,expected',[(-5,'low'),(.49,'low'),(.5,'low'),(1.5,'high'),(50,'high')])
def test_score_rounding_and_clamping(tmp_path,score,expected):
    result,_=execute(make_block(tmp_path,'score'),{**raw('score'),'score':score})
    assert result.decisions['local']['answer']==expected


def test_config_reuse_dispatch_temperature_language_and_invocation(tmp_path):
    block=make_block(tmp_path); loads=[]; predictions=[]
    class Agent:
        def __init__(self,key): self.key=key
        def predict(self,text,questions,**kwargs):
            predictions.append((self.key,kwargs));return {'answers':{'local':raw()}}
    def loader(model,**kwargs):
        loads.append((model,kwargs)); return Agent((model,kwargs))
    registry=AgentRegistry(loader=loader)
    a=RunConfig(model='A'); b=RunConfig(model='B',temperature=.2,lang='fr')
    for config in (a,b,a,RunConfig(model='A',temperature=.3)):
        block.run({'text':'x'},config=config,registry=registry)
    assert [x[0] for x in loads]==['A','B','A']
    assert loads[0][1]=={} and loads[1][1]=={'lang_temperatures':{'fr':{'temperature':[.2]*3}}}
    assert [x[0][0] for x in predictions]==['A','B','A','A']
    assert predictions[1][1]=={'lang':'fr'} and predictions[0][1]=={}
    block.run({'text':'x'},config=a,registry=AgentRegistry(loader=loader))
    assert len(loads)==4


def test_load_failure_not_cached_and_prediction_failure_not_retried(tmp_path):
    block=make_block(tmp_path); calls=[]
    def loader(*args,**kwargs): calls.append(1); raise RuntimeError('load')
    registry=AgentRegistry(loader=loader)
    for _ in range(2):
        with pytest.raises(RuntimeError,match='load'):
            block.run({'text':'x'},config=RunConfig(model='x'),registry=registry)
    assert len(calls)==2
    class Agent:
        def predict(self,*args,**kwargs): calls.append(2); raise TimeoutError('deadline')
    with pytest.raises(TimeoutError): block.run({'text':'x'},config=RunConfig(model='x'),registry=AgentRegistry(loader=lambda *a,**k:Agent()))
    assert calls==[1,1,2]


def test_mismatch_logs_structured_fields_and_no_preparation(tmp_path,monkeypatch):
    import laya_context_router.block_runtime.runtime as runtime
    logs=[]; monkeypatch.setattr(runtime,'log',lambda *args,**kwargs:logs.append((args,kwargs)))
    block=make_block(tmp_path,rules=[rule(),rule('noul',name='wrong')])
    block.prepare_input=lambda *_:pytest.fail('preparation must not execute')
    with pytest.raises(BlockConfigurationError): execute(block,rule_overrides={'local':'wrong'})
    event=next(fields for _,fields in logs if fields.get('code')=='rule_type_mismatch')
    assert event=={'block':'tiny','stage':'configuration','code':'rule_type_mismatch','question':'local','rule':'wrong','expected_type':'choice','actual_type':'noul'}


@pytest.mark.parametrize('value',[{},[],{'text':1},None])
def test_input_validation_cannot_be_bypassed_by_custom_preparer(tmp_path,value):
    block=make_block(tmp_path)
    with pytest.raises(BlockInputError):
        block.run(value,config=RunConfig(model='fake'),registry=AgentRegistry(loader=lambda *_:pytest.fail('loaded')),
            prepare_input=lambda *_:pytest.fail('prepared'))
