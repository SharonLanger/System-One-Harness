from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import pytest
from laya_context_router.hooks.contracts import Context,Noop,Failure
from laya_context_router.hooks.dispatcher import dispatch_hook,enrich_envelope

ARGS=SimpleNamespace(hook='UserPromptSubmit')
def payload():
    return {'hook_event_name':'UserPromptSubmit','session_id':'s','transcript_path':'unused.jsonl','cwd':'/project','prompt':'x'}
def invoke(p,**kwargs):
    calls=[];records=[]
    def handler(e,a,l):calls.append(e);return Context('fixed')
    result=dispatch_hook(p,ARGS,'invocation',lambda *a,**k:records.append((a,k)),
                         dispatchers={'UserPromptSubmit':handler},**kwargs)
    return result,calls,records

@pytest.mark.parametrize('key',['session_id','cwd','hook_event_name','transcript_path'])
@pytest.mark.parametrize('value',[None,False,1,[],{},'', ' '])
def test_invalid_common(key,value):
    p=payload();p[key]=value
    result,calls,_=invoke(p)
    assert isinstance(result,Failure) and result.field==key and not calls

@pytest.mark.parametrize('key',['session_id','cwd','hook_event_name','transcript_path'])
def test_missing_common(key):
    p=payload();del p[key]
    result,calls,_=invoke(p)
    assert isinstance(result,Failure) and result.field==key and not calls

@pytest.mark.parametrize('key',['permission_mode'])
@pytest.mark.parametrize('value',[None,False,4,[],{},'', ' '])
def test_invalid_optional_when_present(key,value):
    p=payload();p[key]=value
    result,calls,_=invoke(p)
    assert isinstance(result,Failure) and result.field==key and not calls

def test_relative_cwd_rejected():
    p=payload();p['cwd']='relative'
    result,calls,_=invoke(p)
    assert isinstance(result,Failure) and not calls

def test_metadata_forward_compatibility_and_immutability():
    p=payload();p.update(transcript_path='not-existing.jsonl',permission_mode='future-mode',extra={'x':[1]})
    original=deepcopy(p)
    result,calls,records=invoke(p)
    assert result==Context('fixed') and len(calls)==1
    assert p==original and calls[0].raw_payload==p
    assert calls[0].common['permission_mode']=='future-mode'
    assert calls[0].derived=={} and enrich_envelope(calls[0]) is calls[0]
    assert records[0][1]['session_id']=='s'
    calls[0].raw_payload['extra']['x'].append(2)
    assert p==original

def test_unknown_requires_no_feature_metadata():
    result=dispatch_hook({'hook_event_name':'Unknown'},SimpleNamespace(hook='Unknown'),'id',lambda *a,**k:None)
    assert result==Noop('unsupported_event')

def test_mismatched_names_do_not_dispatch():
    p=payload();p['hook_event_name']='Stop'
    result,calls,_=invoke(p)
    assert result.code=='event_mismatch' and not calls

@pytest.mark.parametrize('change',[{'common':{}},{'raw_payload':{}},{'hook_name':'Stop'},
    {'invocation_id':'changed'},{'derived':{'project_root':'/other'}},{'derived':None}])
def test_invalid_enrichment_cannot_change_sources(change):
    result,calls,_=invoke(payload(),enricher=lambda e:replace(e,**change))
    assert result.code=='invalid_enrichment' and not calls

def test_invocations_do_not_share_derived_state():
    _,first,_=invoke(payload());_,second,_=invoke(payload())
    first[0].derived['x']=1
    assert second[0].derived=={}

def test_input_order_and_one_dispatch():
    events=[]
    def seam(e):events.append('seam');return e
    def handler(e,a,l):events.append('handler');return Noop('multiple_relevant')
    result=dispatch_hook(payload(),ARGS,'id',lambda level,event,**k:events.append(event),
                         dispatchers={'UserPromptSubmit':handler},enricher=seam)
    assert result==Noop('multiple_relevant') and events==['hook_dispatcher_started','seam','common_input_validated',
        'hook_dispatcher_routed','handler','hook_dispatcher_finished']
