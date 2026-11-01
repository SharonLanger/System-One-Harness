"""The reusable block contract survives wheel installation, not just a checkout."""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def test_both_block_resources_load_from_isolated_wheel(tmp_path):
    root = Path(__file__).resolve().parents[1]
    wheel_dir = tmp_path / "wheels"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-build-isolation", "--no-deps",
                    "--wheel-dir", str(wheel_dir), str(root)], check=True, capture_output=True, text=True)
    wheel, = wheel_dir.glob("*.whl")
    installed = tmp_path / "installed"
    relative = "building_blocks/questions"
    with zipfile.ZipFile(wheel) as archive:
        for name in ["ticket_triage", "method_selection"]:
            for filename in ["questions.json", "rules.json", "block.py", "README.md"]:
                member = f"{relative}/{name}/{filename}"
                assert archive.read(member) == (root / "src" / member).read_bytes()
        archive.extractall(installed)
    code = '''import json
from importlib.resources import files
from blocks import QuestionBlock
resources=files("building_blocks.questions")
print(json.dumps({name:list(QuestionBlock(resources / name).questions) for name in ["ticket_triage","method_selection"]}))
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path,
                            env={**os.environ, "PYTHONPATH": str(installed)}, check=True,
                            capture_output=True, text=True)
    assert json.loads(result.stdout) == {"ticket_triage": ["department", "churn_risk"],
                                        "method_selection": ["method", "multiple_relevant"]}
