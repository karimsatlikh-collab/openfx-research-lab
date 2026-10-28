"""
Evaluation Module
Basic quality checks for collected data metadata.
"""

import logging
from collections import Counter

logger = logging.getLogger("research_team.evaluation")


def evaluate_records(records: list[dict]) -> dict:
    """
    Evaluate metadata records for completeness and duplicate files.

    This is a basic metadata evaluation, not a verification of
    the actual correctness of file contents.
    """
    total = len(records)

    if total == 0:
        return {
            "total_records": 0,
            "unique_files": 0,
            "duplicate_records": 0,
            "missing_fields": {},
            "quality_status": "no_data",
        }

    required_fields = [
        "file_name",
        "file_type",
        "file_size_bytes",
        "sha256",
        "collection_method",
    ]

    missing_fields = Counter()

    for record in records:
        for field in required_fields:
            if record.get(field) in (None, ""):
                missing_fields[field] += 1

    hashes = [
        record.get("sha256")
        for record in records
        if record.get("sha256")
    ]

    unique_hashes = set(hashes)
    duplicate_records = len(hashes) - len(unique_hashes)

    completeness = 1 - (
        sum(missing_fields.values()) / (total * len(required_fields))
    )

    if completeness >= 0.95 and duplicate_records == 0:
        quality_status = "passed_basic_checks"
    elif completeness >= 0.75:
        quality_status = "needs_review"
    else:
        quality_status = "poor_metadata_quality"

    result = {
        "total_records": total,
        "unique_files": len(unique_hashes),
        "duplicate_records": duplicate_records,
        "missing_fields": dict(missing_fields),
        "metadata_completeness": round(completeness, 4),
        "quality_status": quality_status,
        "evaluation_scope": "metadata_only",
    }

    logger.info(
        "Metadata evaluation completed: %s",
        result["quality_status"],
    )

    return result
