import contextlib
import copy
import io
import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from openfx.backtest_result import validate_backtest_result, verify_artifact_files
from openfx.result_cli import main as result_cli_main


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


    def test_ea_and_data_hashes_must_match_artifact_hashes(self):
        fixture = make_result()
        fixture["artifacts"][2]["sha256"] = "d" * 64
        fixture["artifacts"][3]["sha256"] = "e" * 64
        result = validate_backtest_result(fixture)
        self.assertIn("ea_binary_hash_mismatch", result["blockers"])
        self.assertIn("data_manifest_hash_mismatch", result["blockers"])

    def test_empty_required_artifact_blocks_review(self):
        fixture = make_result()
        fixture["artifacts"][0]["size_bytes"] = 0
        result = validate_backtest_result(fixture)
        self.assertIn("empty_required_artifacts:tester_report", result["blockers"])

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


    def materialize_artifacts(self, fixture, root):
        for artifact in fixture["artifacts"]:
            path = root / artifact["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if artifact["kind"] == "tester_report":
                content = b"""<html><table>
                <tr><td>Total Net Profit:</td><td>250.00</td></tr>
                <tr><td>Gross Profit:</td><td>500.00</td></tr>
                <tr><td>Gross Loss:</td><td>-250.00</td></tr>
                <tr><td>Profit Factor:</td><td>2.00</td></tr>
                <tr><td>Expected Payoff:</td><td>2.50</td></tr>
                <tr><td>Total Trades:</td><td>100</td></tr>
                <tr><td>Maximal Drawdown:</td><td>1,200.00 (12.00%)</td></tr>
                <tr><td>Relative Drawdown:</td><td>800.00 (8.00%)</td></tr>
                </table></html>"""
            else:
                content = ("synthetic artifact: " + artifact["kind"]).encode("utf-8")
            path.write_bytes(content)
            artifact["size_bytes"] = len(content)
            artifact["sha256"] = hashlib.sha256(content).hexdigest()
            if artifact["kind"] == "ea_binary":
                fixture["execution"]["ea_sha256"] = artifact["sha256"]
            if artifact["kind"] == "data_manifest":
                fixture["execution"]["data_sha256"] = artifact["sha256"]

    def test_artifact_bytes_and_hashes_are_verified(self):
        fixture = make_result()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.materialize_artifacts(fixture, root)
            result = verify_artifact_files(fixture, root)
            self.assertEqual(result["status"], "artifact_bytes_verified")
            self.assertEqual(len(result["verified_artifacts"]), 4)

    def test_modified_artifact_is_rejected(self):
        fixture = make_result()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.materialize_artifacts(fixture, root)
            target = root / fixture["artifacts"][0]["path"]
            target.write_bytes(b"X" * target.stat().st_size)
            result = verify_artifact_files(fixture, root)
            self.assertIn("artifact_hash_mismatch:reports/tester.html", result["blockers"])


    def test_result_cli_reports_verified_artifact_bytes(self):
        fixture = make_result()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.materialize_artifacts(fixture, root)
            result_path = root / "result.json"
            result_path.write_text(json.dumps(fixture), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = result_cli_main([
                    "validate", "--result", str(result_path), "--artifact-root", str(root),
                ])
            self.assertEqual(code, 0)
            self.assertIn("ready_for_independent_review", output.getvalue())
            self.assertIn("does_not_parse_mt5_report", output.getvalue())

    def test_result_cli_returns_nonzero_when_artifact_is_missing(self):
        fixture = make_result()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "result.json"
            result_path.write_text(json.dumps(fixture), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = result_cli_main([
                    "validate", "--result", str(result_path), "--artifact-root", str(root),
                ])
            self.assertEqual(code, 2)
            self.assertIn("incomplete", output.getvalue())

    def test_invalid_modeling_mode_type_is_rejected_cleanly(self):
        fixture = make_result()
        fixture["execution"]["modeling_mode"] = []
        with self.assertRaisesRegex(ValueError, "modeling_mode"):
            validate_backtest_result(fixture)

    def test_windows_drive_artifact_path_is_rejected(self):
        fixture = make_result()
        fixture["artifacts"][0]["path"] = "C:/private/report.html"
        with self.assertRaisesRegex(ValueError, "relative|escape"):
            validate_backtest_result(fixture)


if __name__ == "__main__":
    unittest.main()
