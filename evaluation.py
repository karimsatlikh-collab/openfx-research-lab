"""
Evaluation Module
Quality checks for collected file metadata; this is not content verification.
"""

import logging
import re
from collections import Counter

logger = logging.getLogger("openfx.evaluation")
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_REQUIRED_FIELDS = (
    "file_name", "file_type", "file_size_bytes", "sha256", "collection_method",
)


def evaluate_records(records: list[dict]) -> dict:
    """Evaluate metadata completeness, field types, SHA-256 format, and duplicates."""
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError("every record must be an object")
    total = len(records)
    if total == 0:
        return {
            "total_records": 0,
            "unique_files": 0,
            "duplicate_records": 0,
            "missing_fields": {},
            "invalid_fields": {},
            "invalid_hash_records": 0,
            "quality_status": "no_data",
            "evaluation_scope": "metadata_only",
        }

    missing_fields = Counter()
    invalid_fields = Counter()
    valid_hashes = []
    invalid_hash_records = 0

    for index, record in enumerate(records):
        for field in _REQUIRED_FIELDS:
            if record.get(field) in (None, ""):
                missing_fields[field] += 1

        for field in ("file_name", "file_type", "collection_method"):
            value = record.get(field)
            if value not in (None, "") and not isinstance(value, str):
                invalid_fields[field] += 1

        size = record.get("file_size_bytes")
        if size not in (None, "") and (
            not isinstance(size, int) or isinstance(size, bool) or size < 0
        ):
            invalid_fields["file_size_bytes"] += 1

        digest = record.get("sha256")
        if digest in (None, ""):
            continue
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            invalid_hash_records += 1
            invalid_fields["sha256"] += 1
        else:
            valid_hashes.append(digest.lower())

    hash_counts = Counter(valid_hashes)
    unique_hashes = set(valid_hashes)
    duplicate_records = sum(count - 1 for count in hash_counts.values() if count > 1)
    completeness = 1 - (
        sum(missing_fields.values()) / (total * len(_REQUIRED_FIELDS))
    )
    has_invalid_fields = bool(invalid_fields)

    if completeness >= 0.95 and duplicate_records == 0 and not has_invalid_fields:
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
        "invalid_fields": dict(invalid_fields),
        "invalid_hash_records": invalid_hash_records,
        "metadata_completeness": round(completeness, 4),
        "quality_status": quality_status,
        "evaluation_scope": "metadata_only",
    }
    logger.info("Metadata evaluation completed: %s", result["quality_status"])
    return result
