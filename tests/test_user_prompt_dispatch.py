from types import SimpleNamespace
import pytest
from laya_context_router.hooks.contracts import Context, Noop, Failure
from laya_context_router.hooks.dispatcher import ingest_common, dispatch_hook
from laya_context_router.hooks.user_prompt_submit.dispatcher import dispatch_user_prompt_submit

ARGS=SimpleNamespace(hook='UserPromptSubmit',repository_root=None)
def event():return {'hook_event_name':'UserPromptSubmit','session_id':'s','transcript_path':'unused.jsonl','cwd':'/root','prompt':'  Explain `a.ts`: 😀\n'}
def call(p,output=Context('known')):
    calls=[];logs=[]
    def handler(request,logger):calls.append(request);return output
    result=dispatch_user_prompt_submit(ingest_common(p,'id'),ARGS,
        lambda *a,**k:logs.append((a,k)),handler=handler)
    return result,calls,logs

@pytest.mark.parametrize('value',[None,False,0,[],{}])
def test_wrong_prompt_type(value):
    p=event();p['prompt']=value
    result,calls,_=call(p)
    assert result==Failure('invalid_field','user_prompt_submit','prompt','user_prompt_submit: invalid_field (prompt)')
    assert not calls

def test_missing_prompt():
    p=event();del p['prompt']
    result,calls,_=call(p)
    assert result.code=='invalid_field' and result.field=='prompt' and not calls

@pytest.mark.parametrize('prompt',['', '  ', '  Explain `a.ts`: 😀\n'])
def test_prompt_preserved_and_one_handler(prompt):
    p=event();p['prompt']=prompt
    result,calls,logs=call(p,Noop('no_match'))
    assert result==Noop('no_match') and len(calls)==1
    assert calls[0].prompt==prompt and calls[0].config is ARGS
    assert calls[0].envelope.raw_payload==p
    assert [x[0][1] for x in logs]==['event_dispatcher_started','hook_input_ingested','feature_started','feature_finished','event_dispatcher_finished']
    assert all('prompt' not in x[1] for x in logs)

@pytest.mark.parametrize('output',[Context('known'),Noop('multiple_relevant'),Failure('model_error','feature')])
def test_outcome_propagates(output):
    result,calls,_=call(event(),output)
    assert result is output and len(calls)==1

@pytest.mark.parametrize('output',[None,{},Context(''),Context(1)])
def test_bad_handler_result(output):
    result,calls,_=call(event(),output)
    assert result.code=='invalid_result' and len(calls)==1

def test_exception_reaches_outer_boundary():
    def handler(*args):raise RuntimeError('planned')
    with pytest.raises(RuntimeError,match='planned'):
        dispatch_user_prompt_submit(ingest_common(event(),'id'),ARGS,lambda *a,**k:None,handler=handler)

def test_main_to_event_to_handler_and_extra_metadata():
    p=event();p['future']={'x':[1]};calls=[]
    def event_dispatch(e,a,l):
        return dispatch_user_prompt_submit(e,a,l,handler=lambda r,log:calls.append(r) or Context('known'))
    result=dispatch_hook(p,ARGS,'id',lambda *a,**k:None,
        dispatchers={'UserPromptSubmit':event_dispatch})
    assert result==Context('known') and len(calls)==1
    assert calls[0].envelope.raw_payload['future']=={'x':[1]}
    assert p['future']=={'x':[1]}


@pytest.mark.parametrize('output',[Context('known'),Noop('multiple_relevant'),Failure('model_error','feature')])
def test_feature_completion_metadata(output):
    records=[];ticks=iter([3.0,3.25])
    result=dispatch_user_prompt_submit(ingest_common(event(),'id'),ARGS,
        lambda l,e,**d:records.append((l,e,d)),handler=lambda *a:output,clock=lambda:next(ticks))
    final=next(d for l,e,d in records if e=='feature_finished')
    assert final['duration_seconds']==0.25
    assert final['outcome']==('context' if isinstance(output,Context) else ('noop' if isinstance(output,Noop) else 'error'))
    assert final['reason']==('multiple_relevant' if isinstance(output,Noop) else None)
    assert final['code']==('model_error' if isinstance(output,Failure) else None)

def test_unexpected_exception_has_completion_record():
    records=[]
    def handler(*a):raise RuntimeError('planned')
    with pytest.raises(RuntimeError):
        dispatch_user_prompt_submit(ingest_common(event(),'id'),ARGS,
            lambda l,e,**d:records.append((e,d)),handler=handler,clock=lambda:1.0)
    assert records[-1][0]=='event_dispatcher_finished'
    assert records[-1][1]['outcome']=='error' and records[-1][1]['code']=='dispatcher_exception'
