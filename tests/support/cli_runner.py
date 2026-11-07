"""Test-only launcher: real CLI/gateway, real blocks, scripted SDK, temporary state."""
import functools
import json
import os
from pathlib import Path
import runpy
import sys

from tests.support.fake_laya import ScriptedLaya
from tests.support.offline_scenarios import scenario_steps


def main():
    entry, scenario, project, state, *args = sys.argv[1:]
    project, state = Path(project), Path(state)
    if not state.is_absolute():
        raise ValueError('state must be an absolute temporary path')
    fake = ScriptedLaya(*scenario_steps(scenario, project / 'sample.ts'))
    from laya import registry, predict
    registry.real_loader = predict.real_loader = fake.load
    from hooks import session_state
    session_state.save_event = functools.partial(session_state.save_event, logs_root=state)
    session_state.inspect_and_save_event = functools.partial(session_state.inspect_and_save_event, logs_root=state)
    import log_utils
    records = []
    # Only file persistence crosses a real storage boundary. Diagnostics stay in memory.
    with log_utils.capture_records(records.append):
        if scenario == 'noise':
            original = fake.predict
            def noisy(*a, **kw):
                print('scripted SDK stdout noise')
                os.write(1, b'scripted SDK fd noise\n')
                return original(*a, **kw)
            fake.predict = noisy
        sys.argv = [entry, *(['hook'] if entry == 'cli' else []), *args]
        try:
            runpy.run_module('cli' if entry == 'cli' else 'hooks.gateway', run_name='__main__')
        except SystemExit as exc:
            code = exc.code
        else:
            code = 0
    fake.assert_complete()
    print('TEST_EVIDENCE:' + json.dumps({'calls': len(fake.calls), 'records': records}, default=str), file=sys.stderr)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
