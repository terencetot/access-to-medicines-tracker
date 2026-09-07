"""
Unit tests for the derived measures in compute.py, run against the real
extracted data.json so that the hand-checked case is verified against the
actual workbook, not a fixture.

Hand-checked case (from the build brief): Ethiopia should come out at 12
completed of 31 applicable milestones, completion rate 38.7 percent,
weighted index 40.3 percent.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import compute

DATA_JSON = Path(__file__).resolve().parent.parent / "output" / "data.json"


class TestDerivedMeasures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA_JSON.read_text(encoding="utf-8"))
        cls.progress = cls.data["progress"]
        cls.results = cls.data["results"]
        cls.risks = cls.data["risks"]

    def test_ethiopia_hand_checked_case(self):
        rate = compute.milestone_completion_rate(self.progress, "ETH")
        wpi = compute.weighted_progress_index(self.progress, "ETH")
        applicable = [
            r for r in self.progress if r["ISO3"] == "ETH" and r["Status"] != "NA"
        ]
        completed = [r for r in applicable if r["Status"] == "C"]

        self.assertEqual(len(applicable), 31)
        self.assertEqual(len(completed), 12)
        self.assertAlmostEqual(rate, 12 / 31, places=4)
        self.assertAlmostEqual(rate * 100, 38.7, places=1)
        self.assertAlmostEqual(wpi * 100, 40.3, places=1)

    def test_completion_rate_bounds(self):
        for row in self.data["countries"]:
            iso = row["ISO3"]
            rate = compute.milestone_completion_rate(self.progress, iso)
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)

    def test_weighted_index_always_at_least_completion_rate_when_no_delays(self):
        # Weighted index treats IP milestones as half-credit, so where a
        # country has any IP milestone the weighted index must exceed the
        # strict completion rate (never the other way round).
        for row in self.data["countries"]:
            iso = row["ISO3"]
            rows = [r for r in self.progress if r["ISO3"] == iso and r["Status"] != "NA"]
            has_ip = any(r["Status"] == "IP" for r in rows)
            has_delayed_or_ns_only_else = any(r["Status"] in ("D",) for r in rows)
            if has_ip and not has_delayed_or_ns_only_else:
                rate = compute.milestone_completion_rate(self.progress, iso)
                wpi = compute.weighted_progress_index(self.progress, iso)
                self.assertGreaterEqual(wpi, rate)

    def test_evidence_coverage_zero_when_nothing_verified(self):
        # Every status in this workbook is carried over from v1 and unverified
        # (Verified == 'No' throughout); evidence coverage must therefore be
        # zero for every country until a Yes appears in the data.
        for row in self.data["countries"]:
            iso = row["ISO3"]
            coverage = compute.evidence_coverage(self.progress, iso)
            completed = [
                r for r in self.progress if r["ISO3"] == iso and r["Status"] == "C"
            ]
            if completed:
                self.assertEqual(coverage, 0.0)

    def test_phase_position_known_for_every_country(self):
        for row in self.data["countries"]:
            iso = row["ISO3"]
            phase = compute.phase_position(self.progress, iso)
            self.assertIn(phase, compute.PHASE_ORDER)

    def test_regional_rollup_bounds(self):
        for milestone in self.data["milestones"]:
            mid = milestone["Milestone ID"]
            rollup = compute.regional_rollup(self.progress, mid)
            self.assertGreaterEqual(rollup, 0.0)
            self.assertLessEqual(rollup, 1.0)

    def test_indicator_gap_none_when_no_value_recorded(self):
        # At this stage almost every results row has no value for this round,
        # which must yield an explicit None (empty state), never a fabricated
        # zero or placeholder gap.
        code = self.results[1]["Indicator code"]
        iso = self.results[1]["ISO3"]
        gap = compute.indicator_gap(self.results, code, iso)
        row = self.results[1]
        if row.get("Value for this round") is None:
            self.assertIsNone(gap)

    def test_open_high_or_extreme_risks_subset_of_all_risks(self):
        open_risks = compute.open_high_or_extreme_risks(self.risks)
        self.assertLessEqual(len(open_risks), len(self.risks))
        for r in open_risks:
            self.assertIn(r["Status"], ("Open", "In progress"))
            self.assertIn(r["Rating"], ("High", "Extreme"))


if __name__ == "__main__":
    unittest.main()
