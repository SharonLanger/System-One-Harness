"""Disposable Bash/Python hook scenario; fake SDK only, no Claude activation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from laya_context_router.blocks import QuestionBlock
from laya_context_router.building_blocks.questions.method_selection.block import BLOCK_DIR
from laya_context_router.building_blocks.typescript import outline

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='laya-hook-scenario-') as temporary:
        root = Path(temporary)
        source = root/'main.ts'
        source.write_text('export function greet(name: string) { return "Hello " + name; }')
        original = source.read_bytes()
        data = outline(source)
        selected = data['callables'][0]['name']  # Explicit fixture choice, not inference.
        block = QuestionBlock(BLOCK_DIR)
        questions = {name: question.to_predict_dict() for name, question in block.questions.items()}
        questions['method']['criteria'] = {
            selected: data['callables'][0]['signature'],
            'none_or_unclear': questions['method']['criteria']['none_or_unclear']}
        prompt = 'Explain `main.ts`: how does greet work?'
        spec = root/'spec.json'
        spec.write_text(json.dumps({'prompt': prompt, 'questions': questions, 'raw': {'answers': {
            'method': {'type': 'choice', 'choice': selected, 'answer_confidence': .95,
                       'probabilities': {selected: .95, 'none_or_unclear': .05}},
            'multiple_relevant': {'type': 'noul', 'noul': .1, 'answer_confidence': .95}}}}))
        # This child-only module replaces exactly the external SDK boundary.
        (root/'sitecustomize.py').write_text('''import json, os, sys, types
spec=json.load(open(os.environ['LAYA_SCENARIO_SPEC']))
class Agent:
    def predict(self,text,questions,**kwargs):
        assert (text,questions,kwargs)==(spec['prompt'],spec['questions'],{})
        print('Explicitly simulated SDK boundary; no model loaded')
        return spec['raw']
def load(model,**kwargs):
    assert model=='mock-scenario' and kwargs=={}
    return Agent()
sys.modules['laya_mlx']=types.SimpleNamespace(load=load)
''')
        config = root/'config.json'
        config.write_text(json.dumps({'model': 'mock-scenario'}))
        event = {'session_id': 'synthetic-scenario', 'transcript_path': 'unused.jsonl',
                 'permission_mode': 'default', 'hook_event_name': 'UserPromptSubmit',
                 'cwd': str(root), 'prompt': prompt}
        result = subprocess.run(['bash', '-c', 'exec "$@"', 'laya-hook', sys.executable,
            str(ROOT/'hooks/user_prompt_submit.py'), '--repository-root', str(root),
            '--config', str(config), '--real'], input=json.dumps(event), text=True,
            capture_output=True, timeout=15, env={**os.environ,
                'PYTHONPATH': os.pathsep.join([str(root), str(ROOT/'src')]),
                'LAYA_SCENARIO_SPEC': str(spec)})
        if result.returncode or not result.stdout:
            raise RuntimeError(f'scenario failed: {result.stderr}')
        output = json.loads(result.stdout)
        assert set(output) == {'hookSpecificOutput'}
        assert source.read_bytes() == original and not (root/'.claude').exists()
        sys.stderr.write(result.stderr)
        sys.stdout.write(result.stdout)


if __name__ == '__main__':
    main()
