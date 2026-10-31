import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import engine
from schema import load
from worker_logging import ErrorLog, worker_errors


class WorkerLoggingTests(unittest.TestCase):
    def test_filters_traces_and_restores_imported_aliases(self):
        from laya_context_router import log_utils
        from laya_context_router.laya import predict
        original = log_utils.log
        alias = predict.log
        name = 'laya_context_router._logging_test'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'worker.jsonl'
            with patch.dict(sys.modules):
                with self.assertRaisesRegex(RuntimeError, 'scope failed'):
                    with worker_errors(path) as sink:
                        sink.context = {'case_id': 'case-1'}
                        for _ in range(1000):
                            predict.log('DEBUG', 'laya', 'response_received', response='x' * 10000)
                            log_utils.log('INFO', 'laya', 'agent_reused')
                        self.assertFalse(path.exists())
                        module = types.ModuleType(name)
                        module.log = log_utils.log
                        sys.modules[name] = module
                        try:
                            raise ValueError('bad response')
                        except ValueError as exc:
                            module.log('ERROR', 'laya', 'prediction_failed', error=exc, payload='secret payload')
                        raise RuntimeError('scope failed')
                self.assertIs(module.log, original)
            self.assertIs(log_utils.log, original)
            self.assertIs(predict.log, alias)
            record = json.loads(path.read_text())
            self.assertEqual(record['context']['case_id'], 'case-1')
            self.assertEqual(record['error']['type'], 'ValueError')
            self.assertIn('raise ValueError', record['error']['traceback'])
            self.assertNotIn('secret payload', path.read_text())

    def test_error_flood_rotates_and_limits_huge_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'worker.jsonl'
            sink = ErrorLog(path, max_bytes=8192, backups=2)
            for _ in range(300):
                sink('ERROR', 'worker', 'failed', error=ValueError('é' * 100000))
            files = list(Path(directory).iterdir())
            self.assertEqual(len(files), 3)
            self.assertLessEqual(sum(p.stat().st_size for p in files), 3 * 8192)
            for file in files:
                self.assertLessEqual(file.stat().st_size, 8192)
                for line in file.read_text().splitlines():
                    json.loads(line)

    def test_successful_worker_keeps_evidence_without_duplicate_logs(self):
        cases = load(HERE / 'examples/generic-choice/cases.json')
        suite = load(HERE / 'examples/generic-choice/suite.json')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            engine.save(root / 'manifest.json', {'suite': suite, 'cases': cases, 'mode': 'fixture',
                        'rule_mode': 'replay', 'limits': {}, 'run_id': 'test'})
            engine.worker(root, 'sdk-default')
            self.assertEqual(load(root / 'worker-sdk-default-status.json')['status'], 'completed')
            self.assertFalse((root / 'worker-sdk-default.jsonl').exists())
            inferences = list((root / 'inferences').glob('*.json'))
            self.assertTrue(inferences)
            for path in inferences:
                record = load(path)
                self.assertEqual(record['logs'], [])
                self.assertTrue(record['raw_response']['answers'])
                self.assertTrue(record['payload'])

    def test_case_failures_keep_checkpoint_and_bounded_diagnostic(self):
        cases = load(HERE / 'examples/generic-choice/cases.json')
        suite = load(HERE / 'examples/generic-choice/suite.json')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            engine.save(root / 'manifest.json', {'suite': suite, 'cases': cases, 'mode': 'fixture',
                        'rule_mode': 'replay', 'limits': {}, 'run_id': 'test'})
            with patch.object(engine, 'execute', side_effect=ValueError('test prediction failure')):
                engine.worker(root, 'sdk-default')
            errors = [json.loads(line) for line in (root / 'worker-sdk-default.jsonl').read_text().splitlines()]
            self.assertTrue(errors)
            self.assertTrue(all(row['context']['case_id'] for row in errors))
            for path in (root / 'inferences').glob('*.json'):
                self.assertEqual(load(path)['error']['message'], 'test prediction failure')
            for path in (root / 'batches').rglob('case-*.json'):
                self.assertEqual(load(path)['status'], 'error')


if __name__ == '__main__':
    unittest.main()
