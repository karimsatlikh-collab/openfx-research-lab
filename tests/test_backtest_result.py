import copy
import unittest

from openfx.backtest_result import validate_backtest_result


def make_result():
    return {
        "schema_version": 1,
        "experiment_id": "mt5-run-001",
        "created_at_utc": "2026-10-29T12:00:00+00:00",
        "source_commit_sha": "b" * 40,
        "result_origin": "mt5_strategy_tester",
        "execution": {
            "terminal_build": "5000",
            "ea_sha256": "a" * 64,
            "data_sha256": "c" * 64,
            "symbol": "EURUSD",
            "timeframe": "M15",
            "data_start": "2020-01-01",
            "data_end": "2025-12-31",
            "modeling_mode": "every_tick",
            "initial_deposit": 10000.0,
            "deposit_currency": "USD",
            "leverage": 100,
            "spread_points": 12.0,
            "commission_per_lot": 7.0,
            "slippage_points": 1.0,
        },
        "splits": {
            "development": {"start": "2020-01-01", "end": "2022-12-31"},
            "validation": {"start": "2023-01-01", "end": "2023-12-31"},
            "final_oos": {"start": "2024-01-01", "end": "2025-12-31"},
        },
        "metrics": {
            "trade_count": 100,
            "net_profit": 250.0,
            "gross_profit": 500.0,
            "gross_loss": 250.0,
            "profit_factor": 2.0,
            "expected_payoff": 2.5,
            "max_drawdown_pct": 12.0,
            "relative_drawdown_pct": 8.0,
        },
        "artifacts": [
            {"kind": "tester_report", "path": "reports/tester.html", "size_bytes": 1000, "sha256": "1" * 64},
            {"kind": "journal_log", "path": "logs/tester.log", "size_bytes": 500, "sha256": "2" * 64},
            {"kind": "ea_binary", "path": "build/PlanGo.ex5", "size_bytes": 30000, "sha256": "a" * 64},
            {"kind": "data_manifest", "path": "data/manifest.json", "size_bytes": 250, "sha256": "c" * 64},
        ],
        "verification": {
            "tester_report_parsed": True,
            "journal_complete": True,
            "data_coverage_verified": True,
            "costs_recorded": True,
            "split_boundaries_verified": True,
        },
        "notes": "Synthetic test fixture only; no real MT5 run is claimed.",
    }


class BacktestResultTests(unittest.TestCase):
    def test_complete_result_is_only_ready_for_independent_review(self):
        result = validate_backtest_result(make_result())
        self.assertEqual(result["review_status"], "ready_for_independent_review")
        self.assertEqual(result["blockers"], [])
        self.assertIn("not_profitability_verification", result["scope"])

    def test_missing_required_artifact_blocks_review(self):
        fixture = make_result()
        fixture["artifacts"] = [a for a in fixture["artifacts"] if a["kind"] != "journal_log"]
        result = validate_backtest_result(fixture)
        self.assertEqual(result["review_status"], "incomplete")
        self.assertIn("missing_required_artifacts:journal_log", result["blockers"])

    def test_false_verification_check_blocks_review(self):
        fixture = make_result()
        fixture["verification"]["journal_complete"] = False
        result = validate_backtest_result(fixture)
        self.assertIn("verification_incomplete:journal_complete", result["blockers"])

    def test_overlapping_out_of_sample_splits_are_rejected(self):
        fixture = make_result()
        fixture["splits"]["validation"]["start"] = "2022-12-31"
        with self.assertRaisesRegex(ValueError, "overlaps"):
            validate_backtest_result(fixture)

    def test_non_finite_metrics_are_rejected(self):
        fixture = make_result()
        fixture["metrics"]["net_profit"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite number"):
            validate_backtest_result(fixture)

    def test_profit_factor_mismatch_is_a_warning_not_a_success_claim(self):
        fixture = make_result()
        fixture["metrics"]["profit_factor"] = 9.0
        result = validate_backtest_result(fixture)
        self.assertIn("profit_factor_differs_from_gross_profit_over_gross_loss", result["warnings"])
        self.assertEqual(result["scope"], "schema_and_metadata_validation_not_profitability_verification")

    def test_mock_result_cannot_be_mislabeled_as_backtest(self):
        fixture = make_result()
        fixture["result_origin"] = "mock"
        with self.assertRaisesRegex(ValueError, "mock results are not backtests"):
            validate_backtest_result(fixture)

    def test_artifact_path_traversal_is_rejected(self):
        fixture = make_result()
        fixture["artifacts"][0]["path"] = "../private/report.html"
        with self.assertRaisesRegex(ValueError, "escape"):
            validate_backtest_result(fixture)

    def test_invalid_modeling_mode_type_is_rejected_cleanly(self):
        fixture = make_result()
        fixture["execution"]["modeling_mode"] = []
        with self.assertRaisesRegex(ValueError, "modeling_mode"):
            validate_backtest_result(fixture)


if __name__ == "__main__":
    unittest.main()
