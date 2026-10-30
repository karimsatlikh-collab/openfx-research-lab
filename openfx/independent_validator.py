"""Standalone, read-only verifier for signed executor run claims.

This module intentionally imports no worker, strategy, or executor code.
It verifies claims and artifact bytes; it does not execute or assess a strategy.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DOMAIN = b"OPENFX_EXECUTOR_ATTESTATION_V1\n"
MAX_ATTESTATION_TTL = timedelta(minutes=15)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")


class ValidationError(ValueError):
    """A fail-closed validation error with a stable, non-sensitive reason code."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValidationError("NON_CANONICAL_JSON", "input cannot be canonically serialized") from exc


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("INVALID_TIMESTAMP", f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("INVALID_TIMESTAMP", f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValidationError("INVALID_TIMESTAMP", f"{field} must be explicitly UTC")
    return parsed.astimezone(timezone.utc)


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("INPUT_READ_FAILED", f"could not read {label} JSON") from exc
    if not isinstance(value, dict):
        raise ValidationError("INVALID_INPUT_SHAPE", f"{label} root must be an object")
    return value


def _require(condition: bool, reason: str, message: str) -> None:
    if not condition:
        raise ValidationError(reason, message)


def _load_trusted_key(
    trust_store: dict[str, Any], attestation: dict[str, Any], now: datetime
) -> Ed25519PublicKey:
    _require(trust_store.get("schema_version") == 1, "TRUST_STORE_VERSION", "unsupported trust-store version")
    entries = trust_store.get("keys")
    _require(isinstance(entries, list), "TRUST_STORE_INVALID", "trust-store keys must be a list")

    key_id = attestation.get("key_id")
    matches = [item for item in entries if isinstance(item, dict) and item.get("key_id") == key_id]
    _require(len(matches) == 1, "UNKNOWN_OR_DUPLICATE_KEY", "key ID is unknown or duplicated")
    entry = matches[0]

    _require(entry.get("revoked") is False, "KEY_REVOKED", "executor key is revoked")
    _require(entry.get("algorithm") == "Ed25519", "KEY_ALGORITHM", "only Ed25519 keys are accepted")
    _require(entry.get("executor_id") == attestation.get("executor_id"),
             "KEY_IDENTITY_MISMATCH", "key is not trusted for this executor identity")
    allowed = entry.get("allowed_engines")
    _require(isinstance(allowed, list) and attestation.get("engine") in allowed,
             "ENGINE_NOT_ALLOWED", "executor key is not authorized for this engine")

    valid_from = parse_utc(entry.get("not_before_utc"), "trust_store.not_before_utc")
    valid_until = parse_utc(entry.get("not_after_utc"), "trust_store.not_after_utc")
    _require(valid_from < valid_until, "TRUST_KEY_WINDOW", "trust-key validity window is invalid")
    _require(valid_from <= now <= valid_until, "KEY_OUTSIDE_VALIDITY", "executor key is outside its validity window")
    issued = parse_utc(attestation.get("issued_at_utc"), "attestation.issued_at_utc")
    expires = parse_utc(attestation.get("expires_at_utc"), "attestation.expires_at_utc")
    _require(valid_from <= issued and expires <= valid_until,
             "ATTESTATION_OUTSIDE_KEY_VALIDITY",
             "attestation validity must be contained within the trusted key validity window")

    encoded = entry.get("public_key_b64")
    _require(isinstance(encoded, str), "TRUST_KEY_INVALID", "trusted public key is missing")
    try:
        raw_key = base64.b64decode(encoded, validate=True)
        return Ed25519PublicKey.from_public_bytes(raw_key)
    except (ValueError, TypeError) as exc:
        raise ValidationError("TRUST_KEY_INVALID", "trusted Ed25519 public key is malformed") from exc


def _verify_attestation(
    attestation: dict[str, Any], trust_store: dict[str, Any],
    job: dict[str, Any], run: dict[str, Any], job_digest: str, now: datetime,
) -> dict[str, str]:
    required = (
        "key_id", "executor_id", "job_id", "run_id", "job_spec_sha256",
        "engine", "implementation_sha256", "nonce", "issued_at_utc",
        "expires_at_utc", "signature",
    )
    for field in required:
        _require(isinstance(attestation.get(field), str) and bool(attestation[field].strip()),
                 "ATTESTATION_FIELD_MISSING", f"attestation.{field} is required")

    implementation = job.get("implementation")
    _require(isinstance(implementation, dict), "JOB_IMPLEMENTATION_INVALID", "job implementation is required")
    expected = {
        "job_id": job.get("job_id"),
        "run_id": run.get("run_id"),
        "job_spec_sha256": job_digest,
        "engine": job.get("requested_engine"),
        "implementation_sha256": implementation.get("build_sha256"),
    }
    for field, expected_value in expected.items():
        _require(attestation.get(field) == expected_value,
                 "ATTESTATION_BINDING_MISMATCH", f"attestation.{field} does not match frozen inputs")

    authorization = job.get("authorization")
    _require(isinstance(authorization, dict), "JOB_AUTHORIZATION_MISSING", "frozen job authorization is required")
    nonce = authorization.get("nonce")
    _require(isinstance(nonce, str) and _NONCE_RE.fullmatch(nonce),
             "JOB_NONCE_INVALID", "job authorization nonce is invalid")
    _require(attestation.get("nonce") == nonce, "ATTESTATION_NONCE_MISMATCH",
             "attestation nonce does not match the frozen job authorization")

    issued = parse_utc(attestation["issued_at_utc"], "attestation.issued_at_utc")
    expires = parse_utc(attestation["expires_at_utc"], "attestation.expires_at_utc")
    _require(issued < expires, "ATTESTATION_TIME_WINDOW", "attestation expiry must follow issue time")
    _require(expires - issued <= MAX_ATTESTATION_TTL,
             "ATTESTATION_TTL_TOO_LONG", "attestation validity exceeds the 15-minute maximum")
    _require(issued <= now <= expires, "ATTESTATION_EXPIRED_OR_FUTURE",
             "attestation is not currently valid")

    public_key = _load_trusted_key(trust_store, attestation, now)
    signature_text = attestation.get("signature")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValidationError("SIGNATURE_ENCODING", "attestation signature is not valid base64") from exc
    signed_claims = {key: value for key, value in attestation.items() if key != "signature"}
    try:
        public_key.verify(signature, DOMAIN + canonical_bytes(signed_claims))
    except InvalidSignature as exc:
        raise ValidationError("SIGNATURE_INVALID", "executor attestation signature is invalid") from exc

    return {"key_id": attestation["key_id"], "executor_id": attestation["executor_id"]}


def _hash_artifact(root: Path, record: dict[str, Any]) -> str:
    relative = record.get("path")
    _require(isinstance(relative, str) and relative, "ARTIFACT_PATH_INVALID", "artifact path is required")
    _require("\\" not in relative, "ARTIFACT_PATH_INVALID", "artifact path must use POSIX separators")
    raw_parts = relative.split("/")
    rel = PurePosixPath(relative)
    _require(not rel.is_absolute() and all(part not in ("", ".", "..") for part in raw_parts),
             "ARTIFACT_PATH_ESCAPE", "artifact path must be a safe relative path")

    current = root
    for part in rel.parts:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ValidationError("ARTIFACT_MISSING", "declared artifact does not exist") from exc
        _require(not stat.S_ISLNK(info.st_mode), "ARTIFACT_SYMLINK", "symlink artifacts are not accepted")

    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValidationError("ARTIFACT_PATH_ESCAPE", "artifact resolves outside the artifact root") from exc

    try:
        descriptor = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise ValidationError("ARTIFACT_OPEN_FAILED", "artifact could not be opened safely") from exc
    try:
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode), "ARTIFACT_NOT_REGULAR", "artifact must be a regular file")
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = os.fstat(descriptor)
        _require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                 (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                 "ARTIFACT_CHANGED_DURING_READ", "artifact changed while being verified")
    finally:
        os.close(descriptor)

    expected_size = record.get("size_bytes")
    expected_hash = record.get("sha256")
    _require(isinstance(expected_size, int) and not isinstance(expected_size, bool) and expected_size >= 0,
             "ARTIFACT_SIZE_INVALID", "artifact size_bytes must be a non-negative integer")
    _require(isinstance(expected_hash, str) and _SHA256_RE.fullmatch(expected_hash),
             "ARTIFACT_HASH_INVALID", "artifact SHA-256 is malformed")
    _require(after.st_size == expected_size, "ARTIFACT_SIZE_MISMATCH", "artifact size does not match RunRecord")
    actual_hash = digest.hexdigest()
    _require(actual_hash == expected_hash, "ARTIFACT_HASH_MISMATCH", "artifact bytes do not match RunRecord")
    return actual_hash


