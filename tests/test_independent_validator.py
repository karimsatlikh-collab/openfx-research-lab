import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from openfx.independent_validator import (
    DOMAIN, ValidationError, canonical_bytes, sha256_bytes, validate_independently,
)


NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
NOW_TEXT = NOW.isoformat().replace("+00:00", "Z")
NONCE = "nonce_1234567890abcdef"


class IndependentValidatorTests(unittest.TestCase):
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
            "schema_version": 1,
            "job_id": "job-001",
            "requested_engine": "synthetic",
            "implementation": {"build_sha256": "a" * 64},
            "authorization": {"nonce": NONCE},
        }
        job_digest = sha256_bytes(canonical_bytes(self.job))
        artifact_bytes = self.artifact.read_bytes()
        self.run = {
            "schema_version": 1,
            "run_id": "run-001",
            "job_id": "job-001",
            "status": "COMPLETED",
            "evidence_level": "synthetic",
            "timestamps": {"finished_at_utc": "2026-10-30T11:59:30Z"},
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
                "key_id": "executor-key-1",
                "executor_id": "executor-local-1",
                "algorithm": "Ed25519",
                "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
                "not_before_utc": "2026-01-01T00:00:00Z",
                "not_after_utc": "2027-01-01T00:00:00Z",
                "revoked": False,
                "allowed_engines": ["synthetic"],
            }],
        }
        self.attestation = {
            "key_id": "executor-key-1",
            "executor_id": "executor-local-1",
            "job_id": "job-001",
            "run_id": "run-001",
            "job_spec_sha256": job_digest,
            "engine": "synthetic",
            "implementation_sha256": "a" * 64,
            "nonce": NONCE,
            "issued_at_utc": "2026-10-30T11:59:00Z",
            "expires_at_utc": "2026-10-30T12:05:00Z",
        }
        self.sign()

    def tearDown(self):
        self.temp.cleanup()

    def sign(self):
        claims = {k: v for k, v in self.attestation.items() if k != "signature"}
        signature = self.private_key.sign(DOMAIN + canonical_bytes(claims))
        self.attestation["signature"] = base64.b64encode(signature).decode("ascii")

    def verify(self):
        return validate_independently(
            self.job, self.run, self.attestation, self.trust_store,
            self.artifacts, now_utc=NOW_TEXT,
        )

    def test_valid_signature_and_artifact_pass(self):
        result = self.verify()
        self.assertTrue(result["valid"])
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["verified_artifact_count"], 1)
        self.assertNotIn("synthetic_result", json.dumps(result))

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

    def test_unknown_key_is_rejected(self):
        self.attestation["key_id"] = "unknown-key"
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "UNKNOWN_OR_DUPLICATE_KEY")

    def test_revoked_key_is_rejected(self):
        self.trust_store["keys"][0]["revoked"] = True
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "KEY_REVOKED")

    def test_expired_attestation_is_rejected(self):
        self.attestation["expires_at_utc"] = "2026-10-30T11:59:59Z"
        self.sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_EXPIRED_OR_FUTURE")

    def test_future_attestation_is_rejected(self):
        self.attestation["issued_at_utc"] = "2026-10-30T12:01:00Z"
        self.attestation["expires_at_utc"] = "2026-10-30T12:06:00Z"
        self.sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_EXPIRED_OR_FUTURE")

    def test_excessive_attestation_ttl_is_rejected(self):
        self.attestation["expires_at_utc"] = "2026-10-30T12:20:00Z"
        self.sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_TTL_TOO_LONG")

    def test_nonce_mismatch_is_rejected(self):
        self.attestation["nonce"] = "nonce_another_123456"
        self.sign()
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ATTESTATION_NONCE_MISMATCH")

    def test_job_digest_mismatch_is_rejected(self):
        self.run["inputs"]["job_spec_sha256"] = "0" * 64
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "RUN_JOB_DIGEST_MISMATCH")

    def test_artifact_tampering_is_rejected(self):
        self.artifact.write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_SIZE_MISMATCH")

    def test_artifact_path_traversal_is_rejected(self):
        self.run["outputs"][0]["path"] = "../report.json"
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_PATH_ESCAPE")

    def test_artifact_symlink_is_rejected(self):
        link = self.artifacts / "link.json"
        try:
            link.symlink_to(self.artifact)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this platform")
        self.run["outputs"][0]["path"] = "link.json"
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "ARTIFACT_SYMLINK")

    def test_run_engine_mismatch_is_rejected(self):
        self.run["evidence_level"] = "mt5-demo"
        with self.assertRaises(ValidationError) as ctx:
            self.verify()
        self.assertEqual(ctx.exception.reason_code, "RUN_ENGINE_MISMATCH")

    def test_cli_runs_as_separate_process_and_returns_bounded_report(self):
        files = {
            "job.json": self.job,
            "run.json": self.run,
            "attestation.json": self.attestation,
            "trust.json": self.trust_store,
        }
        for name, value in files.items():
            (self.root / name).write_text(json.dumps(value), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable, "-m", "openfx.independent_validator",
                "--job", str(self.root / "job.json"),
                "--run", str(self.root / "run.json"),
                "--attestation", str(self.root / "attestation.json"),
                "--trust-store", str(self.root / "trust.json"),
                "--artifact-root", str(self.artifacts),
                "--now-utc", NOW_TEXT,
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertNotIn("synthetic_result", result.stdout)

        self.attestation["signature"] = base64.b64encode(b"x" * 64).decode("ascii")
        (self.root / "attestation.json").write_text(json.dumps(self.attestation), encoding="utf-8")
        failed = subprocess.run(
            [
                sys.executable, "-m", "openfx.independent_validator",
                "--job", str(self.root / "job.json"),
                "--run", str(self.root / "run.json"),
                "--attestation", str(self.root / "attestation.json"),
                "--trust-store", str(self.root / "trust.json"),
                "--artifact-root", str(self.artifacts),
                "--now-utc", NOW_TEXT,
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(json.loads(failed.stdout)["reason_codes"], ["SIGNATURE_INVALID"])


if __name__ == "__main__":
    unittest.main()
