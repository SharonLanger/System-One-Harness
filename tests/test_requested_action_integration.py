"""New-block log, resource and caller integration without real SDK inference."""
from examples._plumbing_inspection import PLUMBING_SOURCE
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from unittest.mock import Mock
import pytest
from test_requested_action_block import Harness, response
from laya_context_router.block_runtime import BlockInputError, BlockConfigurationError


def test_T41_T42_logs(tmp_path,monkeypatch):
    from laya_context_router import log_utils
    path=tmp_path/'debug.jsonl';monkeypatch.setattr(log_utils,'LOG_PATH',path)
    h=Harness();h.run()
    events=[json.loads(l) for l in path.read_text().splitlines()]
    def event(component,name):return next(e['details'] for e in events if e['component']==component and e['event']==name)
    assert event('block_runtime','configured')['rules']['requested_action']['name']=='requested_action_default'
    assert event('block_runtime','prepared')['block']=='requested_action'
    assert set(event('block_runtime','prepared')['questions'])=={'requested_action'}
    assert event('laya','response_received')['response']==response()
    assert event('enrichment','completed')['enriched']['probability_gap']==.65
    assert event('block_runtime','completed')['decisions']['requested_action']['answer']=='explain'
    path.unlink();h=Harness()
    with pytest.raises(BlockInputError):h.run({'prompt':''})
    with pytest.raises(BlockConfigurationError):h.run(rule_overrides={'requested_action':'multiple_methods_default'})
    events=[json.loads(l) for l in path.read_text().splitlines()]
    codes={e['details'].get('code') for e in events}
    assert {'invalid_input','rule_type_mismatch'}<=codes
    assert not any(e['event']=='prediction_started' for e in events)
    assert not h.loads


def test_T44_no_target_reads_or_utilities(tmp_path,monkeypatch):
    from laya_context_router.building_blocks import typescript
    for name in ('outline','extract_callable'):
        monkeypatch.setattr(typescript,name,Mock(side_effect=AssertionError('TypeScript called')))
    monkeypatch.setattr(subprocess,'run',Mock(side_effect=AssertionError('subprocess called')))
    monkeypatch.setattr(subprocess,'Popen',Mock(side_effect=AssertionError('subprocess called')))
    import builtins
    actual=builtins.open
    target=tmp_path/'target.ts';target.write_text('SECRET')
    def guarded(file,*a,**k):
        if isinstance(file,(str,os.PathLike)) and Path(file)==target:raise AssertionError('target read')
        return actual(file,*a,**k)
    monkeypatch.setattr(builtins,'open',guarded)
    io_open=__import__('io').open
    def guarded_io(file,*a,**k):
        if isinstance(file,(str,os.PathLike)) and Path(file)==target:raise AssertionError('target read')
        return io_open(file,*a,**k)
    monkeypatch.setattr(__import__('io'),'open',guarded_io)
    assert Harness().run({'prompt':f'Explain {target}'}).data=={'action':'explain'}


def test_T45_installed_wheel(tmp_path):
    root=Path(__file__).resolve().parents[1];wheels=tmp_path/'wheels'
    subprocess.run([sys.executable,'-m','pip','wheel','--no-build-isolation','--no-deps','--wheel-dir',str(wheels),str(root)],check=True,capture_output=True,text=True)
    wheel,=wheels.glob('*.whl');installed=tmp_path/'installed'
    with zipfile.ZipFile(wheel) as archive:
        for directory in ['defaults/questions','defaults/rules','building_blocks/questions/requested_action']:
            for p in (root/'src/laya_context_router'/directory).iterdir():
                if p.suffix in {'.json','.md','.py'}:assert archive.read(f'laya_context_router/{directory}/{p.name}')==p.read_bytes()
        archive.extractall(installed)
    raw=json.dumps(response())
    code=PLUMBING_SOURCE+f'''
import laya_context_router
from pathlib import Path
assert Path(laya_context_router.__file__).is_relative_to({str(installed)!r})
from laya_context_router.building_blocks.questions.requested_action.block import run
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
class Fake:
 def predict(self,text,questions,**kwargs):
  assert text=='outside checkout'
  return {raw}
r=run({{'prompt':'outside checkout'}},config=RunConfig(model='synthetic'),registry=AgentRegistry(inspection_provider=plumbing_provider, loader=lambda *a,**k:Fake()))
assert r.data=={{'action':'explain'}}
print('installed requested_action passed')
'''
    environment={**os.environ,'PYTHONPATH':str(installed),'PYTHONNOUSERSITE':'1'}
    r=subprocess.run([sys.executable,'-s','-c',code],cwd=tmp_path,env=environment,check=True,capture_output=True,text=True)
    assert r.stdout.strip()=='installed requested_action passed'


def test_semantic_corpus_is_separate_and_pending_cases_unscored():
    corpus=json.loads((Path(__file__).parent/'fixtures/requested_action_prompts.json').read_text())
    assert corpus['live_evaluated'] is False
    cases=corpus['cases'];assert {c['id'] for c in cases}=={f'E{i:02}' for i in range(1,23)}
    assert any(c['split']=='held_out' for c in cases)
    for c in cases:
        assert c['status'] in {'settled','provisional','taxonomy_pending'}
        if c['status']!='settled':assert c['score_accuracy'] is False


def test_T08_T44_fresh_import_and_block_construction(tmp_path):
    root=Path(__file__).resolve().parents[1]
    code=PLUMBING_SOURCE+'''
import subprocess
from unittest.mock import Mock
from laya_context_router.laya import predict as sdk
sdk.real_loader=Mock(side_effect=AssertionError('model loaded at import/construction'))
subprocess.run=Mock(side_effect=AssertionError('subprocess at import/construction'))
subprocess.Popen=Mock(side_effect=AssertionError('subprocess at import/construction'))
from laya_context_router.building_blocks import typescript
for name in ('outline','extract_callable'):
 setattr(typescript,name,Mock(side_effect=AssertionError('TypeScript at import/construction')))
from laya_context_router.building_blocks.questions.requested_action import block
from laya_context_router.block_runtime import Block
b=Block(block.BLOCK_DIR/'block.json',validate_input=block.validate_input,
 prepare_input=block.prepare,reduce=block.reduce,validate_output=block.validate_output,
 validate_prepared=block.validate_prepared)
assert b.name=='requested_action'
sdk.real_loader.assert_not_called()
print('lazy import and construction passed')
'''
    r=subprocess.run([sys.executable,'-s','-c',code],cwd=tmp_path,
        env={**os.environ,'PYTHONPATH':str(root/'src')},capture_output=True,text=True,check=True)
    assert r.stdout.strip()=='lazy import and construction passed'


def test_T43_caller_branches_all_results():
    routes={'explain':'understand','generate_tests':'create-tests','modify_code':'change-code','undecided':'normal'}
    observed=[]
    for raw in (response('explain'),response('generate_tests'),response('modify_code'),response(probs=(.5,.5,0),confidence=.5)):
        result=Harness(raw).run()
        observed.append(routes[result.data['action']])
    assert observed==['understand','create-tests','change-code','normal']
