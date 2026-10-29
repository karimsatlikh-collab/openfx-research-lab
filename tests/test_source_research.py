import hashlib
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from openfx.source_registry import (
    load_source_registry,
    make_source_record,
    new_source_registry,
    save_source_registry,
    validate_source_record,
    validate_source_registry,
    validate_transcript_segment,
)
from openfx.transcript_quality import compare_transcript_fidelity


def source_record(**overrides):
    record = {
        "source_id": "source-001",
        "source_type": "video",
        "url": "https://example.com/video/1",
        "title": "Synthetic source fixture",
        "author": "Example author",
        "published_date": "2025-01-01",
        "license_status": "unknown",
        "license_reference": None,
        "access_method": "manual",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_sha256": None,
        "notes": "Synthetic test data",
    }
    record.update(overrides)
    return record


class SourceRegistryTests(unittest.TestCase):
    def test_accepts_source_with_explicit_unknown_rights(self):
        record = validate_source_record(source_record())
        self.assertEqual(record["license_status"], "unknown")

    def test_rejects_url_credentials(self):
        with self.assertRaises(ValueError):
            validate_source_record(source_record(url="https://user:pass@example.com/video"))

    def test_rejects_impossible_publication_date(self):
        with self.assertRaises(ValueError):
            validate_source_record(source_record(published_date="2025-99-01"))

    def test_permitted_license_requires_evidence_reference(self):
        with self.assertRaises(ValueError):
            validate_source_record(source_record(license_status="reviewed_permitted"))

    def test_content_hash_is_reproducible(self):
        record = make_source_record(
            source_id="source-002", source_type="transcript",
            url="https://example.com/transcript", title="Synthetic transcript",
            content=b"hello", access_method="user_provided",
        )
        self.assertEqual(record["content_sha256"], hashlib.sha256(b"hello").hexdigest())

    def test_transcript_segment_requires_registered_source_and_matching_hash(self):
        text = "The setup is not valid at 1.25 ATR."
        segment = {
            "segment_id": "segment-001",
            "source_id": "source-001",
            "start_seconds": 10.0,
            "end_seconds": 12.0,
            "text": text,
            "extraction_method": "manual_review",
            "confidence": 0.95,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        self.assertEqual(validate_transcript_segment(segment, {"source-001"})["text"], text)
        with self.assertRaises(ValueError):
            validate_transcript_segment(segment, set())
        with self.assertRaises(ValueError):
            validate_transcript_segment({**segment, "text_sha256": "0" * 64}, {"source-001"})

    def test_transcript_segment_rejects_non_finite_timestamp(self):
        segment = {
            "segment_id": "segment-001", "source_id": "source-001",
            "start_seconds": float("nan"), "end_seconds": 12.0,
            "text": "text", "extraction_method": "manual_review",
            "confidence": 0.5, "text_sha256": hashlib.sha256(b"text").hexdigest(),
        }
        with self.assertRaises(ValueError):
            validate_transcript_segment(segment, {"source-001"})


    def test_empty_registry_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            registry = new_source_registry()
            save_source_registry(registry, path)
            self.assertEqual(load_source_registry(path), registry)

    def test_registry_rejects_duplicate_source_ids(self):
        record = source_record()
        registry = {"schema_version": 1, "sources": [record, record], "transcript_segments": []}
        with self.assertRaisesRegex(ValueError, "duplicate source_id"):
            validate_source_registry(registry)

    def test_registry_rejects_orphan_transcript_segment(self):
        registry = {
            "schema_version": 1, "sources": [],
            "transcript_segments": [{
                "segment_id": "segment-001", "source_id": "missing-source",
                "start_seconds": 0, "end_seconds": 1, "text": "text",
                "extraction_method": "manual", "confidence": 1,
                "text_sha256": hashlib.sha256(b"text").hexdigest(),
            }],
        }
        with self.assertRaisesRegex(ValueError, "not registered"):
            validate_source_registry(registry)

    def test_malformed_source_type_is_rejected_cleanly(self):
        with self.assertRaises(ValueError):
            validate_source_record(source_record(source_type=[]))


class TranscriptFidelityTests(unittest.TestCase):
    def test_exact_transcript_passes_selected_checks(self):
        text = "Do not enter below 1.5 ATR on 2025-01-02."
        result = compare_transcript_fidelity(text, text)
        self.assertEqual(result["status"], "pass_selected_checks")
        self.assertEqual(result["flags"], [])

    def test_dropped_negation_and_changed_number_are_flagged(self):
        reference = "Do not enter below 1.5 ATR."
        extracted = "Do enter below 2.5 ATR."
        result = compare_transcript_fidelity(reference, extracted)
        self.assertIn("negation_mismatch", result["flags"])
        self.assertIn("missing_or_changed_numbers", result["flags"])
        self.assertIn("unexpected_numbers", result["flags"])
        self.assertEqual(result["status"], "needs_human_review")


    def test_signed_number_change_is_flagged(self):
        result = compare_transcript_fidelity("Use -5 points.", "Use 5 points.")
        self.assertIn("missing_or_changed_numbers", result["flags"])
        self.assertIn("unexpected_numbers", result["flags"])

    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_transcript_fidelity("source words", "   ")

    def test_persian_negation_change_is_flagged(self):
        result = compare_transcript_fidelity("این سطح معتبر نیست", "این سطح معتبر است")
        self.assertIn("negation_mismatch", result["flags"])


if __name__ == "__main__":
    unittest.main()
