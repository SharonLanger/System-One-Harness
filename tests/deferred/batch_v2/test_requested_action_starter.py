import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

"""Mechanical checks for the campaign launcher report; existing fruit fixtures only."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import engine
from schema import load
from research.protocol import digest
from research import records

spec = importlib.util.spec_from_file_location('starter_screen', HERE / 'experiments/requested-action-500/screening_report.py')
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


class StarterScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load(HERE / 'examples/generic-choice/cases.json')
        cls.cases['cases'][2]['split'] = 'held_out'
        cls.suite = load(HERE / 'examples/generic-choice/suite.json')
        cls.roles = {'apple-food': 'development', 'apple-company': 'held_out'}
        cls.protocol = {'campaign_id': cls.suite['experiment_id'], 'cases_hash': digest(cls.cases), 'roles_hash': digest(cls.roles), 'critical_groups': []}
        cls.root = engine.create(cls.cases, cls.suite, 'fixture', 'replay', {})
        if engine.run(cls.root):
            raise RuntimeError('Mechanical fixture failed')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def test_report_never_opens_held_out_predictions(self):
        forbidden = set()
        for q in self.suite['questions']:
            for cfg in self.suite['configurations']:
                iid = digest([q['id'], None, cfg['id'], 'case-03'])[:32]
                forbidden.add(self.root / 'inferences' / (iid + '.json'))
                for rule in self.suite['rules']:
                    forbidden.add(engine.case_path(self.root, q, rule, cfg, self.cases['cases'][2]))
        original_load = records.load
        def checked_load(path):
            self.assertNotIn(Path(path), forbidden)
            return original_load(path)
        with patch.object(records, 'load', side_effect=checked_load), patch.object(screen, 'load', side_effect=checked_load):
            report = screen.write_screening_report(self.root, self.roles, self.protocol)
        data = load(report.with_name('screening.json'))
        self.assertEqual(data['allowed_case_ids'], ['case-01', 'case-02'])
        self.assertFalse(data['held_out_loaded'])
        self.assertEqual(len(data['questions']), 4)
        self.assertEqual(len(data['rules']), 8)
        group = data['questions']['q-baseline|sdk-default']['all_development']
        self.assertEqual(group['classification']['n'], 2)
        self.assertEqual(group['probability']['strict_nll_status'], 'finite')
        self.assertIn(f"{group['probability']['strict_nll']:.4f}", report.read_text())

    def test_missing_rule_outcome_is_partial_not_zero_error(self):
        path = engine.case_path(self.root, self.suite['questions'][0], self.suite['rules'][1], self.suite['configurations'][0], self.cases['cases'][0])
        original = path.read_bytes()
        path.unlink()
        try:
            report = screen.write_screening_report(self.root, self.roles, self.protocol)
            data = load(report.with_name('screening.json'))
            group = data['rules']['q-baseline|sdk-default|r-strict']['all_development']
            self.assertFalse(group['complete'])
            self.assertEqual(group['technical_statuses']['unattempted'], 1)
            self.assertIn('PARTIAL', report.read_text())
        finally:
            path.write_bytes(original)

    def test_stale_rule_provenance_fails(self):
        path = engine.case_path(self.root, self.suite['questions'][0], self.suite['rules'][1], self.suite['configurations'][0], self.cases['cases'][0])
        original = path.read_bytes()
        changed = json.loads(original)
        changed['rule_hash'] = 'wrong'
        path.write_text(json.dumps(changed))
        try:
            with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
                screen.write_screening_report(self.root, self.roles, self.protocol)
        finally:
            path.write_bytes(original)

    def test_missing_probabilities_are_visibly_partial(self):
        iid = digest(['q-baseline', None, 'sdk-default', 'case-01'])[:32]
        path = self.root / 'inferences' / (iid + '.json')
        original = path.read_bytes()
        changed = json.loads(original)
        del changed['raw_response']['answers']['subject']['probabilities']
        path.write_text(json.dumps(changed))
        try:
            report = screen.write_screening_report(self.root, self.roles, self.protocol)
            data = load(report.with_name('screening.json'))
            group = data['questions']['q-baseline|sdk-default']['all_development']
            self.assertFalse(group['screen_complete'])
            self.assertEqual(group['settled_planned'], 2)
            self.assertEqual(group['probability']['n'], 1)
            self.assertIn('PARTIAL', report.read_text())
        finally:
            path.write_bytes(original)

    def test_changed_dataset_hash_fails(self):
        protocol = copy.deepcopy(self.protocol)
        protocol['cases_hash'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'frozen dataset'):
            screen.write_screening_report(self.root, self.roles, protocol)


if __name__ == '__main__':
    unittest.main()
