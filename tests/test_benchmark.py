"""Benchmark aggregation must expose variability and changing output."""

import copy
import unittest

from scripts.benchmark import combine_rounds, summarize


class BenchmarkResults(unittest.TestCase):
    def test_combined_rounds_retain_spread_and_detect_output_changes(self):
        run = {
            "javascript": summarize([10, 20, 30]),
            "python": summarize([5, 10, 15]),
            "speedup": 2.0,
            "equal": True,
            "stable": True,
            "output_sha256": {"javascript": ["a"], "python": ["a"]},
            "output_bytes": {"javascript": 1, "python": 1},
        }
        row = {"rounds": [run, copy.deepcopy(run)]}
        combine_rounds(row)
        self.assertTrue(row["equal"] and row["stable"])
        self.assertEqual(row["speedup"], 2)
        self.assertEqual(row["round_speedups"], [2, 2])
        self.assertEqual(len(row["python"]["samples_ms"]), 6)
        self.assertEqual(run["python"]["p10_ms"], 6)
        self.assertEqual(run["python"]["p90_ms"], 14)

        # Matching within each round is insufficient if output changes between rounds.
        row["rounds"][1]["output_sha256"] = {"javascript": ["b"], "python": ["b"]}
        combine_rounds(row)
        self.assertTrue(row["equal"])
        self.assertFalse(row["stable"])
