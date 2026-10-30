"""Run the existing file-method flow on a multi-file TypeScript fixture."""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from flow_method_context import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, help='alternate saved JSON prompt/config input')
    args = parser.parse_args()
    return run(args.input.resolve() if args.input else HERE / 'inputs/flow_connected_project.json',
               'flow_connected_project',
               script_name=Path(__file__).name)


if __name__ == '__main__':
    raise SystemExit(main())
