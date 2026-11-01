"""The block's resources and executable wrapper survive wheel installation."""
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def test_task_completion_installed_wheel(tmp_path):
    root = Path(__file__).resolve().parents[1]
    wheels = tmp_path / 'wheels'
    subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-build-isolation',
                    '--no-deps', '--wheel-dir', str(wheels), str(root)],
                   check=True, capture_output=True, text=True)
    wheel, = wheels.glob('*.whl')
    installed = tmp_path / 'installed'
    with zipfile.ZipFile(wheel) as archive:
        for path in ('building_blocks/questions/task_completion/block.py',
                     'building_blocks/questions/task_completion/block.json',
                     'building_blocks/questions/task_completion/README.md',
                     'defaults/questions/task_completion.json',
                     'defaults/rules/task_completion_default.json'):
            source = root / 'src' / path
            assert archive.read('' + path) == source.read_bytes()
        archive.extractall(installed)
    code = '''
from block_runtime import Catalog
from building_blocks.questions.task_completion.block import run
from laya.config import RunConfig
from laya.registry import AgentRegistry
assert set(Catalog().question('task_completion')['criteria']) == {'yes', 'no'}
class Agent:
 def predict(self,text,questions,**kwargs):
  assert text=='All work done.' and set(questions)=={'task_completion'}
  return {'answers': {'task_completion': {'type':'choice','choice':'yes','probabilities':{'yes':.9,'no':.1},'answer_confidence':.9}}}
assert run({'response':'All work done.'},config=RunConfig(model='fake'),registry=AgentRegistry(loader=lambda *a,**k:Agent())).data == {'completion':'yes'}
'''
    subprocess.run([sys.executable, '-c', code], cwd=tmp_path,
                   env={**os.environ, 'PYTHONPATH':str(installed)},
                   check=True, capture_output=True, text=True)
