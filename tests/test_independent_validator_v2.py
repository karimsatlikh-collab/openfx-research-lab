import base64
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator

from openfx.independent_validator_v2 import (
    DOMAIN, MAX_ARTIFACT_SIZE_BYTES, ValidationError, canonical_bytes,
    sha256_bytes, validate_independently,
)


NOW = datetime.now(timezone.utc).replace(microsecond=0)
NOW_TEXT = NOW.isoformat().replace("+00:00", "Z")
NONCE = "nonce_1234567890abcdef"


class IndependentValidatorV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.artifact = self.artifacts / "report.json"
        self.artifact.write_text('{"synthetic_result":"fixture"}', encoding="utf-8")
        self.private_key = Ed25519PrivateKey.generate()
        public_raw = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.job = {
            "schema_version": 2,
            "job_id": "job-v2-001",
            "requested_engine": "synthetic",
            "implementation": {"build_sha256": "a" * 64},
            "authorization": {"nonce": NONCE},
            "expected_outputs": ["report.json"],
        }
        job_digest = sha256_bytes(canonical_bytes(self.job))
        artifact_bytes = self.artifact.read_bytes()
        self.run = {
            "schema_version": 2,
            "run_id": "run-v2-001",
            "job_id": self.job["job_id"],
            "status": "COMPLETED",
            "evidence_level": "synthetic",
            "timestamps": {"finished_at_utc": (NOW - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")},
            "inputs": {
                "job_spec_sha256": job_digest,
                "implementation_sha256": "a" * 64,
            },
            "outputs": [{
                "path": "report.json",
                "size_bytes": len(artifact_bytes),
                "sha256": sha256_bytes(artifact_bytes),
            }],
        }
        self.trust_store = {
            "schema_version": 1,
            "keys": [{
                "key_id": "executor-key-v2",
                "executor_id": "executor-local-v2",
                "algorithm": "Ed25519",
                "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
                "not_before_utc": (NOW - timedelta(days=30)).isoformat().replace("+00:00", "Z"),
                "not_after_utc": (NOW + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
                "revoked": False,
                "allowed_engines": ["synthetic"],
            }],
        }
        self.attestation = {
            "key_id": "executor-key-v2",
            "executor_id": "executor-local-v2",
            "job_id": self.job["job_id"],
            "run_id": self.run["run_id"],
            "job_spec_sha256": job_digest,
            "run_record_sha256": sha256_bytes(canonical_bytes(self.run)),
            "engine": "synthetic",
            "implementation_sha256": "a" * 64,
            "nonce": NONCE,
            "issued_at_utc": (NOW - timedelta(seconds=10)).isoformat().replace("+00:00", "Z"),
            "expires_at_utc": (NOW + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        }
        self.sign()

    def tearDown(self):
        self.temp.cleanup()

    def sign(self):
        claims = {key: value for key, value in self.attestation.items() if key != "signature"}
        signature = self.private_key.sign(DOMAIN + canonical_bytes(claims))
        self.attestation["signature"] = base64.b64encode(signature).decode("ascii")

    def refresh_bindings_and_sign(self):
        self.run["inputs"]["job_spec_sha256"] = sha256_bytes(canonical_bytes(self.job))
        self.attestation["job_spec_sha256"] = sha256_bytes(canonical_bytes(self.job))
        self.attestation["run_record_sha256"] = sha256_bytes(canonical_bytes(self.run))
        self.sign()

    def verify(self):
        return validate_independently(
            self.job, self.run, self.attestation, self.trust_store,
            self.artifacts,
        )

    def test_valid_signature_binds_complete_run_and_artifact(self):
        result = self.verify()
        self.assertTrue(result["valid"])
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["run_record_sha256"], self.attestation["run_record_sha256"])
        self.assertEqual(result["verified_artifact_count"], 1)
        self.assertNotIn("synthetic_result", json.dumps(result))

    def test_v2_envelopes_match_versioned_schemas(self):
        schema_root = Path(__file__).resolve().parents[1] / "schemas"
        for filename, document in (
            ("independent-job-v2.schema.json", self.job),
            ("independent-run-v2.schema.json", self.run),
            ("executor-attestation-v2.schema.json", self.attestation),
            ("executor-trust-store-v1.schema.json", self.trust_store),
        ):
            schema = json.loads((schema_root / filename).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(document)

    def test_run_record_mutation_after_signing_is_rejected(self):
        self.run["outputs"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_RUN_RECORD_MISMATCH")

    def test_run_timestamp_mutation_after_signing_is_rejected(self):
        self.run["timestamps"]["finished_at_utc"] = (NOW - timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_RUN_RECORD_MISMATCH")

    def test_expected_output_set_is_enforced(self):
        self.job["expected_outputs"] = ["report.json", "second.json"]
        self.refresh_bindings_and_sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "RUN_OUTPUT_SET_MISMATCH")

    def test_modified_signed_claim_is_rejected(self):
        self.attestation["engine"] = "mt5-demo"
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_BINDING_MISMATCH")

    def test_invalid_signature_is_rejected(self):
        self.attestation["signature"] = base64.b64encode(b"x" * 64).decode("ascii")
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "SIGNATURE_INVALID")

    def test_missing_run_digest_is_rejected(self):
        self.attestation.pop("run_record_sha256")
        self.sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_SHAPE")

    def test_unknown_key_is_rejected(self):
        self.attestation["key_id"] = "unknown-key"
        self.sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "UNKNOWN_OR_DUPLICATE_KEY")

    def test_revoked_key_is_rejected(self):
        self.trust_store["keys"][0]["revoked"] = True
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "KEY_REVOKED")

    def test_artifact_hash_mismatch_is_rejected(self):
        self.run["outputs"][0]["sha256"] = "0" * 64
        self.refresh_bindings_and_sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_HASH_MISMATCH")

    def test_artifact_path_traversal_is_rejected(self):
        self.run["outputs"][0]["path"] = "../report.json"
        self.job["expected_outputs"] = ["../report.json"]
        self.refresh_bindings_and_sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_PATH_ESCAPE")

    def test_final_symlink_is_rejected(self):
        link = self.artifacts / "link.json"
        try:
            link.symlink_to(self.artifact)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.job["expected_outputs"] = ["link.json"]
        self.run["outputs"][0]["path"] = "link.json"
        self.refresh_bindings_and_sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_SYMLINK_OR_NOT_DIRECTORY")

    def test_intermediate_directory_symlink_is_rejected(self):
        real_dir = self.artifacts / "real"
        real_dir.mkdir()
        (real_dir / "report.json").write_text("safe", encoding="utf-8")
        link_dir = self.artifacts / "linkdir"
        try:
            link_dir.symlink_to(real_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlink creation unavailable")
        relative = "linkdir/report.json"
        self.job["expected_outputs"] = [relative]
        self.run["outputs"] = [{
            "path": relative,
            "size_bytes": 4,
            "sha256": sha256_bytes(b"safe"),
        }]
        self.refresh_bindings_and_sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_SYMLINK_OR_NOT_DIRECTORY")

    def test_artifact_size_limit_is_enforced_before_read(self):
        oversized = self.artifacts / "oversized.bin"
        with oversized.open("wb") as stream:
            stream.truncate(MAX_ARTIFACT_SIZE_BYTES + 1)
        self.job["expected_outputs"] = ["oversized.bin"]
        self.run["outputs"] = [{
            "path": "oversized.bin",
            "size_bytes": MAX_ARTIFACT_SIZE_BYTES + 1,
            "sha256": "0" * 64,
        }]
        self.refresh_bindings_and_sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_SIZE_INVALID")

    def test_cli_does_not_accept_caller_supplied_clock(self):
        result = subprocess.run(
            [sys.executable, "-m", "openfx.independent_validator_v2",
             "--job", "missing", "--run", "missing", "--attestation", "missing",
             "--trust-store", "missing", "--artifact-root", str(self.artifacts),
             "--now-utc", NOW_TEXT],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)

    def test_cli_uses_system_clock_and_returns_bounded_report(self):
        paths = {}
        for name, value in (("job.json", self.job), ("run.json", self.run),
                            ("attestation.json", self.attestation), ("trust.json", self.trust_store)):
            path = self.root / name
            path.write_text(json.dumps(value), encoding="utf-8")
            paths[name] = path
        result = subprocess.run(
            [sys.executable, "-m", "openfx.independent_validator_v2",
             "--job", str(paths["job.json"]), "--run", str(paths["run.json"]),
             "--attestation", str(paths["attestation.json"]),
             "--trust-store", str(paths["trust.json"]), "--artifact-root", str(self.artifacts)],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(len(report["validator_source_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
