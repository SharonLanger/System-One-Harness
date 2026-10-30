import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('gateway_trace',Path(__file__).resolve().parents[1]/'experiments/hook_trace.py')
trace=importlib.util.module_from_spec(spec);spec.loader.exec_module(trace)

def record(event,**values):
    return {'pid':1,'component':'hook_gateway','event':event,'details':{'invocation_id':'now',**values}}

def details(records,stdout=''):
    return {'hook_pid':1,'trace':records,'stdout':stdout,'parsed_output':None}

def test_actual_stdout_is_the_payload_oracle():
    response={'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':'Known 😀'}}
    d=details([record('response_prepared',serialized_bytes=99)],json.dumps(response))
    text=trace.hook_output_sections(d)
    assert 'Returned by the hook subprocess' in text and 'Known 😀' in text
    assert 'Prepared payload content was not logged' in text

def test_prepared_metadata_does_not_prove_emission():
    d=details([record('response_prepared',serialized_bytes=99),
               record('gateway_finished',outcome='error',code='stdout_write_failed',stdout_bytes_written=None)])
    text=trace.hook_output_sections(d)
    assert 'partial delivery may have occurred' in text and '99' in text
    assert 'NOT SENT' not in text and 'Returned by the hook subprocess' not in text

def test_noop_empty_stdout_is_distinct_from_json_null():
    text=trace.hook_output_sections(details([record('gateway_finished',outcome='noop',reason='multiple_relevant',stdout_bytes_written=0)]))
    assert 'stdout was empty' in text and 'multiple_relevant' in text

def test_error_is_not_a_successful_noop():
    text=trace.hook_output_sections(details([record('gateway_finished',outcome='error',code='invalid_field',stdout_bytes_written=0)]))
    assert 'invalid_field' in text and 'outcome: **error**' in text

def test_historical_full_preparation_still_visible():
    r={'pid':1,'component':'hook','event':'response_prepared',
       'details':{'response':{'hookSpecificOutput':{'hookEventName':'UserPromptSubmit','additionalContext':'OLD'}}}}
    text=trace.hook_output_sections(details([r]))
    assert 'OLD' in text and 'delivery not confirmed' in text
    assert 'Returned by the hook subprocess' not in text

def test_unrelated_pid_and_stale_invocations_ignored():
    stale=record('response_prepared',response={'hookSpecificOutput':{'additionalContext':'STALE'}})
    stale['details']['invocation_id']='old'
    unrelated=record('gateway_finished',outcome='error',code='OTHER');unrelated['pid']=2
    d=details([stale,record('gateway_received'),record('gateway_finished',outcome='noop',reason='multiple_relevant',stdout_bytes_written=0),unrelated])
    text=trace.hook_output_sections(d)
    assert 'STALE' not in text and 'OTHER' not in text and 'multiple_relevant' in text

def test_stale_parsed_object_cannot_fake_returned_bytes():
    d=details([]);d['parsed_output']={'hookSpecificOutput':{'additionalContext':'FAKE'}}
    text=trace.hook_output_sections(d)
    assert 'FAKE' not in text and 'Returned by the hook subprocess' not in text

def test_actual_replay_runner_preserves_captured_noop_and_final_metadata(tmp_path,monkeypatch):
    import sys
    root=Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root/'experiments'))
    spec=importlib.util.spec_from_file_location('gateway_replay',root/'experiments/hook_user_prompt_submit.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    output=tmp_path/'report';output.mkdir()
    monkeypatch.setattr(module,'allocate_result_dir',lambda *a:output)
    event={'session_id':'replay-test','transcript_path':'not-existing.jsonl','cwd':str(root),
           'hook_event_name':'UserPromptSubmit','prompt':''}
    path=tmp_path/'input.json';path.write_text(json.dumps(event))
    assert module.main(['--input',str(path),'--deadline','5'])==0
    actual=json.loads((output/'details.json').read_text())
    assert actual['stdout']=='' and actual['parsed_output'] is None
    assert actual['observed_status']=='noop' and actual['application_outcome']['reason']=='ineligible_request'
    assert actual['laya_calls']==[]
    assert 'stdout was empty' in (output/'summary.md').read_text()
