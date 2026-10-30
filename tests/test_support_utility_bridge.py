import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from laya_context_router.building_blocks import typescript as ts


def test_call_list_round_trip_with_extractable_target(tmp_path):
    p = tmp_path / 'main.ts'
    p.write_text('function helper(){return 1;} function selected(){return helper();}')
    (tmp_path / 'tsconfig.json').write_text('{"compilerOptions":{"module":"commonjs"}}')
    selected = ts.outline(p)['callables'][1]
    result = ts.list_called_callables(p, selected['id'], repository_root=tmp_path)
    assert result['status'] == 'ok'
    target = result['data']['calls'][0]
    assert ts.extract_callable(target['path'], target['id'])['code'] == 'function helper(){return 1;}'
    assert ts.list_called_callables(p, 'stale', repository_root=tmp_path)['status'] == 'error'


@pytest.mark.parametrize('payload', [
    {'status':'ok','data':{'calls':[{'path':'relative.ts','id':'bad','name':'x','signature':'x()'}]},'diagnostics':[]},
    {'status':'ok','data':{'calls':[]},'diagnostics':[{'code':3,'message':'bad'}]},
    {'status':'error','data':{'calls':[]},'diagnostics':[]},
    {'status':'partial','data':{'calls':[]},'diagnostics':[]},
])
def test_call_list_rejects_invalid_protocol(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(ts.subprocess, 'run', lambda *args,**kwargs: SimpleNamespace(returncode=0,stdout=json.dumps(payload),stderr=''))
    with pytest.raises(ts.TypeScriptError,match='schema'):
        ts.list_called_callables(tmp_path/'main.ts','id',repository_root=tmp_path)


def test_new_envelopes_use_bounded_transport_timeout(tmp_path, monkeypatch):
    def expired(*args,**kwargs):
        assert kwargs['timeout'] == .1
        request=json.loads(kwargs['input'])
        assert request['action']=='detect_references' and 'path' not in request
        raise ts.subprocess.TimeoutExpired(args[0],.1)
    monkeypatch.setattr(ts.subprocess,'run',expired)
    with pytest.raises(ts.TypeScriptError,match='timed out'):
        ts.detect_references('main.ts',timeout=.1)
