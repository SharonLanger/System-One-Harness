"""C19/C25–C34: scope-specific extension points and early contract failures."""
from copy import deepcopy
import pytest
from test_context_scope_block import LABELS, response, run, registry
from laya_context_router.block_runtime import Catalog, PreparedInput, SkipBlock
from laya_context_router.block_runtime.catalog import TypedRule
from laya_context_router.building_blocks.questions.context_scope import block

class OverrideCatalog(Catalog):
    def question(self,name):
        if name=='scope_alt':
            value=super().question('context_scope');value['instructions']='Alternate scope wording.';return value
        return super().question(name)
    def rule(self,name):
        if name in ('loose','strict'):
            return TypedRule.from_dict({'name':name,'question_type':'choice','conditions':[
                {'field':'answer_confidence','op':'gte','value':0 if name=='loose' else .99}]})
        return super().rule(name)

def test_C19_C25_C26_C27_C34_overrides_and_defaults():
    catalog=OverrideCatalog();question=catalog.question('context_scope');before=deepcopy(question)
    raw=response();question['instructions']='Complete override.'
    calls=[]
    assert run(raw=raw,calls=calls,catalog=catalog,question_overrides={'context_scope':question},
               rule_overrides={'context_scope':'loose'}).data['scope']=='method_only'
    assert calls[0][1]['context_scope']['instructions']=='Complete override.'
    assert run(raw=raw,catalog=catalog,rule_overrides={'context_scope':'strict'}).data['scope']=='undecided'
    calls=[];run(calls=calls,catalog=catalog,question_overrides={'context_scope':'scope_alt'})
    assert calls[0][1]['context_scope']['instructions']=='Alternate scope wording.'
    calls=[];run(calls=calls,catalog=catalog)
    assert calls[0][1]['context_scope']==before
    assert question['instructions']=='Complete override.'

@pytest.mark.parametrize('change',['type','rule_type','add','remove','rename','unknown_rule','unknown_question','unknown_key','malformed'])
def test_C28_C29_C30_early_override_failures(change):
    q=Catalog().question('context_scope');kwargs={};loads=[]
    if change=='type':q={'type':'noul','instructions':'true?'}
    elif change=='rule_type':kwargs['rule_overrides']={'context_scope':'multiple_methods_default'}
    elif change=='add':q['criteria']['other']='Other'
    elif change=='remove':q['criteria'].pop('method_only')
    elif change=='rename':q['criteria']['renamed']=q['criteria'].pop('method_only')
    elif change=='unknown_rule':kwargs['rule_overrides']={'context_scope':'missing'}
    elif change=='unknown_question':kwargs['question_overrides']={'context_scope':'missing'}
    elif change=='unknown_key':kwargs['question_overrides']={'other':q}
    elif change=='malformed':q['criteria']=None
    kwargs.setdefault('question_overrides',{'context_scope':q})
    with pytest.raises(ValueError):run(loads=loads,**kwargs)
    assert loads==[]

def test_C12_criteria_order():
    q=Catalog().question('context_scope');q['criteria']=dict(reversed(list(q['criteria'].items())))
    assert run(raw=response('calling_methods'),question_overrides={'context_scope':q}).data['scope']=='calling_methods'

def test_C31_custom_preparation():
    original={'prompt':'original'};seen=[];calls=[]
    def custom(value,questions):
        seen.append(deepcopy(value));value['prompt']='mutated'
        questions['context_scope']['instructions']='Custom wording.'
        return PreparedInput('custom text',questions,{'ignored':'state'})
    result=run(original,calls=calls,prepare_input=custom)
    assert result.data=={'scope':'method_only'} and original=={'prompt':'original'}
    assert seen==[original] and calls[0][0]=='custom text'

@pytest.mark.parametrize('change',['blank','names','type','labels','bad_result'])
def test_C32_bad_preparation(change):
    loads=[]
    def custom(value,questions):
        text='custom'
        if change=='blank':text=' \n'
        if change=='names':questions={'wrong':questions['context_scope']}
        if change=='type':questions['context_scope']={'type':'noul','instructions':'true?'}
        if change=='labels':questions['context_scope']['criteria'].pop('method_only')
        if change=='bad_result':return None
        return PreparedInput(text,questions)
    with pytest.raises(ValueError):run(loads=loads,prepare_input=custom)
    assert loads==[]

def test_C33_skip():
    loads=[]
    def custom(value,questions):raise SkipBlock('caller_skip')
    result=run(loads=loads,prepare_input=custom)
    assert result.status=='skipped' and result.reason=='caller_skip'
    assert result.decisions=={} and result.data=={'scope':'undecided'} and loads==[]
