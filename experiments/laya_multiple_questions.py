"""Send multiple named questions in one direct Laya adapter call."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE.parent / "src") not in sys.path: sys.path.insert(0, str(HERE.parent / "src"))
from experiment_runner import execute

INPUT_PATH = HERE / "inputs" / "laya_multiple_questions.json"

def run(**kwargs): return execute("laya_multiple_questions", "Laya multiple questions", kwargs.pop("input_path", INPUT_PATH), **kwargs)

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--model"); p.add_argument("--temperature", type=float); p.add_argument("--lang"); a = p.parse_args(argv)
    return run(model=a.model, temperature=a.temperature, temperature_set=a.temperature is not None, lang=a.lang)

if __name__ == "__main__": raise SystemExit(main())
