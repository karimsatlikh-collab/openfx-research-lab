"""Evidence-linked claims with explicit separation of source statements and hypotheses."""
from __future__ import annotations

import re
from typing import Any

from .source_registry import validate_source_registry

CLAIM_CLASSES = {"source_confirmed", "source_claim", "interpretation", "hypothesis", "unknown"}
REVIEW_STATUSES = {"draft", "human_verified", "needs_review", "rejected"}
CLAIM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def validate_claim_register(register: Any, source_registry: dict[str, Any]) -> dict[str, Any]:
    """Validate claim provenance against a previously validated source registry.

    Quotes must be exact substrings of the registered transcript segment. This
    validates traceability, not whether a source statement is factually true.
    """
    if not isinstance(register, dict) or set(register) != {"schema_version", "claims"}:
        raise ValueError("claim register must contain only schema_version and claims")
    if type(register["schema_version"]) is not int or register["schema_version"] != 1:
        raise ValueError("unsupported claim register schema_version")
    if not isinstance(register["claims"], list):
        raise ValueError("claims must be a list")

    source_registry = validate_source_registry(source_registry)
    sources = {item["source_id"]: item for item in source_registry["sources"]}
    segments = {item["segment_id"]: item for item in source_registry.get("transcript_segments", [])}
    claim_ids = set()
    contradiction_groups: dict[str, list[str]] = {}

    for claim in register["claims"]:
        required = {
            "claim_id", "claim_text", "classification", "review_status",
            "rationale", "evidence", "contradiction_group",
        }
        if not isinstance(claim, dict) or set(claim) != required:
            raise ValueError("claim has missing or unknown fields")
        claim_id = claim["claim_id"]
        if not isinstance(claim_id, str) or not CLAIM_ID_RE.fullmatch(claim_id):
            raise ValueError("invalid claim_id")
        if claim_id in claim_ids:
            raise ValueError(f"duplicate claim_id: {claim_id}")
        claim_ids.add(claim_id)
        for field in ("claim_text", "rationale"):
            if not isinstance(claim[field], str) or not claim[field].strip():
                raise ValueError(f"{field} must be a non-empty string")
        if not isinstance(claim["classification"], str) or claim["classification"] not in CLAIM_CLASSES:
            raise ValueError("unsupported claim classification")
        if not isinstance(claim["review_status"], str) or claim["review_status"] not in REVIEW_STATUSES:
            raise ValueError("unsupported claim review_status")
        if not isinstance(claim["evidence"], list):
            raise ValueError("evidence must be a list")
        if claim["classification"] in {"source_confirmed", "source_claim"} and not claim["evidence"]:
            raise ValueError(f"{claim['classification']} claims require evidence")
        if claim["classification"] == "source_confirmed" and claim["review_status"] != "human_verified":
            raise ValueError("source_confirmed claims require human_verified review status")

        seen_evidence = set()
        for evidence in claim["evidence"]:
            if not isinstance(evidence, dict) or set(evidence) != {"source_id", "segment_id", "quote"}:
                raise ValueError("evidence must contain only source_id, segment_id, and quote")
            source_id, segment_id, quote = evidence["source_id"], evidence["segment_id"], evidence["quote"]
            if not isinstance(source_id, str) or source_id not in sources:
                raise ValueError("evidence references an unregistered source")
            if not isinstance(segment_id, str) or segment_id not in segments:
                raise ValueError("evidence references an unregistered transcript segment")
            segment = segments[segment_id]
            if segment["source_id"] != source_id:
                raise ValueError("evidence source_id does not match the transcript segment")
            if not isinstance(quote, str) or not quote.strip() or quote not in segment["text"]:
                raise ValueError("evidence quote must exactly match registered transcript text")
            key = (source_id, segment_id, quote)
            if key in seen_evidence:
                raise ValueError("duplicate evidence reference")
            seen_evidence.add(key)

        group = claim["contradiction_group"]
        if group is not None:
            if not isinstance(group, str) or not group.strip():
                raise ValueError("contradiction_group must be a non-empty string or null")
            contradiction_groups.setdefault(group, []).append(claim_id)

    return {
        "schema_version": 1,
        "claim_count": len(claim_ids),
        "contradiction_groups": {
            group: ids for group, ids in contradiction_groups.items() if len(ids) > 1
        },
        "scope": "provenance_validation_not_truth_verification",
    }
