"""CLI for validating MT5 result metadata and declared artifact bytes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .backtest_result import validate_backtest_result, verify_artifact_files


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

    overall = (
        "ready_for_independent_review"
        if metadata["review_status"] == "ready_for_independent_review"
        and artifacts["status"] == "artifact_bytes_verified"
        else "incomplete"
    )
    report = {
        "overall_status": overall,
        "metadata_validation": metadata,
        "artifact_verification": artifacts,
        "scope": "does_not_parse_mt5_report_or_prove_a_real_test_or_profitability",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if overall == "ready_for_independent_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
