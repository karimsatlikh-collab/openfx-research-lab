"""Static contract checks preventing plan/runner/aggregator drift for M3 v2.0.2."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class M3V2CalibrationContractTests(unittest.TestCase):
    def test_runner_identity_matches_frozen_plan(self):
        plan = (ROOT / "docs/M3_HAC_MBB_V2_CALIBRATION_PLAN.md").read_text(encoding="utf-8")
        runner = (ROOT / "research/m3_hac_mbb_v2_calibration.py").read_text(encoding="utf-8")
        aggregator = (ROOT / "research/aggregate_m3_hac_mbb_v2.py").read_text(encoding="utf-8")
        self.assertIn("M3-HAC-MBB-CALIBRATION-V2-2", plan)
        self.assertIn('"plan_id": "M3-HAC-MBB-CALIBRATION-V2-2"', runner)
        self.assertIn('"method_version": "2.0.2"', runner)
        self.assertIn('"M3-HAC-MBB-CALIBRATION-V2-2"', aggregator)
        self.assertIn('"2.0.2"', aggregator)
        self.assertNotIn("M3-HAC-MBB-CALIBRATION-V2-1", runner + aggregator)
        self.assertNotIn('"method_version": "2.0.1"', runner + aggregator)

    def test_runner_seed_bases_match_frozen_plan(self):
        runner = (ROOT / "research/m3_hac_mbb_v2_calibration.py").read_text(encoding="utf-8")
        aggregator = (ROOT / "research/aggregate_m3_hac_mbb_v2.py").read_text(encoding="utf-8")
        expected = (
            "2_300_000_000", "2_400_000_000", "2_500_000_000",
            "2_600_000_000", "2_700_000_000", "2_800_000_000",
            "2_900_000_000",
        )
        for seed in expected:
            self.assertIn(seed, runner)
            self.assertIn(seed, aggregator)
        stale = (
            "1_300_000_000", "1_400_000_000", "1_500_000_000",
            "1_600_000_000", "1_700_000_000", "1_800_000_000",
            "1_900_000_000",
        )
        for seed in stale:
            self.assertNotIn(seed, runner)
            self.assertNotIn(seed, aggregator)

    def test_aggregator_requires_frozen_plan_hash(self):
        aggregator = (ROOT / "research/aggregate_m3_hac_mbb_v2.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--expected-plan-sha256", required=True)', aggregator)
        self.assertIn("_load_cell(path, expected_plan_sha256)", aggregator)


if __name__ == "__main__":
    unittest.main()
