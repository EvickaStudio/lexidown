"""Different output is valid, but output that changes across rounds is not."""

import copy
import unittest

from scripts.benchmark import summarize
from scripts.compare_converters import combine_rounds


class ComparisonResults(unittest.TestCase):
    def test_aggregation_retains_samples_and_distinguishes_equality_from_stability(
        self,
    ):
        run = {
            "engines": {
                name: {
                    **summarize(samples),
                    "output_sha256": [digest],
                    "output_bytes": 10,
                    "equal_to_javascript": name != "other",
                }
                for name, samples, digest in (
                    ("javascript", [10, 20, 30], "a"),
                    ("python", [5, 10, 15], "a"),
                    ("other", [1, 2, 3], "b"),
                )
            }
        }
        row = {"rounds": [run, copy.deepcopy(run)]}
        combine_rounds(row)
        self.assertEqual(row["engines"]["python"]["speedup_over_javascript"], 2)
        self.assertEqual(
            row["engines"]["python"]["round_speedups_over_javascript"], [2, 2]
        )
        self.assertEqual(row["engines"]["other"]["samples_ms"], [1, 2, 3, 1, 2, 3])
        self.assertTrue(row["engines"]["other"]["stable"])
        self.assertFalse(row["engines"]["other"]["equal_to_javascript"])
        row["rounds"][1]["engines"]["python"]["output_sha256"] = ["c"]
        combine_rounds(row)
        self.assertFalse(row["engines"]["python"]["stable"])
