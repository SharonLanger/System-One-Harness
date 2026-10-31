"""Four-choice campaign contracts and synthetic pipeline checks; no live model calls."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import engine
from schema import load, validate
from research.protocol import digest, validate_protocol
from research.records import read_run

CAMPAIGN = HERE / 'experiments/requested-action-500'
spec = importlib.util.spec_from_file_location('unclear_screen', CAMPAIGN / 'screening_report.py')
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


class UnclearCampaignTests(unittest.TestCase):
    def setUp(self):
        self.cases = load(CAMPAIGN / 'cases.json')
        self.suite = load(CAMPAIGN / 'rounds/001-broad/suite.json')
        self.roles = load(CAMPAIGN / 'calibration_roles.json')

    def test_frozen_version_two_preserves_every_input_and_role(self):
        old = load(CAMPAIGN / 'versions/1/cases.json')
        old_suite = load(CAMPAIGN / 'versions/1/suite.json')
        old_roles = load(CAMPAIGN / 'versions/1/calibration_roles.json')
        validate_protocol(load(CAMPAIGN / 'versions/1/protocol.json'), old, old_roles,
                          cases_path=CAMPAIGN / 'versions/1/cases.json')
        validate_protocol(load(CAMPAIGN / 'protocol.json'), self.cases, self.roles,
                          cases_path=CAMPAIGN / 'cases.json')
        validate(old, old_suite)
        validate(self.cases, self.suite)
        self.assertEqual(self.cases['dataset_version'], '2')
        self.assertEqual(self.suite['experiment_id'], 'requested-action-500-v2')
        self.assertEqual(self.roles, old_roles)
        self.assertEqual(self.suite['rules'], old_suite['rules'])
        self.assertEqual(self.suite['configurations'], old_suite['configurations'])
        self.assertEqual(len(self.cases['cases']), 500)
        for before, after in zip(old['cases'], self.cases['cases']):
            for key in ('id', 'input', 'source_family_id', 'split', 'noise_level', 'tags'):
                self.assertEqual(before[key], after[key])
            self.assertEqual(after['expected'], before['expected'] if before['label_status'] == 'settled' else 'unclear')
            self.assertEqual(after['label_status'], 'settled')
            self.assertNotIn('desired_abstention', after)
        self.assertEqual(Counter(c['expected'] for c in self.cases['cases']),
                         {'explain': 140, 'generate_tests': 140, 'modify_code': 140, 'unclear': 80})
        expected_role_counts = {'development': 32, 'temperature': 16, 'policy': 16, 'held_out': 16}
        self.assertEqual(Counter(self.roles[c['source_family_id']] for c in self.cases['cases']
                                 if c['expected'] == 'unclear'), expected_role_counts)
        for question in self.suite['questions']:
            self.assertEqual(list(question['definition']['criteria']),
                             ['explain', 'generate_tests', 'modify_code', 'unclear'])
            self.assertIn('Choose unclear', question['definition']['instructions'])
        with self.assertRaisesRegex(ValueError, 'frozen dataset'):
            validate_protocol(load(CAMPAIGN / 'protocol.json'), old, old_roles)

    def test_all_variants_execute_and_report_unclear_as_scored_nonactionable(self):
        # Four existing development prompts, one per class, with synthetic probabilities.
        selected = [next(c for c in self.cases['cases'] if c['expected'] == label and c['split'] == 'development')
                    for label in self.suite['labels']]
        self.cases['cases'] = selected
        self.suite['configurations'] = self.suite['configurations'][:1]
        self.suite['rules'] = [r for r in self.suite['rules'] if r['id'] in ('r1-ungated', 'r9-combined-strict')]
        self.suite['baseline']['rule_id'] = 'r1-ungated'
        roles = {c['source_family_id']: 'development' for c in selected}
        fixture = {'responses': {}}
        for q in self.suite['questions']:
            for case in selected:
                label = case['expected']; confidence = .4 if label == 'unclear' else 1.0
                probs = {l: confidence if l == label else (1-confidence)/3 for l in self.suite['labels']}
                fixture['responses']['|'.join([q['id'], 'sdk-default', case['id']])] = {
                    'answers': {'requested_action': {'type': 'choice', 'choice': label,
                                'probabilities': probs, 'answer_confidence': confidence}}}
        root = engine.create(self.cases, self.suite, 'fixture', 'replay', {})
        self.addCleanup(shutil.rmtree, root)
        original = engine.load
        def fixture_load(path):
            if Path(path) == HERE / 'examples/generic-choice/responses.json':
                return deepcopy(fixture)
            return original(path)
        with patch.object(engine, 'load', side_effect=fixture_load):
            engine.worker(root, 'sdk-default')
        self.assertEqual(load(root / 'worker-sdk-default-status.json')['status'], 'completed')
        evidence = read_run(root, roles, 'development')
        self.assertEqual(len(evidence['rows']), 40)
        self.assertTrue(all(row['status'] == 'completed' for row in evidence['rows']))
        protocol = {'campaign_id': self.suite['experiment_id'], 'cases_hash': digest(self.cases),
                    'roles_hash': digest(roles), 'critical_groups': []}
        report = screen.write_screening_report(root, roles, protocol)
        results = load(report.with_name('screening.json'))
        for q in self.suite['questions']:
            groups = results['rules'][q['id'] + '|sdk-default|r1-ungated']
            self.assertEqual(groups['all_development']['classification']['n'], 4)
            self.assertEqual(groups['class:unclear']['classification']['accuracy'], 1)
            flow = groups['all_development']['flow_decisions']
            self.assertEqual((flow['actionable'], flow['accepted_unclear'], flow['rule_rejected']), (3, 1, 0))
            strict = results['rules'][q['id'] + '|sdk-default|r9-combined-strict']['all_development']['flow_decisions']
            self.assertEqual((strict['actionable'], strict['accepted_unclear'], strict['rule_rejected']), (3, 0, 1))
        self.assertIn('Actionable output versus unclear and rejection', report.read_text())

    def test_flow_counts_wrong_action_and_missing_evidence_without_zero_error_claim(self):
        base = {'status': 'completed', 'label_status': 'settled', 'native_accepted': True,
                'raw_label': 'unclear', 'expected': 'unclear'}
        result = screen.flow_decisions([base], self.suite['labels'])
        self.assertIsNone(result['actionable_error'])
        rows = [base, {**base, 'raw_label': 'modify_code'}, {**base, 'native_accepted': False},
                {**base, 'status': 'error'}, {**base, 'native_accepted': None}]
        result = screen.flow_decisions(rows, self.suite['labels'])
        self.assertEqual((result['evaluated'], result['missing']), (3, 2))
        self.assertEqual((result['wrong_actionable'], result['actionable_error']), (1, 1.0))


if __name__ == '__main__':
    unittest.main()