def validate_independently(
    job: dict[str, Any], run: dict[str, Any], attestation: dict[str, Any],
    trust_store: dict[str, Any], artifact_root: str | Path, *,
    now_utc: str | None = None,
) -> dict[str, Any]:
    """Verify frozen job/run claims, trusted Ed25519 signature, and output bytes."""
    now = parse_utc(now_utc or datetime.now(timezone.utc).isoformat(), "now_utc")
    _require(job.get("schema_version") == 1, "JOB_SCHEMA_VERSION", "unsupported JobSpec version")
    _require(run.get("schema_version") == 1, "RUN_SCHEMA_VERSION", "unsupported RunRecord version")
    _require(run.get("status") == "COMPLETED", "RUN_NOT_COMPLETED", "only completed runs can be attested")
    _require(run.get("job_id") == job.get("job_id"), "RUN_JOB_MISMATCH", "RunRecord job_id does not match JobSpec")
    _require(run.get("evidence_level") == job.get("requested_engine"),
             "RUN_ENGINE_MISMATCH", "RunRecord evidence level does not match requested engine")

    implementation = job.get("implementation")
    _require(isinstance(implementation, dict) and
             isinstance(implementation.get("build_sha256"), str) and
             _SHA256_RE.fullmatch(implementation["build_sha256"]),
             "JOB_IMPLEMENTATION_INVALID", "JobSpec implementation digest is invalid")
    inputs = run.get("inputs")
    _require(isinstance(inputs, dict), "RUN_INPUTS_MISSING", "RunRecord inputs are required")
    job_digest = sha256_bytes(canonical_bytes(job))
    _require(inputs.get("job_spec_sha256") == job_digest,
             "RUN_JOB_DIGEST_MISMATCH", "RunRecord does not bind the canonical JobSpec digest")
    _require(inputs.get("implementation_sha256") == implementation["build_sha256"],
             "RUN_IMPLEMENTATION_MISMATCH", "RunRecord implementation digest does not match JobSpec")

    timestamps = run.get("timestamps")
    _require(isinstance(timestamps, dict), "RUN_TIMESTAMPS_MISSING", "RunRecord timestamps are required")
    finished = parse_utc(timestamps.get("finished_at_utc"), "run.timestamps.finished_at_utc")
    _require(finished <= now, "RUN_FINISH_IN_FUTURE", "RunRecord finish time is in the future")

    root_input = Path(artifact_root)
    _require(not root_input.is_symlink(), "ARTIFACT_ROOT_SYMLINK", "artifact root must not be a symlink")
    try:
        root = root_input.resolve(strict=True)
    except OSError as exc:
        raise ValidationError("ARTIFACT_ROOT_MISSING", "artifact root does not exist") from exc
    _require(root.is_dir(), "ARTIFACT_ROOT_INVALID", "artifact root must be a directory")

    verified_identity = _verify_attestation(attestation, trust_store, job, run, job_digest, now)
    outputs = run.get("outputs")
    _require(isinstance(outputs, list) and len(outputs) > 0,
             "RUN_OUTPUTS_MISSING", "RunRecord must declare at least one output artifact")
    verified_artifacts = []
    seen_paths = set()
    for record in outputs:
        _require(isinstance(record, dict), "ARTIFACT_RECORD_INVALID", "artifact record must be an object")
        _require(record.get("path") not in seen_paths, "ARTIFACT_DUPLICATE_PATH", "duplicate artifact path")
        seen_paths.add(record.get("path"))
        verified_artifacts.append(_hash_artifact(root, record))

    return {
        "schema_version": 1,
        "valid": True,
        "decision": "PASS",
        "reason_codes": ["JOB_RUN_BINDING_VALID", "EXECUTOR_SIGNATURE_VALID", "ARTIFACTS_VALID"],
        "job_spec_sha256": job_digest,
        "run_id": run["run_id"],
        "executor_id": verified_identity["executor_id"],
        "key_id": verified_identity["key_id"],
        "verified_artifact_count": len(verified_artifacts),
        "verified_artifact_sha256": verified_artifacts,
        "limitations": [
            "This verifies signed execution claims and artifact bytes only; it does not prove engine correctness or profitability.",
            "The CLI is a separate process, not strong OS isolation when run under the same account/host as the worker.",
            "Nonce binding prevents reuse for a different frozen job authorization; same-run replay/idempotency must be enforced by the external registrar.",
            "Trust-store integrity depends on human-controlled provisioning outside the worker's write authority.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only OpenFX independent run validator")
    parser.add_argument("--job", required=True, help="frozen JobSpec JSON")
    parser.add_argument("--run", required=True, help="RunRecord JSON")
    parser.add_argument("--attestation", required=True, help="signed executor attestation JSON")
    parser.add_argument("--trust-store", required=True, help="externally administered public-key trust store")
    parser.add_argument("--artifact-root", required=True, help="root directory containing declared output artifacts")
    parser.add_argument("--now-utc", help="fixed UTC time for deterministic tests; omit in production")
    args = parser.parse_args(argv)

    try:
        report = validate_independently(
            _read_json(args.job, "JobSpec"),
            _read_json(args.run, "RunRecord"),
            _read_json(args.attestation, "executor attestation"),
            _read_json(args.trust_store, "executor trust store"),
            args.artifact_root,
            now_utc=args.now_utc,
        )
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
        return 0
    except ValidationError as exc:
        print(json.dumps({
            "schema_version": 1, "valid": False, "decision": "FAIL",
            "reason_codes": [exc.reason_code],
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
