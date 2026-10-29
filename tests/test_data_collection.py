import json
import tempfile
import unittest
from pathlib import Path

from data_collection import collect_local_metadata, save_metadata
from evaluation import evaluate_records


class DataCollectionTests(unittest.TestCase):
    def test_collects_metadata_only_for_supported_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.txt").write_text("synthetic fixture", encoding="utf-8")
            (root / "ignore.exe").write_text("not collected", encoding="utf-8")

            records = collect_local_metadata(str(root))

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["file_name"], "sample.txt")
            self.assertEqual(records[0]["relative_path"], "sample.txt")
            self.assertEqual(records[0]["collection_method"], "authorized_local_file_scan")
            self.assertFalse(records[0]["content_extracted"])
            self.assertEqual(len(records[0]["sha256"]), 64)

    def test_missing_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "does-not-exist"
            with self.assertRaises(FileNotFoundError):
                collect_local_metadata(str(missing))

    def test_root_relative_paths_disambiguate_duplicate_basenames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first").mkdir()
            (root / "second").mkdir()
            (root / "first" / "notes.txt").write_text("one", encoding="utf-8")
            (root / "second" / "notes.txt").write_text("two", encoding="utf-8")

            records = collect_local_metadata(str(root))
            paths = {record["relative_path"] for record in records}
            self.assertEqual(paths, {"first/notes.txt", "second/notes.txt"})

    def test_symlink_to_file_outside_selected_root_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "selected"
            root.mkdir()
            outside = parent / "outside.txt"
            outside.write_text("outside the selected root", encoding="utf-8")
            link = root / "linked.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are not supported by this environment")

            records = collect_local_metadata(str(root))
            self.assertEqual(records, [])

    def test_metadata_can_be_saved_and_evaluated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.csv"
            source.write_text("a,b\n1,2\n", encoding="utf-8")
            records = collect_local_metadata(str(root))
            output = root / "metadata.json"
            save_metadata(records, str(output))
            loaded = json.loads(output.read_text(encoding="utf-8"))
            result = evaluate_records(loaded)
            self.assertEqual(result["total_records"], 1)
            self.assertEqual(result["quality_status"], "passed_basic_checks")

    def test_duplicate_hashes_are_reported(self):
        records = [
            {"file_name": "a.txt", "file_type": ".txt", "file_size_bytes": 1,
             "sha256": "same", "collection_method": "test"},
            {"file_name": "b.txt", "file_type": ".txt", "file_size_bytes": 1,
             "sha256": "same", "collection_method": "test"},
        ]
        result = evaluate_records(records)
        self.assertEqual(result["duplicate_records"], 1)
        self.assertEqual(result["quality_status"], "needs_review")


if __name__ == "__main__":
    unittest.main()
