"""Compare two Laya configurations on the same saved questions."""
import argparse
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE.parent / "src") not in sys.path: sys.path.insert(0, str(HERE.parent / "src"))
from experiment_runner import execute

INPUT_PATH = HERE / "inputs" / "laya_compare_models.json"

def run(**kwargs): return execute("laya_compare_models", "Laya configuration comparison", kwargs.pop("input_path", INPUT_PATH), **kwargs)

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--model"); p.add_argument("--temperature", type=float); p.add_argument("--lang")
    p.add_argument("--compare-model"); p.add_argument("--compare-temperature", type=float); p.add_argument("--compare-lang"); a = p.parse_args(argv)
    return run(model=a.model, temperature=a.temperature, temperature_set=a.temperature is not None, lang=a.lang,
               compare_model=a.compare_model, compare_temperature=a.compare_temperature,
               compare_temperature_set=a.compare_temperature is not None, compare_lang=a.compare_lang)

if __name__ == "__main__": raise SystemExit(main())
