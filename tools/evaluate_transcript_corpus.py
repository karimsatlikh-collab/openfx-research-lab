"""Evaluate the curated synthetic transcript-fidelity regression corpus."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openfx.transcript_quality import compare_transcript_fidelity

CORPUS_PATH = ROOT / "tests" / "fixtures" / "transcript_adversarial_cases.json"


def main() -> int:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    counts = {"true_positive": 0, "false_negative": 0, "false_positive": 0, "true_negative": 0}
    errors = []
    for case in corpus["cases"]:
        result = compare_transcript_fidelity(case["reference"], case["extracted"])
        flagged = result["status"] == "needs_human_review"
        meaning_change = case["label"] == "meaning_change"
        if meaning_change and flagged:
            counts["true_positive"] += 1
        elif meaning_change:
            counts["false_negative"] += 1
        elif flagged:
            counts["false_positive"] += 1
        else:
            counts["true_negative"] += 1
        if result["status"] != case["expected_status"]:
            errors.append({
                "id": case["id"],
                "label": case["label"],
                "expected_status": case["expected_status"],
                "actual_status": result["status"],
                "flags": result["flags"],
                "similarity": result["similarity"],
            })

    total = len(corpus["cases"])
    report = {
        "scope": corpus["scope"],
        "cases_total": total,
        "confusion_matrix": counts,
        "false_positive_rate_on_curated_equivalent_cases": (
            counts["false_positive"] / (counts["false_positive"] + counts["true_negative"])
            if counts["false_positive"] + counts["true_negative"] else None
        ),
        "false_negative_rate_on_curated_meaning_change_cases": (
            counts["false_negative"] / (counts["false_negative"] + counts["true_positive"])
            if counts["false_negative"] + counts["true_positive"] else None
        ),
        "mismatches": errors,
        "warning": "These rates describe only this small synthetic curated fixture set; they are not estimates of performance on real transcripts.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
