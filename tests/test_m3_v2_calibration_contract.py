"""Static contract checks preventing plan/runner/aggregator drift for M3 v2.0.3."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class M3V2CalibrationContractTests(unittest.TestCase):
    def test_runner_identity_matches_frozen_plan(self):
        plan = (ROOT / "docs/M3_HAC_MBB_V2_CALIBRATION_PLAN.md").read_text(encoding="utf-8")
        runner = (ROOT / "research/m3_hac_mbb_v2_calibration.py").read_text(encoding="utf-8")
        aggregator = (ROOT / "research/aggregate_m3_hac_mbb_v2.py").read_text(encoding="utf-8")
        self.assertIn("M3-HAC-MBB-CALIBRATION-V2-3", plan)
        self.assertIn('"plan_id": "M3-HAC-MBB-CALIBRATION-V2-3"', runner)
        self.assertIn('"method_version": "2.0.2"', runner)
        self.assertIn("FAMILY_REPLICATES = 5000", runner)
        self.assertIn('"families": 5000', aggregator)
        self.assertIn('"M3-HAC-MBB-CALIBRATION-V2-3"', aggregator)
        self.assertIn('"2.0.2"', aggregator)
        self.assertNotIn("M3-HAC-MBB-CALIBRATION-V2-1", runner + aggregator)
        self.assertNotIn('"method_version": "2.0.1"', runner + aggregator)

    def test_runner_seed_bases_match_frozen_plan(self):
        runner = (ROOT / "research/m3_hac_mbb_v2_calibration.py").read_text(encoding="utf-8")
        aggregator = (ROOT / "research/aggregate_m3_hac_mbb_v2.py").read_text(encoding="utf-8")
        expected = (
            "3_300_000_000", "3_400_000_000", "3_500_000_000",
            "3_600_000_000", "3_700_000_000", "3_800_000_000",
            "3_900_000_000",
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

    def test_all_execution_paths_bind_plan_and_git_provenance(self):
        runner = (ROOT / "research/m3_hac_mbb_v2_calibration.py").read_text(encoding="utf-8")
        checker = (ROOT / "research/validate_m3_v2_reference.py").read_text(encoding="utf-8")
        aggregator = (ROOT / "research/aggregate_m3_hac_mbb_v2.py").read_text(encoding="utf-8")
        provenance = (ROOT / "research/m3_calibration_provenance.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--plan-file", required=True)', runner)
        self.assertIn("verify_execution_bindings(", runner)
        self.assertNotIn("--runner-revision", runner)
        self.assertNotIn("--plan-sha256", runner)
        self.assertIn('parser.add_argument("--engine-revision", required=True)', checker)
        self.assertIn('"runner_revision": runner_revision', provenance)
        self.assertIn('parser.add_argument("--plan-file", required=True)', aggregator)
        self.assertIn('reference.get("runner_revision") != cells[0]["runner_revision"]', aggregator)
        self.assertIn("aggregator_git_blob", aggregator)
        self.assertIn("reference_check_git_blob", aggregator)
        self.assertIn("source_provenance", aggregator)
        self.assertIn('git', provenance)
        self.assertIn("hash-object", provenance)


if __name__ == "__main__":
    unittest.main()
