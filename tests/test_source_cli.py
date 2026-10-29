import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from openfx.source_cli import main
from openfx.source_registry import load_source_registry


class SourceCliTests(unittest.TestCase):
    def invoke(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_init_register_and_import_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "sources.json"
            transcript = root / "captions.srt"
            transcript.write_text(
                "1\n00:00:01,000 --> 00:00:02,000\nDo not enter.\n",
                encoding="utf-8",
            )
            self.assertEqual(self.invoke(["init", "--output", str(registry)])[0], 0)
            code, _, err = self.invoke([
                "add-source", "--registry", str(registry),
                "--source-id", "video-001", "--type", "video",
                "--url", "https://example.com/video", "--title", "Synthetic video",
            ])
            self.assertEqual((code, err), (0, ""))
            code, out, err = self.invoke([
                "import-transcript", "--registry", str(registry),
                "--source-id", "video-001", "--input", str(transcript),
            ])
            self.assertEqual((code, err), (0, ""))
            self.assertIn("Imported 1 transcript segments", out)
            loaded = load_source_registry(registry)
            self.assertEqual(loaded["transcript_segments"][0]["text"], "Do not enter.")

    def test_cli_init_refuses_to_overwrite_existing_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            self.assertEqual(self.invoke(["init", "--output", str(path)])[0], 0)
            code, _, err = self.invoke(["init", "--output", str(path)])
            self.assertEqual(code, 2)
            self.assertIn("refusing to overwrite", err)
            self.assertEqual(json.loads(path.read_text())["sources"], [])

    def test_cli_blocks_import_from_restricted_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "sources.json"
            transcript = root / "captions.txt"
            transcript.write_text("Sensitive transcript", encoding="utf-8")
            self.invoke(["init", "--output", str(registry)])
            code, _, _ = self.invoke([
                "add-source", "--registry", str(registry),
                "--source-id", "video-001", "--type", "video",
                "--url", "https://example.com/video", "--title", "Restricted source",
                "--license-status", "restricted",
            ])
            self.assertEqual(code, 0)
            code, _, err = self.invoke([
                "import-transcript", "--registry", str(registry),
                "--source-id", "video-001", "--input", str(transcript),
            ])
            self.assertEqual(code, 2)
            self.assertIn("rights status", err)
            self.assertEqual(load_source_registry(registry)["transcript_segments"], [])


if __name__ == "__main__":
    unittest.main()
