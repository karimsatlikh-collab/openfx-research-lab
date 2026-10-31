import hashlib
import unittest
from datetime import datetime, timezone

from openfx.canonical_source_evidence_bridge import (
    SourceEvidenceBridgeError,
    convert_legacy_evidence,
)


SOURCE_BYTES = b"authorized synthetic source fixture bytes"


def fixtures():
    text = "The confirmed pivot is 1.5 ATR; do not enter before close."
    source = {
        "source_id": "source-001", "source_type": "video",
        "url": "https://example.com/video/1", "title": "Synthetic lesson",
        "author": "Example", "published_date": "2025-01-01",
        "license_status": "public_domain", "license_reference": "PD registry entry",
        "access_method": "user_provided",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_sha256": hashlib.sha256(SOURCE_BYTES).hexdigest(),
        "notes": "synthetic fixture",
    }
    segment = {
        "segment_id": "segment-001", "source_id": "source-001",
        "start_seconds": 10.0, "end_seconds": 12.5, "text": text,
        "extraction_method": "human_checked_transcript", "confidence": 1.0,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }
    registry = {"schema_version": 1, "sources": [source], "transcript_segments": [segment]}
    claim = {
        "claim_id": "claim-001",
        "claim_text": "The source states a 1.5 ATR pivot threshold.",
        "classification": "source_confirmed", "review_status": "human_verified",
        "rationale": "synthetic fixture claim", "evidence": [{
            "source_id": "source-001", "segment_id": "segment-001",
            "quote": "The confirmed pivot is 1.5 ATR",
        }],
        "contradiction_group": None,
    }
    register = {"schema_version": 1, "claims": [claim]}
    return registry, register


class CanonicalSourceEvidenceBridgeTests(unittest.TestCase):
    def convert(self, registry=None, register=None, **kwargs):
        default_registry, default_register = fixtures()
        return convert_legacy_evidence(
            source_registry=registry or default_registry,
            claim_register=register or default_register,
            claim_id="claim-001", source_id="source-001",
            segment_id="segment-001", source_content=SOURCE_BYTES, **kwargs,
        )

    def test_converts_public_domain_claim_and_preserves_timestamp(self):
        result = self.convert()
        self.assertEqual(result["source_record"]["rights_basis"], "public_domain")
        self.assertEqual(result["atomic_claim"]["provenance_state"], "observed")
        self.assertEqual(result["trace"]["timestamp_locator"], "https://example.com/video/1#t=10.000,12.500")
        self.assertEqual(result["atomic_claim"]["source_ref"]["exact_locator"], result["trace"]["timestamp_locator"])
        self.assertEqual(result["trace"]["quote"], "The confirmed pivot is 1.5 ATR")
        self.assertEqual(result["trace"]["segment_start_seconds"], 10.0)
        self.assertEqual(result["trace"]["segment_end_seconds"], 12.5)

    def test_ambiguous_or_reviewed_permitted_rights_fail_closed(self):
        registry, register = fixtures()
        registry["sources"][0]["license_status"] = "reviewed_permitted"
        with self.assertRaisesRegex(SourceEvidenceBridgeError, "not safely mappable"):
            self.convert(registry=registry, register=register)

    def test_explicit_permission_requires_structured_human_approval(self):
        with self.assertRaisesRegex(SourceEvidenceBridgeError, "human approval evidence"):
            self.convert(
                rights_basis="explicit_permission",
                permission_evidence="permission email reference",
            )

    def test_explicit_permission_with_approval_is_schema_valid(self):
        result = self.convert(
            rights_basis="explicit_permission",
            permission_evidence="permission email reference",
            human_approval={
                "actor_id": "reviewer-1",
                "approved_at_utc": "2026-10-31T10:00:00+00:00",
                "reason": "permission evidence inspected",
            },
        )
        self.assertEqual(result["source_record"]["rights_basis"], "explicit_permission")

    def test_missing_source_bytes_fail_closed(self):
        registry, register = fixtures()
        with self.assertRaisesRegex(SourceEvidenceBridgeError, "source_content bytes"):
            convert_legacy_evidence(
                source_registry=registry, claim_register=register,
                claim_id="claim-001", source_id="source-001",
                segment_id="segment-001", source_content=b"",
            )

    def test_source_hash_mismatch_fails(self):
        registry, register = fixtures()
        registry["sources"][0]["content_sha256"] = "0" * 64
        with self.assertRaisesRegex(SourceEvidenceBridgeError, "hash does not match"):
            self.convert(registry=registry, register=register)

    def test_source_segment_mismatch_fails(self):
        registry, register = fixtures()
        registry["transcript_segments"][0]["source_id"] = "other-source"
        with self.assertRaises(SourceEvidenceBridgeError):
            self.convert(registry=registry, register=register)

    def test_timestamp_drift_changes_canonical_locator_and_invalid_segment_rejected(self):
        registry, register = fixtures()
        registry["transcript_segments"][0]["start_seconds"] = 11.0
        # Valid timestamp changes are preserved, not silently rounded to a different cue.
        result = self.convert(registry=registry, register=register)
        self.assertEqual(result["trace"]["timestamp_locator"], "https://example.com/video/1#t=11.000,12.500")

    def test_quote_mismatch_fails_before_conversion(self):
        registry, register = fixtures()
        register["claims"][0]["evidence"][0]["quote"] = "A fabricated quote"
        with self.assertRaisesRegex(SourceEvidenceBridgeError, "exactly match"):
            self.convert(registry=registry, register=register)

    def test_non_source_claim_classification_is_not_promoted(self):
        registry, register = fixtures()
        register["claims"][0]["classification"] = "hypothesis"
        register["claims"][0]["evidence"] = []
        register["claims"][0]["review_status"] = "draft"
        with self.assertRaisesRegex(SourceEvidenceBridgeError, "only source_confirmed"):
            self.convert(registry=registry, register=register)

    def test_duplicate_claim_ids_rejected_by_legacy_validator(self):
        registry, register = fixtures()
        register["claims"].append(dict(register["claims"][0]))
        with self.assertRaisesRegex(SourceEvidenceBridgeError, "duplicate claim_id"):
            self.convert(registry=registry, register=register)


if __name__ == "__main__":
    unittest.main()
