"""Check repeated-run aggregation and retention of failed measurements."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import benchmark


class BenchmarkTests(unittest.TestCase):
    def test_weighted_cost_distinguishes_shortest_and_cheapest_paths(self):
        stage = dict(id='detour', board=['SF.F.', '.FFFF', 'F....', '.F..G'],
                     bridges=[], switches=[], splitters=[])
        self.assertEqual(benchmark.replay_weighted_cost(stage, ['D', 'R', 'R', 'R', 'R', 'D']), 16)
        self.assertEqual(benchmark.replay_weighted_cost(stage, ['D', 'D', 'R', 'R', 'U', 'R', 'D']), 15)

    def test_incorrect_reported_cost_is_not_certified_by_ac(self):
        stage = dict(id='detour', board=['SF.F.', '.FFFF', 'F....', '.F..G'],
                     bridges=[], switches=[], splitters=[])
        result = dict(verdict='AC', statistics={}, answer=dict(
            actions=['D', 'D', 'R', 'R', 'U', 'R', 'D'], metrics={'weighted_cost': 7}))
        validation = benchmark.validate_weighted_cost(result, stage, 'UCS')
        self.assertEqual(result['verdict'], 'AC')
        self.assertEqual(validation['status'], 'mismatch')
        self.assertEqual(validation['replayed'], 15)
        self.assertEqual(validation['reported'], 7)

    def test_statistics_and_missing_values(self):
        stats = benchmark.describe([1, 2, 3, 4, 100, None])
        self.assertEqual(stats['median'], 3)
        self.assertEqual(stats['iqr'], 2)
        self.assertIsNone(benchmark.describe([])['median'])

    def test_failed_run_is_retained_and_not_averaged_as_zero(self):
        calls = 0

        def execute(*args, **kwargs):
            nonlocal calls
            calls += 1
            failed = calls == 3  # warmup + one AC + one TLE
            return dict(verdict='TLE' if failed else 'AC', metrics_complete=not failed,
                        statistics={'search_time_ms': None if failed else 12,
                                    'solution_length': None if failed else 7},
                        actions=None if failed else ['R'], answer=None)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'experiment'
            argv = ['benchmark', '--algorithms', 'BFS', '--repeats', '2', '--output', str(output)]
            case = dict(id='sample01', input='samples/01.in.json', reference_length=7)
            with patch('sys.argv', argv), patch.object(benchmark, 'environment', return_value={}), \
                    patch.object(benchmark, 'resolve_manifest_testcases', return_value=[case]), \
                    patch.object(benchmark, 'execute_and_check', side_effect=execute):
                self.assertEqual(benchmark.main(), 1)
            rows = [json.loads(line) for line in (output / 'runs.jsonl').read_text().splitlines()]
            self.assertEqual([r['verdict'] for r in rows], ['AC', 'TLE'])
            summary = json.loads((output / 'summary.json').read_text())[0]
            self.assertEqual(summary['runs'], 2)
            self.assertEqual(summary['complete'], 1)
            self.assertEqual(summary['search_time_ms_median'], 12)
            self.assertEqual(summary['verdicts']['TLE'], 1)


if __name__ == '__main__':
    unittest.main()
