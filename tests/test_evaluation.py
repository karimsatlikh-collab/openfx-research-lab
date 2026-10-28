import unittest

from evaluation import evaluate_records


def make_record(**overrides):
    record = {
        "file_name": "sample.csv",
        "file_type": ".csv",
        "file_size_bytes": 100,
        "sha256": "abc123",
        "collection_method": "test",
    }
    record.update(overrides)
    return record


class TestEvaluation(unittest.TestCase):

    def test_empty_records(self):
        result = evaluate_records([])

        self.assertEqual(result["total_records"], 0)
        self.assertEqual(result["unique_files"], 0)
        self.assertEqual(result["quality_status"], "no_data")

    def test_complete_record(self):
        result = evaluate_records([make_record()])

        self.assertEqual(result["total_records"], 1)
        self.assertEqual(result["duplicate_records"], 0)
        self.assertEqual(
            result["quality_status"],
            "passed_basic_checks",
        )

    def test_missing_field(self):
        record = make_record(file_name="")

        result = evaluate_records([record])

        self.assertEqual(result["missing_fields"]["file_name"], 1)
        self.assertEqual(result["metadata_completeness"], 0.8)
        self.assertEqual(result["quality_status"], "needs_review")

    def test_duplicate_hashes(self):
        records = [
            make_record(file_name="first.csv"),
            make_record(file_name="second.csv"),
        ]

        result = evaluate_records(records)

        self.assertEqual(result["total_records"], 2)
        self.assertEqual(result["unique_files"], 1)
        self.assertEqual(result["duplicate_records"], 1)
        self.assertEqual(result["quality_status"], "needs_review")

    def test_empty_hashes(self):
        records = [
            make_record(sha256=""),
            make_record(sha256=""),
        ]

        result = evaluate_records(records)

        self.assertEqual(result["duplicate_records"], 0)
        self.assertEqual(result["unique_files"], 0)


if __name__ == "__main__":
    unittest.main()
