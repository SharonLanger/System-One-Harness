"""New defaults and runtime execute from wheel resources outside the checkout."""
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def test_new_catalog_and_mocked_block_execute_from_isolated_wheel(tmp_path):
    root=Path(__file__).resolve().parents[2]
    wheels=tmp_path/'wheels'
    subprocess.run([sys.executable,'-m','pip','wheel','--no-build-isolation','--no-deps','--wheel-dir',str(wheels),str(root)],check=True,capture_output=True,text=True)
    wheel,=wheels.glob('*.whl');installed=tmp_path/'installed'
    with zipfile.ZipFile(wheel) as archive:
        for directory in ['defaults/rules','defaults/questions','block_runtime','building_blocks/questions/ticket_triage_v2','building_blocks/questions/method_selection_v2']:
            for source in (root/'src/laya_context_router'/directory).iterdir():
                if source.suffix in {'.json','.py','.md'}:
                    assert archive.read(f'laya_context_router/{directory}/{source.name}')==source.read_bytes()
        archive.extractall(installed)
    code='''
from laya_context_router.block_runtime import Catalog, Block, PreparedInput
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
assert Catalog().rule('multiple_methods_default').question_type=='noul'
class Agent:
 def predict(self,text,questions,**kwargs):
  assert text=='hello' and set(questions)=={'local'}
  return {'answers':{'local':{'type':'noul','noul':.8,'answer_confidence':.9}}}
block=Block({'name':'installed','questions':{'local':{'question_ref':'multiple_relevant','rule_ref':'multiple_methods_default'}}},validate_input=lambda x:x,prepare_input=lambda x,q:PreparedInput(x['text'],q),reduce=lambda d,s:d,validate_output=lambda x:x)
result=block.run({'text':'hello'},config=RunConfig(model='mock'),registry=AgentRegistry(loader=lambda *a,**k:Agent()))
assert result.decisions['local']['answer']=='yes'
print('installed runtime passed')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=tmp_path,env={**os.environ,'PYTHONPATH':str(installed)},check=True,capture_output=True,text=True)
    assert result.stdout.strip()=='installed runtime passed'
