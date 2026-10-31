"""Explicit fixture preparation. Tests NEVER call this or download assets.

Use --source /path/to/tokenizer.json for a verified local copy, or --download
for the pinned public tokenizer (3.5 MB). No model weights are fetched.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--source', type=Path)
    group.add_argument('--download', action='store_true')
    args = parser.parse_args()
    spec = json.loads((ROOT / 'tests/fixtures/token-budget/manifest.json').read_text())['tokenizer']
    if args.source:
        data = args.source.read_bytes()
    else:
        with urlopen(spec['url'], timeout=60) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise SystemExit('Fixture hash mismatch; nothing installed')
    dest = ROOT / '.token-budget-fixtures/tokenizer.json'
    dest.parent.mkdir(exist_ok=True)
    dest.write_bytes(data)
    print(f'Verified pinned tokenizer: {dest}')


if __name__ == '__main__':
    main()
