"""Read the existing log without creating or modifying it."""
from collections import deque
import sys


def run(last):
    from ..log_utils import LOG_PATH

    try:
        with LOG_PATH.open(encoding='utf-8') as stream:
            lines = deque(stream, maxlen=last)
    except FileNotFoundError:
        print(f'No log file yet: {LOG_PATH}', file=sys.stderr)
        return 0
    except (OSError, UnicodeError) as exc:
        print(f'Cannot read log file {LOG_PATH}: {exc}', file=sys.stderr)
        return 1
    sys.stdout.writelines(lines)
    return 0
