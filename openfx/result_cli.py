"""CLI for validating MT5 result metadata and declared artifact bytes."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

from .backtest_result import validate_backtest_result, verify_artifact_files
from .mt5_report_parser import compare_report_metrics, parse_mt5_report_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate result JSON and verify artifact files")
    validate.add_argument("--result", required=True, help="backtest result JSON file")
    validate.add_argument("--artifact-root", required=True, help="trusted directory containing declared artifacts")
    args = parser.parse_args(argv)
    try:
        result = json.loads(Path(args.result).read_text(encoding="utf-8"))
        metadata = validate_backtest_result(result)
        artifacts = verify_artifact_files(result, args.artifact_root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"OpenFX result validation error: {exc}", file=sys.stderr)
        return 2

    report_parsing = {"status": "skipped", "reason": "artifact bytes were not verified"}
    metric_comparison = {"status": "skipped", "mismatched_metrics": []}
    if artifacts["status"] == "artifact_bytes_verified":
        tester_reports = [item for item in result["artifacts"] if item["kind"] == "tester_report"]
        if len(tester_reports) != 1:
            report_parsing = {"status": "failed", "reason": "exactly one tester_report artifact is required"}
        else:
            report_path = Path(args.artifact_root).resolve() / tester_reports[0]["path"]
            try:
                report_limit = 5 * 1024 * 1024
                with report_path.open("rb") as stream:
                    report_bytes = stream.read(report_limit + 1)
                if len(report_bytes) > report_limit:
                    raise ValueError("tester report exceeds the 5 MiB parser limit")
                if (len(report_bytes) != tester_reports[0]["size_bytes"]
                        or hashlib.sha256(report_bytes).hexdigest().lower() != tester_reports[0]["sha256"].lower()):
                    raise ValueError("tester report changed after artifact verification")
                report_text = report_bytes.decode("utf-8-sig")
                report_parsing = parse_mt5_report_html(report_text)
                report_parsing["status"] = "parsed"
                metric_comparison = compare_report_metrics(report_parsing, result)
                # This flag is set from the independent parser result, not trusted from input.
                reviewed_result = copy.deepcopy(result)
                reviewed_result["verification"]["tester_report_parsed"] = True
                metadata = validate_backtest_result(reviewed_result)
            except (OSError, UnicodeError, ValueError) as exc:
                report_parsing = {"status": "failed", "reason": str(exc)}

    overall = (
        "ready_for_independent_review"
        if metadata["review_status"] == "ready_for_independent_review"
        and artifacts["status"] == "artifact_bytes_verified"
        and report_parsing.get("status") == "parsed"
        and metric_comparison.get("status") == "matched"
        else "incomplete"
    )
    report_verified = (
        report_parsing.get("status") == "parsed"
        and metric_comparison.get("status") == "matched"
        and artifacts["status"] == "artifact_bytes_verified"
    )
    verification_claims = {
        "tester_report_parsed": {
            "input_assertion": result["verification"]["tester_report_parsed"],
            "status": "verified_by_cli" if report_verified else "not_verified_by_cli",
        },
    }
    for key in (
        "journal_complete",
        "data_coverage_verified",
        "costs_recorded",
        "split_boundaries_verified",
    ):
        verification_claims[key] = {
            "input_assertion": result["verification"][key],
            "status": "declared_not_independently_verified",
        }

    report = {
        "overall_status": overall,
        "metadata_validation": metadata,
        "artifact_verification": artifacts,
        "report_parsing": report_parsing,
        "metric_comparison": metric_comparison,
        "verification_claims": verification_claims,
        "scope": "does_not_prove_data_quality_or_profitability",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if overall == "ready_for_independent_review" else 2



if __name__ == "__main__":
    raise SystemExit(main())
