"""Fail-closed bridge from the legacy source/transcript registry to canonical M1 provenance.

The bridge is deliberately one-way. It validates the legacy records, requires the
actual source bytes, preserves timestamp locators and exact quotes, and never
promotes legacy review labels into stronger epistemic claims.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openfx.evidence import validate_claim_register
from openfx.source_provenance import (
    build_atomic_claim,
    build_source_record,
    validate_source_record as validate_m1_source_record,
)
from openfx.source_registry import validate_source_registry

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
_RIGHTS = {"owner_created", "explicit_permission", "public_domain", "licensed"}


class SourceEvidenceBridgeError(ValueError):
    """Raised when legacy evidence cannot be safely represented by M1."""


def _schema_validate(document: dict[str, Any], filename: str) -> None:
    try:
        schema = json.loads((_SCHEMA_DIR / filename).read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)
    except Exception as exc:
        raise SourceEvidenceBridgeError(
            f"canonical M1 schema validation failed ({filename}): {exc}"
        ) from exc


def _timestamp_locator(url: str, segment: dict[str, Any]) -> str:
    start, end = segment["start_seconds"], segment["end_seconds"]
    if start is None or end is None:
        return f"{url}#segment={segment['segment_id']}"
    return f"{url}#t={start:.3f},{end:.3f}"


def convert_legacy_evidence(
    *,
    source_registry: dict[str, Any],
    claim_register: dict[str, Any],
    claim_id: str,
    source_id: str,
    segment_id: str,
    source_content: bytes,
    rights_basis: str | None = None,
    permission_evidence: str | None = None,
    human_approval: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Convert one legacy claim/evidence edge to canonical SourceRecord + AtomicClaim.

    Rights conversion is intentionally conservative:
    - legacy public_domain maps only when a non-empty rights reference exists;
    - all other statuses require an explicit caller-supplied M1 rights decision;
    - explicit_permission additionally requires structured human approval.
    """
    if not isinstance(source_content, bytes) or not source_content:
        raise SourceEvidenceBridgeError("actual non-empty source_content bytes are required")

    try:
        registry = validate_source_registry(source_registry)
        validate_claim_register(claim_register, registry)
    except (TypeError, ValueError) as exc:
        raise SourceEvidenceBridgeError(f"legacy provenance validation failed: {exc}") from exc

    sources = {row["source_id"]: row for row in registry["sources"]}
    segments = {row["segment_id"]: row for row in registry["transcript_segments"]}
    source = sources.get(source_id)
    segment = segments.get(segment_id)
    if source is None:
        raise SourceEvidenceBridgeError("source_id is not present in validated source registry")
    if segment is None:
        raise SourceEvidenceBridgeError("segment_id is not present in validated transcript registry")
    if segment["source_id"] != source_id:
        raise SourceEvidenceBridgeError("source/segment identity mismatch")

    actual_source_hash = hashlib.sha256(source_content).hexdigest()
    recorded_source_hash = source.get("content_sha256")
    if recorded_source_hash is not None and recorded_source_hash.lower() != actual_source_hash:
        raise SourceEvidenceBridgeError("source content hash does not match legacy source record")

    legacy_claims = {row["claim_id"]: row for row in claim_register["claims"]}
    claim = legacy_claims.get(claim_id)
    if claim is None:
        raise SourceEvidenceBridgeError("claim_id is not present in validated claim register")
    if claim["classification"] not in {"source_confirmed", "source_claim"}:
        raise SourceEvidenceBridgeError(
            "only source_confirmed/source_claim classifications can map to AtomicClaim"
        )
    matching = [
        item for item in claim["evidence"]
        if item["source_id"] == source_id and item["segment_id"] == segment_id
    ]
    if len(matching) != 1:
        raise SourceEvidenceBridgeError("claim must contain exactly one matching source/segment edge")
    quote = matching[0]["quote"]
    if not quote or quote not in segment["text"]:
        raise SourceEvidenceBridgeError("evidence quote does not exactly match transcript segment")

    if rights_basis is None:
        if source["license_status"] == "public_domain" and source.get("license_reference"):
            resolved_rights = "public_domain"
            resolved_permission = source["license_reference"]
        else:
            raise SourceEvidenceBridgeError(
                "legacy rights status is not safely mappable; provide an explicit M1 rights decision"
            )
    else:
        if rights_basis not in _RIGHTS:
            raise SourceEvidenceBridgeError("unsupported explicit M1 rights_basis")
        resolved_rights = rights_basis
        resolved_permission = permission_evidence
        if not isinstance(resolved_permission, str) or not resolved_permission.strip():
            raise SourceEvidenceBridgeError("explicit M1 rights decision requires permission_evidence")

    locator = _timestamp_locator(source["url"], segment)
    try:
        canonical_source = build_source_record(
            source_id=source_id,
            identity=" — ".join(part for part in (source["title"], source.get("author")) if part),
            rights_basis=resolved_rights,
            permission_evidence=resolved_permission,
            retrieved_at_utc=source["collected_at_utc"],
            exact_locator=locator,
            capture_method=f"{source['access_method']}:{segment['extraction_method']}",
            content=source_content,
            provenance_state="code_reviewed_only",
            human_approval=human_approval,
        )
        validate_m1_source_record(canonical_source, source_content)
        canonical_claim = build_atomic_claim(
            claim_id=claim_id,
            source_record=canonical_source,
            source_content=source_content,
            exact_locator=locator,
            statement=claim["claim_text"],
            # Legacy human_verified/source_confirmed labels are not promoted.
            provenance_state="code_reviewed_only",
        )
    except (TypeError, ValueError) as exc:
        raise SourceEvidenceBridgeError(f"canonical M1 conversion failed: {exc}") from exc

    _schema_validate(canonical_source, "source-record-v1.schema.json")
    _schema_validate(canonical_claim, "atomic-claim-v1.schema.json")
    return {
        "schema_version": 1,
        "source_record": canonical_source,
        "atomic_claim": canonical_claim,
        "trace": {
            "legacy_source_id": source_id,
            "legacy_segment_id": segment_id,
            "legacy_claim_id": claim_id,
            "timestamp_locator": locator,
            "quote": quote,
            "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            "segment_text_sha256": segment["text_sha256"],
            "segment_start_seconds": segment["start_seconds"],
            "segment_end_seconds": segment["end_seconds"],
            "extraction_method": segment["extraction_method"],
            "source_content_sha256": actual_source_hash,
            "legacy_classification": claim["classification"],
            "legacy_review_status": claim["review_status"],
            "canonical_provenance_state": "code_reviewed_only",
        },
        "limitations": [
            "Conversion validates traceability and structure, not source authenticity or factual truth.",
            "A legacy review label is preserved as metadata and is not promoted to verified fact.",
            "The caller-supplied rights decision is recorded, not independently legally verified.",
            "The transcript text hash is not a substitute for the original source-content hash.",
        ],
    }
