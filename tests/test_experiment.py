import tempfile
import unittest
from pathlib import Path

from openfx.experiment import load_manifest, new_experiment, save_manifest, transition
from openfx.mock_worker import run_mock


def sample():
    return new_experiment(
        experiment_id="test-001",
        hypothesis="Synthetic lifecycle test only",
        strategy_version="unimplemented",
        symbol="EURUSD",
        timeframe="M15",
        data_start="2024-01-01",
        data_end="2024-06-30",
        parameters={"fixture": True},
    )


class ExperimentTests(unittest.TestCase):
    def test_new_manifest_starts_queued(self):
        manifest = sample()
        self.assertEqual(manifest["status"], "QUEUED")
        self.assertEqual(manifest["schema_version"], 1)

    def test_rejects_invalid_id(self):
        with self.assertRaises(ValueError):
            new_experiment("../unsafe", "h", "v1", "EURUSD", "M15", "2024-01-01", "2024-02-01")

    def test_rejects_reverse_date_range(self):
        with self.assertRaises(ValueError):
            new_experiment("test", "h", "v1", "EURUSD", "M15", "2024-02-01", "2024-01-01")

    def test_illegal_transition_is_rejected(self):
        with self.assertRaises(ValueError):
            transition(sample(), "COMPLETED")

    def test_manifest_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.json"
            save_manifest(sample(), path)
            loaded = load_manifest(path)
            self.assertEqual(loaded["experiment_id"], "test-001")

    def test_mock_worker_lifecycle_is_not_a_backtest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.json"
            save_manifest(sample(), path)
            result = run_mock(path)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertFalse(result["result"]["is_backtest"])
            self.assertFalse(result["result"]["is_trading_signal"])
            self.assertEqual(load_manifest(path)["status"], "COMPLETED")

    def test_mock_worker_does_not_rerun_completed_job(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.json"
            save_manifest(sample(), path)
            run_mock(path)
            with self.assertRaises(ValueError):
                run_mock(path)


    def test_artifact_record_hashes_file_and_rejects_escape(self):
        from openfx.experiment import artifact_record

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "report.txt"
            artifact.write_text("reproducible artifact", encoding="utf-8")
            record = artifact_record(artifact, root)
            self.assertEqual(record["path"], "report.txt")
            self.assertEqual(record["size_bytes"], len("reproducible artifact"))
            self.assertEqual(len(record["sha256"]), 64)
            outside = root.parent / f"{root.name}-outside-openfx-test.txt"
            try:
                outside.write_text("outside", encoding="utf-8")
                with self.assertRaises(ValueError):
                    artifact_record(outside, root)
            finally:
                outside.unlink(missing_ok=True)



if __name__ == "__main__":
    unittest.main()
