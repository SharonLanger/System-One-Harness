"""Readable, atomically allocated result directories, matching the original batch runner."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def allocate(parent):
    stamp = datetime.now(ZoneInfo('Asia/Jerusalem')).strftime('%Y-%m-%d_%H-%M-%S')
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    for index in range(10000):
        path = parent / (stamp if not index else f'{stamp}_{index:03}')
        try:
            path.mkdir()
            return path
        except FileExistsError:
            pass
    raise RuntimeError('too many timestamp collisions')
