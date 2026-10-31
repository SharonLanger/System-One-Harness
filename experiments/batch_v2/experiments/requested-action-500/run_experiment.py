"""Start the first requested-action experiment; no production changes or package installs."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BATCH = HERE.parents[1]
sys.path.insert(0, str(BATCH))
from schema import load, validate, vectors
from research.protocol import validate_protocol
from run_paths import allocate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Validate frozen files and print counts; no model calls.')
    parser.add_argument('--report-run', type=Path, help='Rebuild the development-only report for an existing run; no model calls.')
    args = parser.parse_args(argv)
    cases = load(HERE / 'cases.json')
    suite = load(HERE / 'rounds/001-broad/suite.json')
    roles = load(HERE / 'calibration_roles.json')
    protocol = load(HERE / 'protocol.json')
    validate(cases, suite)
    validate_protocol(protocol, cases, roles, cases_path=HERE / 'cases.json')
    if args.report_run:
        from screening_report import write_screening_report
        path = write_screening_report(args.report_run.resolve(), roles, protocol)
        print('Development report: ' + str(path), flush=True)
        return 0
    count = len(cases['cases'])
    calls = count * len(suite['questions']) * len(suite['configurations'])
    print(json.dumps({'cases': count, 'question_variants': len(suite['questions']), 'rules': len(suite['rules']),
                      'temperature_settings': [c['temperature'] for c in suite['configurations']],
                      'inference_calls': calls, 'logical_rule_outcomes': count * len(vectors(suite)),
                      'interface_probe_calls': len(suite['configurations']), 'rule_mode': 'replay'}, indent=2), flush=True)
    if args.dry_run:
        return 0
    if platform.system() != 'Darwin':
        raise ValueError('Live LAYA execution requires your Mac with the existing SDK and cached model. Use --dry-run here.')

    # Probe only the established fruit example, so held-out campaign cases are not used
    # for setup decisions. Use a subprocess to release its cached models before the batch.
    probe_path = allocate(BATCH / 'results' / suite['experiment_id'] / 'probes') / 'probe.json'
    temperatures = [c['temperature'] for c in suite['configurations']]
    probe_command = [sys.executable, '-B', '-m', 'research.probe', '--cases', str(BATCH / 'examples/generic-choice/cases.json'),
                     '--suite', str(BATCH / 'examples/generic-choice/suite.json'), '--temperatures', json.dumps(temperatures),
                     '--max-calls', str(len(temperatures)), '--output', str(probe_path), '--allow-live']
    print('Checking the installed SDK temperature interface...', flush=True)
    subprocess.run(probe_command, cwd=BATCH, check=True)
    probe = load(probe_path)
    if probe.get('unsupported') or probe.get('supported_temperatures') != temperatures:
        raise ValueError('The full requested grid is not supported. Keep the probe evidence and revise a new round explicitly: ' + str(probe_path))

    from engine import create, run, save
    root = create(cases, suite, 'live', 'replay', {'max_calls': calls, 'max_seconds': None, 'worker_timeout': None})
    save(root / 'campaign-launch.json', {'round': '001-broad', 'protocol': protocol, 'probe_file': str(probe_path),
                                        'probe': probe, 'launcher': str(Path(__file__).resolve()), 'repeat_policy': 'new run, never overwrite'})
    print('Run folder: ' + str(root), flush=True)
    print('All requests are frozen. Each later launch creates a new run. Model and report work may take time.', flush=True)
    result = run(root)
    manifest = load(root / 'manifest.json')
    if result != 0 or manifest['status'] != 'completed':
        print('Run is incomplete. Preserve its folder; do not select a winner. Resume with:\n'
              + sys.executable + ' -B ' + str(BATCH / 'run.py') + ' --resume ' + str(root), flush=True)
        return result or 1
    from screening_report import write_screening_report
    report = write_screening_report(root, roles, protocol)
    print('Open this development-only report: ' + str(report), flush=True)
    print('Keep the full run folder. Do not use the runner overall report or held-out predictions to choose settings.', flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, ImportError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
