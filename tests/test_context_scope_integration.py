"""C09/C35–C40: actual registry, logs, caller composition and wheel resources."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
import pytest
from test_context_scope_block import LABELS, response, registry, run
from building_blocks.questions.context_scope import block
from laya.config import RunConfig
from laya.registry import AgentRegistry

def test_C09_no_retrieval(monkeypatch):
    import building_blocks.typescript as ts
    def forbidden(*args,**kwargs):raise AssertionError('No retrieval allowed')
    for name in ('outline','extract_callable','collect_local_context','collect_project_context'):
        monkeypatch.setattr(ts,name,forbidden)
    monkeypatch.setattr(subprocess,'run',forbidden)
    assert run({'prompt':'Explain /missing/project/method.ts'}).data['scope']=='method_only'

def test_C35_C36_registry_reuse_and_identity():
    loads=[];calls=[];shared=registry(calls=calls,loads=loads)
    configs=[RunConfig(model='A'),RunConfig(model='A'),RunConfig(model='B'),
             RunConfig(model='A',temperature=.2),RunConfig(model='A',temperature=.2,lang='he')]
    for config in configs:block.run({'prompt':'x'},config=config,registry=shared)
    assert len(loads)==4 and len(calls)==5
    assert loads[0]==(('A',),{}) and loads[1]==(('B',),{})
    assert loads[2][1]=={'lang_temperatures':{'en':{'temperature':[.2]*3}}}
    assert loads[3][1]=={'lang_temperatures':{'he':{'temperature':[.2]*3}}}
    assert calls[-1][2]=={'lang':'he'}
    block.run({'prompt':'x'},config=configs[0],registry=registry(loads=loads))
    assert len(loads)==5

def test_C23_C36_failed_load_not_cached():
    attempts=[]
    def loader(*args,**kwargs):attempts.append(1);raise RuntimeError('load failed')
    shared=AgentRegistry(loader=loader)
    for _ in range(2):
        with pytest.raises(RuntimeError,match='load failed'):
            block.run({'prompt':'x'},config=RunConfig(),registry=shared)
    assert len(attempts)==2

def test_C28_C37_actual_logs(tmp_path,monkeypatch):
    import log_utils as logs
    path=tmp_path/'logs.jsonl';monkeypatch.setattr(logs,'LOG_PATH',path)
    run({'prompt':'Where used?','requested_action':'explain'})
    with pytest.raises(ValueError):run(rule_overrides={'context_scope':'multiple_methods_default'})
    records=[json.loads(line) for line in path.read_text().splitlines()]
    def event(component,name):return next(r['details'] for r in records if r['component']==component and r['event']==name)
    submitted=event('laya','prediction_started')
    assert json.loads(submitted['text'])=={'prompt':'Where used?','requested_action':'explain'}
    assert set(submitted['questions'])=={'context_scope'}
    assert event('laya','response_received')['response']==response()
    enriched=event('enrichment','completed')
    assert enriched['block']=='context_scope' and enriched['enriched']['probability_gap']==.7
    assert event('block_runtime','configured')['rules']['context_scope']['name']=='context_scope_default'
    assert event('block_runtime','completed')['decisions']['context_scope']['answer']=='method_only'
    assert any(r['level']=='ERROR' and r['details'].get('code')=='rule_type_mismatch' for r in records)

def test_C38_C39_caller_composition():
    destinations={scope:f'use_{scope}' for scope in LABELS};destinations['undecided']='normal_path'
    seen=[]
    for label in LABELS:
        for action in ('explain','undecided'):
            value={'prompt':'request','requested_action':action};calls=[]
            result=run(value,raw=response(label),calls=calls)
            seen.append(destinations[result.data['scope']])
            if action=='undecided':assert calls[0][0]=='request'
            else:assert json.loads(calls[0][0])==value
    raw=response(probs=dict(zip(LABELS,(.3,.3,.2,.2))))
    assert destinations[run(raw=raw).data['scope']]=='normal_path'
    assert set(seen)=={f'use_{scope}' for scope in LABELS}

def test_C40_installed_wheel_resources_and_execution(tmp_path):
    root=Path(__file__).resolve().parents[1];wheels=tmp_path/'wheels'
    subprocess.run([sys.executable,'-m','pip','wheel','--no-build-isolation','--no-deps',
                    '--wheel-dir',str(wheels),str(root)],check=True,capture_output=True,text=True)
    wheel,=wheels.glob('*.whl');installed=tmp_path/'installed'
    with zipfile.ZipFile(wheel) as archive:
        for path in ['defaults/questions/context_scope.json','defaults/rules/context_scope_default.json',
                     'building_blocks/questions/context_scope/block.json','building_blocks/questions/context_scope/README.md']:
            assert archive.read(''+path)==(root/'src'/path).read_bytes()
    code='''
import pathlib
import building_blocks
from building_blocks.questions.context_scope.block import run
from laya.registry import AgentRegistry
from laya.config import RunConfig
class Fake:
 def predict(self,text,questions,**kwargs):
  assert text=='Explain it' and set(questions)=={'context_scope'}
  return {'answers':{'context_scope':{'type':'choice','choice':'method_only','answer_confidence':.8,'probabilities':{'method_only':.8,'called_methods':.1,'calling_methods':.06,'both_directions':.04}}}}
result=run({'prompt':'Explain it'},config=RunConfig(model='fake'),registry=AgentRegistry(loader=lambda *a,**k:Fake()))
assert result.data=={'scope':'method_only'}
assert 'site-packages' in str(pathlib.Path(building_blocks.__file__))
print('scope wheel passed')
'''
    environment=tmp_path/'venv'
    subprocess.run([sys.executable,'-m','venv',str(environment)],check=True,capture_output=True,text=True)
    python=environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    env={key:value for key,value in os.environ.items() if key not in {'PYTHONPATH','PYTHONHOME'}}
    subprocess.run([str(python),'-m','pip','install','--no-deps',str(wheel)],
        cwd=tmp_path,env=env,check=True,capture_output=True,text=True)
    outcome=subprocess.run([str(python),'-c',code],cwd=tmp_path,
        env=env,check=True,capture_output=True,text=True)
    assert outcome.stdout.strip()=='scope wheel passed'
