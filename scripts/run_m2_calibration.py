"""CLI for the frozen M2 synthetic calibration campaign."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from openfx.calibration import run_campaign


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir)
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output directory: {output}")
    output.mkdir(parents=True)
    result = run_campaign()
    raw_path = output / "raw-records.jsonl"
    with raw_path.open("x", encoding="utf-8", newline="\n") as stream:
        for record in result.pop("raw_records"):
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False) + "\n")
    summary_path = output / "aggregate-report.json"
    with summary_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({
        "raw_records": str(raw_path),
        "aggregate_report": str(summary_path),
        "acceptance": result["acceptance"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
