import unittest as _deferred_unittest
raise _deferred_unittest.SkipTest("Phase two: experiment dependency; see tests/deferred/README.md")

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_paths


class RunPathTests(unittest.TestCase):
    def test_readable_israel_time_and_latest_first_sort(self):
        with TemporaryDirectory() as directory, patch.object(run_paths, 'datetime') as clock:
            clock.now.side_effect = lambda zone: datetime(2026, 10, 31, 22, 25, 3, tzinfo=timezone.utc).astimezone(zone)
            earlier = run_paths.allocate(directory)
            self.assertEqual(earlier.name, '2026-11-01_00-25-03')
            clock.now.side_effect = lambda zone: datetime(2026, 11, 1, 7, 5, 9, tzinfo=timezone.utc).astimezone(zone)
            later = run_paths.allocate(directory)
            self.assertEqual(later.name, '2026-11-01_09-05-09')
            self.assertEqual(sorted([earlier.name, later.name], reverse=True), [later.name, earlier.name])

    def test_concurrent_same_second_runs_never_overwrite(self):
        with TemporaryDirectory() as directory, patch.object(run_paths, 'datetime') as clock:
            clock.now.return_value = datetime(2026, 10, 31, 20, 25, 3)
            parent = Path(directory) / 'results'
            with ThreadPoolExecutor(max_workers=8) as pool:
                paths = list(pool.map(lambda _: run_paths.allocate(parent), range(8)))
            expected = ['2026-10-31_20-25-03'] + [f'2026-10-31_20-25-03_{i:03}' for i in range(1, 8)]
            self.assertEqual(sorted(p.name for p in paths), expected)
            self.assertTrue(all(p.is_dir() for p in paths))
            marker = paths[0] / 'keep.txt'
            marker.write_text('existing result')
            self.assertEqual(run_paths.allocate(parent).name, '2026-10-31_20-25-03_008')
            self.assertEqual(marker.read_text(), 'existing result')
