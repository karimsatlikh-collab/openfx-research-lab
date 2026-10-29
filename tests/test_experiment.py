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


    def test_rejects_impossible_calendar_dates(self):
        with self.assertRaises(ValueError):
            new_experiment("test-date", "h", "v1", "EURUSD", "M15", "2024-99-99", "2024-12-31")

    def test_rejects_non_iso_date_shape(self):
        with self.assertRaises(ValueError):
            new_experiment("test-date", "h", "v1", "EURUSD", "M15", "20240101", "2024-12-31")

    def test_completed_requires_non_empty_structured_result(self):
        queued = sample()
        running = transition(queued, "RUNNING")
        with self.assertRaises(ValueError):
            transition(running, "COMPLETED")
        with self.assertRaises(ValueError):
            transition(running, "COMPLETED", result={})

    def test_manifest_rejects_invalid_nested_dates(self):
        from openfx.experiment import validate_manifest
        manifest = sample()
        manifest["market"]["data_start"] = "2024-99-99"
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_manifest_rejects_timezone_free_timestamp(self):
        from openfx.experiment import validate_manifest
        manifest = sample()
        manifest["created_at_utc"] = "2024-01-01T00:00:00"
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_constructor_rejects_non_object_parameters(self):
        with self.assertRaises(ValueError):
            new_experiment("test-params", "h", "v1", "EURUSD", "M15",
                           "2024-01-01", "2024-02-01", parameters=["unsafe"])

    def test_constructor_rejects_non_finite_parameter(self):
        with self.assertRaises(ValueError):
            new_experiment("test-nan", "h", "v1", "EURUSD", "M15",
                           "2024-01-01", "2024-02-01", parameters={"x": float("nan")})

    def test_manifest_rejects_unknown_root_fields(self):
        from openfx.experiment import validate_manifest
        manifest = sample()
        manifest["unexpected"] = True
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_manifest_rejects_artifact_path_traversal(self):
        from openfx.experiment import validate_manifest
        manifest = sample()
        manifest["artifacts"] = [{
            "path": "../secret.txt",
            "size_bytes": 1,
            "sha256": "a" * 64,
        }]
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_running_manifest_requires_start_timestamp(self):
        from openfx.experiment import validate_manifest
        manifest = sample()
        manifest["status"] = "RUNNING"
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_completed_manifest_requires_finished_timestamp(self):
        from openfx.experiment import validate_manifest
        manifest = sample()
        manifest["status"] = "COMPLETED"
        manifest["result"] = {"kind": "mock"}
        with self.assertRaises(ValueError):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
