"""Static contract checks preventing plan/runner/aggregator drift for M3 v2.0.3."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m3_calibration_provenance import verify_benchmark_report


class M3V2CalibrationContractTests(unittest.TestCase):
    def test_runner_identity_matches_frozen_plan(self):
        plan = (ROOT / "docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md").read_text(encoding="utf-8")
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
            "3_600_000_000", "4_100_000_000", "4_200_000_000",
            "4_300_000_000", "4_400_000_000",
        )
        for seed in expected:
            self.assertIn(seed, runner)
            self.assertIn(seed, aggregator)
        stale = (
            "1_300_000_000", "1_400_000_000", "1_500_000_000",
            "1_600_000_000", "1_700_000_000", "1_800_000_000",
            "1_900_000_000", "2_300_000_000", "2_400_000_000",
            "2_500_000_000", "2_600_000_000", "2_700_000_000",
            "2_800_000_000", "2_900_000_000", "3_700_000_000", "3_800_000_000", "3_900_000_000",
        )
        for seed in stale:
            self.assertNotIn(seed, runner)
            self.assertNotIn(seed, aggregator)

    def test_all_execution_paths_bind_plan_and_git_provenance(self):
        runner = (ROOT / "research/m3_hac_mbb_v2_calibration.py").read_text(encoding="utf-8")
        checker = (ROOT / "research/validate_m3_v2_reference.py").read_text(encoding="utf-8")
        aggregator = (ROOT / "research/aggregate_m3_hac_mbb_v2.py").read_text(encoding="utf-8")
        provenance = (ROOT / "research/m3_calibration_provenance.py").read_text(encoding="utf-8")
        benchmark = (ROOT / "research/benchmark_m3_v2_family.py").read_text(encoding="utf-8")
        plan = (ROOT / "docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--plan-file", required=True)', runner)
        self.assertIn("verify_execution_bindings(", runner)
        self.assertIn("verify_benchmark_report(", runner)
        self.assertIn("expected_estimate = mean * 151500 / 3600.0", provenance)
        self.assertIn("benchmark_seed_ranges", provenance)
        self.assertIn('parser.add_argument("--benchmark-report", required=True)', runner)
        self.assertIn('parser.add_argument("--max-cpu-hours", type=float, required=True)', runner)
        self.assertNotIn("--runner-revision", runner)
        self.assertNotIn("--plan-sha256", runner)
        self.assertIn('parser.add_argument("--engine-revision", required=True)', checker)
        self.assertIn('parser.add_argument("--benchmark-report", required=True)', checker)
        self.assertIn('parser.add_argument("--max-cpu-hours", type=float, required=True)', checker)
        self.assertIn('"runner_revision": runner_revision', provenance)
        self.assertIn('parser.add_argument("--plan-file", required=True)', aggregator)
        self.assertIn('parser.add_argument("--benchmark-report", required=True)', aggregator)
        self.assertIn('parser.add_argument("--max-cpu-hours", type=float, required=True)', aggregator)
        self.assertIn('reference.get("runner_revision") != cells[0]["runner_revision"]', aggregator)
        self.assertIn("aggregator_git_blob", aggregator)
        self.assertIn("reference_check_git_blob", aggregator)
        self.assertIn("source_provenance", aggregator)
        self.assertIn("benchmark_git_blob", aggregator)
        self.assertIn("verify_benchmark_report(", aggregator)
        self.assertIn("research/benchmark_m3_v2_family.py", provenance)
        self.assertIn("performance_preflight_only_not_calibration", benchmark)
        self.assertLess(benchmark.index("elapsed = time.perf_counter() - started"), benchmark.index("timings.append(elapsed)"))
        self.assertIn('result["benchmark_sha256"]', benchmark)
        self.assertIn("TOTAL_FAMILY_EQUIVALENTS = 151_500", benchmark)
        self.assertIn("94.94%", plan)
        self.assertIn("5,000 independent families", plan)
        self.assertIn('git', provenance)
        self.assertIn("hash-object", provenance)


    def test_benchmark_report_is_self_hashed_and_budget_gated(self):
        provenance = {
            "plan_sha256": "a" * 64,
            "engine_revision": "b" * 40,
            "runner_revision": "c" * 40,
            "plan_git_blob": "d" * 40,
            "engine_git_blob": "e" * 40,
            "runner_git_blob": "f" * 40,
            "aggregator_git_blob": "1" * 40,
            "reference_check_git_blob": "2" * 40,
            "benchmark_git_blob": "3" * 40,
        }
        runtime = {
            "python": "3.12.0", "numpy": "2.3.5", "numba": "0.65.1",
            "platform": "Linux-test", "cpu_count": 8,
        }
        report = {
            "evidence_class": "performance_preflight_only_not_calibration",
            "plan_id": "M3-HAC-MBB-CALIBRATION-V2-3",
            **provenance,
            "runtime": runtime, "platform": runtime["platform"], "cpu_count": 8,
            "timed_bootstrap_replicates": 9999, "timed_families": 3,
            "family_seconds": [1.0, 2.0, 3.0],
            "mean_seconds_per_family": 2.0,
            "estimated_total_family_equivalents": 151500,
            "estimated_campaign_cpu_hours": 2.0 * 151500 / 3600.0,
            "benchmark_seed_ranges": {
                "family": [3_950_000_000, 3_950_000_003],
                "bootstrap": [3_960_000_000, 3_960_000_003],
            },
            "pvalue_output_sha256": "4" * 64,
            "return_hashes_sha256": "5" * 64,
            "realized_correlations": [0.4, 0.5, 0.6],
        }
        canonical = json.dumps(report, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False).encode("utf-8")
        report["benchmark_sha256"] = hashlib.sha256(canonical).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmark.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            valid = verify_benchmark_report(path, provenance, runtime, 100.0)
            self.assertEqual(valid["benchmark_sha256"], report["benchmark_sha256"])
            self.assertEqual(valid["approved_max_cpu_hours"], 100.0)
            with self.assertRaises(ValueError):
                verify_benchmark_report(path, provenance, runtime, 50.0)
            report["mean_seconds_per_family"] = 99.0
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_benchmark_report(path, provenance, runtime, 100.0)


if __name__ == "__main__":
    unittest.main()
