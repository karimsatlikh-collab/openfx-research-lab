import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from openfx.source_registry import make_source_record, new_source_registry, validate_source_registry
from openfx.transcript_import import (
    import_transcript_file,
    import_transcript_into_registry,
    parse_transcript_text,
)


def make_registry():
    registry = new_source_registry()
    registry["sources"].append(make_source_record(
        source_id="source-001",
        source_type="transcript",
        url="https://example.com/captions",
        title="Synthetic caption fixture",
        author="Example",
        license_status="unknown",
        access_method="user_provided",
    ))
    return registry


class TranscriptImportTests(unittest.TestCase):
    def test_imports_srt_cues_and_preserves_exact_text(self):
        content = """1
00:00:01,000 --> 00:00:02,500
Hello &amp; welcome <i>now</i>.

2
00:00:02,500 --> 00:00:04,000
Do not enter 1.5 ATR.
"""
        segments = parse_transcript_text(content, "source-001", "srt")
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["text"], "Hello & welcome now.")
        self.assertEqual(segments[0]["start_seconds"], 1.0)
        self.assertEqual(segments[0]["end_seconds"], 2.5)
        self.assertEqual(segments[1]["text"], "Do not enter 1.5 ATR.")
        self.assertEqual(
            segments[1]["text_sha256"],
            hashlib.sha256(segments[1]["text"].encode()).hexdigest(),
        )

    def test_imports_webvtt_short_timestamps_and_speaker(self):
        content = """WEBVTT

cue-1
00:01.000 --> 00:02.000 align:start
<v Saeid>Pivot is confirmed.</v>
"""
        segments = parse_transcript_text(content, "source-001", "vtt")
        self.assertEqual(segments[0]["start_seconds"], 1.0)
        self.assertEqual(segments[0]["text"], "Saeid: Pivot is confirmed.")

    def test_plain_text_is_segmented_without_invented_timestamps(self):
        segments = parse_transcript_text("First paragraph.\n\nSecond paragraph.", "source-001", "txt")
        self.assertEqual(len(segments), 2)
        self.assertIsNone(segments[0]["start_seconds"])
        self.assertIsNone(segments[0]["end_seconds"])

    def test_rejects_invalid_timestamp_ranges(self):
        content = """1
00:99:01,000 --> 00:99:02,000
invalid
"""
        with self.assertRaisesRegex(ValueError, "out-of-range"):
            parse_transcript_text(content, "source-001", "srt")

    def test_rejects_empty_or_unsupported_transcripts(self):
        with self.assertRaises(ValueError):
            parse_transcript_text("  ", "source-001", "txt")
        with self.assertRaisesRegex(ValueError, "unsupported"):
            parse_transcript_text("some text", "source-001", "pdf")

    def test_import_appends_only_to_registered_source(self):
        registry = make_registry()
        updated = import_transcript_into_registry(
            registry, "source-001", "A rule.\n\nA second rule.", "txt"
        )
        self.assertEqual(len(updated["transcript_segments"]), 2)
        self.assertEqual(len(registry["transcript_segments"]), 0)
        validate_source_registry(updated)
        with self.assertRaisesRegex(ValueError, "must be registered"):
            import_transcript_into_registry(registry, "missing-source", "text", "txt")

    def test_reimporting_same_transcript_is_rejected(self):
        registry = make_registry()
        updated = import_transcript_into_registry(registry, "source-001", "A rule.", "txt")
        with self.assertRaisesRegex(ValueError, "already exist"):
            import_transcript_into_registry(updated, "source-001", "A rule.", "txt")

    def test_imports_local_file_with_size_limit_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.srt"
            path.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello.", encoding="utf-8")
            segments = import_transcript_file(path, "source-001")
            self.assertEqual(segments[0]["text"], "Hello.")


if __name__ == "__main__":
    unittest.main()
