"""Hardened independent run validator v2.

V2 binds the complete canonical RunRecord into the executor signature and
opens artifacts beneath a pinned directory descriptor without following any
symlink component. The CLI always uses the system clock.
"""
from __future__ import annotations

import argparse
import base64
import errno
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

VALIDATOR_VERSION = "2.0.0"
DOMAIN = b"OPENFX_EXECUTOR_ATTESTATION_V2\n"
MAX_ATTESTATION_TTL = timedelta(minutes=15)
MAX_INPUT_JSON_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_SIZE_BYTES = 512 * 1024 * 1024
MAX_ARTIFACT_COUNT = 1000
MAX_PATH_LENGTH = 1024
MAX_PATH_DEPTH = 32
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_JOB_KEYS = {"schema_version", "job_id", "requested_engine", "implementation",
             "authorization", "expected_outputs"}
_RUN_KEYS = {"schema_version", "run_id", "job_id", "status", "evidence_level",
             "timestamps", "inputs", "outputs"}
_ATTESTATION_KEYS = {"key_id", "executor_id", "job_id", "run_id",
                     "job_spec_sha256", "run_record_sha256", "engine",
                     "implementation_sha256", "nonce", "issued_at_utc",
                     "expires_at_utc", "signature"}
_TRUST_STORE_KEYS = {"schema_version", "keys"}
_TRUST_KEY_KEYS = {"key_id", "executor_id", "algorithm", "public_key_b64",
                   "not_before_utc", "not_after_utc", "revoked", "allowed_engines"}


class ValidationError(ValueError):
    """Fail-closed validation error with a stable reason code."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
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
    target = Path(path)
    try:
        info = target.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_INPUT_JSON_BYTES:
            raise ValidationError("INPUT_SIZE_OR_TYPE", f"{label} must be a regular JSON file within the size limit")
        raw = target.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except ValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("INPUT_READ_FAILED", f"could not read {label} JSON") from exc
    if not isinstance(value, dict):
        raise ValidationError("INVALID_INPUT_SHAPE", f"{label} root must be an object")
    return value


def _require(condition: bool, reason: str, message: str) -> None:
    if not condition:
        raise ValidationError(reason, message)


def _relative_parts(relative: Any) -> tuple[str, ...]:
    _require(isinstance(relative, str) and bool(relative),
             "ARTIFACT_PATH_INVALID", "artifact path is required")
    _require(len(relative) <= MAX_PATH_LENGTH and "\\" not in relative,
             "ARTIFACT_PATH_INVALID", "artifact path length or separator is invalid")
    raw_parts = relative.split("/")
    rel = PurePosixPath(relative)
    _require(not rel.is_absolute()
             and len(raw_parts) <= MAX_PATH_DEPTH
             and all(part not in ("", ".", "..") for part in raw_parts),
             "ARTIFACT_PATH_ESCAPE", "artifact path must be a safe relative POSIX path")
    return tuple(raw_parts)


def _open_beneath(root: Path, parts: tuple[str, ...]) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if (nofollow is None or directory is None or os.open not in getattr(os, "supports_dir_fd", set())):
        raise ValidationError("ARTIFACT_OPEN_UNSUPPORTED",
                              "platform lacks safe directory-relative no-follow file opening")
    root_fd = None
    current_fd = None
    try:
        root_fd = os.open(root, os.O_RDONLY | directory | nofollow)
        if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
            raise ValidationError("ARTIFACT_ROOT_INVALID", "artifact root is not a directory")
        current_fd = os.dup(root_fd)
        for part in parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        descriptor = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=current_fd)
        return descriptor
    except ValidationError:
        raise
    except FileNotFoundError as exc:
        raise ValidationError("ARTIFACT_MISSING", "declared artifact path does not exist") from exc
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValidationError("ARTIFACT_SYMLINK_OR_NOT_DIRECTORY",
                                  "artifact path contains a symlink or non-directory component") from exc
        raise ValidationError("ARTIFACT_OPEN_FAILED", "artifact could not be opened safely") from exc
    finally:
        if current_fd is not None:
            os.close(current_fd)
        if root_fd is not None:
            os.close(root_fd)


def _hash_artifact(root: Path, record: dict[str, Any]) -> str:
    _require(set(record) == {"path", "size_bytes", "sha256"},
             "ARTIFACT_RECORD_SHAPE", "artifact record has unexpected or missing fields")
    parts = _relative_parts(record.get("path"))
    expected_size = record.get("size_bytes")
    expected_hash = record.get("sha256")
    _require(isinstance(expected_size, int) and not isinstance(expected_size, bool)
             and 0 <= expected_size <= MAX_ARTIFACT_SIZE_BYTES,
             "ARTIFACT_SIZE_INVALID", "artifact size is invalid or exceeds the configured maximum")
    _require(isinstance(expected_hash, str) and _SHA256_RE.fullmatch(expected_hash),
             "ARTIFACT_HASH_INVALID", "artifact SHA-256 is malformed")

    descriptor = _open_beneath(root, parts)
    try:
        before = os.fstat(descriptor)
        _require(stat.S_ISREG(before.st_mode), "ARTIFACT_NOT_REGULAR", "artifact must be a regular file")
        _require(before.st_size <= MAX_ARTIFACT_SIZE_BYTES,
                 "ARTIFACT_TOO_LARGE", "artifact exceeds the configured maximum size")
        digest = hashlib.sha256()
        total = 0
        try:
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    total += len(chunk)
                    if total > MAX_ARTIFACT_SIZE_BYTES:
                        raise ValidationError("ARTIFACT_TOO_LARGE", "artifact grew beyond the configured maximum")
                    digest.update(chunk)
        except OSError as exc:
            raise ValidationError("ARTIFACT_READ_FAILED", "artifact could not be read safely") from exc
        after = os.fstat(descriptor)
        before_state = (before.st_dev, before.st_ino, before.st_size,
                        before.st_mtime_ns, before.st_ctime_ns)
        after_state = (after.st_dev, after.st_ino, after.st_size,
                       after.st_mtime_ns, after.st_ctime_ns)
        _require(before_state == after_state and total == after.st_size,
                 "ARTIFACT_CHANGED_DURING_READ", "artifact changed while being verified")
    finally:
        os.close(descriptor)

    _require(after.st_size == expected_size,
             "ARTIFACT_SIZE_MISMATCH", "artifact size does not match RunRecord")
    actual_hash = digest.hexdigest()
    _require(actual_hash == expected_hash,
             "ARTIFACT_HASH_MISMATCH", "artifact bytes do not match RunRecord")
    return actual_hash


def _load_trusted_key(trust_store: dict[str, Any],
                      attestation: dict[str, Any], now: datetime) -> Ed25519PublicKey:
    _require(set(trust_store) == _TRUST_STORE_KEYS and trust_store.get("schema_version") == 1,
             "TRUST_STORE_INVALID", "trust store has an unsupported version or shape")
    entries = trust_store.get("keys")
    _require(isinstance(entries, list) and 0 < len(entries) <= 1000,
             "TRUST_STORE_INVALID", "trust-store keys must be a bounded non-empty list")
    key_id = attestation.get("key_id")
    matches = [item for item in entries if isinstance(item, dict) and item.get("key_id") == key_id]
    _require(len(matches) == 1, "UNKNOWN_OR_DUPLICATE_KEY", "key ID is unknown or duplicated")
    entry = matches[0]
    _require(set(entry) == _TRUST_KEY_KEYS, "TRUST_KEY_INVALID", "trusted key entry has unexpected fields")
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
             "ATTESTATION_OUTSIDE_KEY_VALIDITY", "attestation validity is outside the trusted key window")
    encoded = entry.get("public_key_b64")
    _require(isinstance(encoded, str), "TRUST_KEY_INVALID", "trusted public key is missing")
    try:
        return Ed25519PublicKey.from_public_bytes(base64.b64decode(encoded, validate=True))
    except (ValueError, TypeError) as exc:
        raise ValidationError("TRUST_KEY_INVALID", "trusted Ed25519 public key is malformed") from exc


def _verify_attestation(attestation: dict[str, Any], trust_store: dict[str, Any],
                        job: dict[str, Any], run: dict[str, Any],
                        job_digest: str, run_digest: str, now: datetime) -> dict[str, str]:
    _require(set(attestation) == _ATTESTATION_KEYS,
             "ATTESTATION_SHAPE", "attestation has unexpected or missing fields")
    for field in _ATTESTATION_KEYS - {"signature"}:
        _require(isinstance(attestation.get(field), str) and bool(attestation[field].strip()),
                 "ATTESTATION_FIELD_MISSING", f"attestation.{field} is required")
    implementation = job["implementation"]
    expected = {
        "job_id": job["job_id"], "run_id": run["run_id"],
        "job_spec_sha256": job_digest, "run_record_sha256": run_digest,
        "engine": job["requested_engine"],
        "implementation_sha256": implementation["build_sha256"],
    }
    for field, value in expected.items():
        if attestation.get(field) != value:
            reason = "ATTESTATION_RUN_RECORD_MISMATCH" if field == "run_record_sha256" else "ATTESTATION_BINDING_MISMATCH"
            raise ValidationError(reason, f"attestation.{field} does not match canonical frozen input")
    nonce = job["authorization"]["nonce"]
    _require(_NONCE_RE.fullmatch(nonce) is not None and attestation.get("nonce") == nonce,
             "ATTESTATION_NONCE_MISMATCH", "attestation nonce does not match frozen job authorization")
    issued = parse_utc(attestation["issued_at_utc"], "attestation.issued_at_utc")
    expires = parse_utc(attestation["expires_at_utc"], "attestation.expires_at_utc")
    _require(issued < expires, "ATTESTATION_TIME_WINDOW", "attestation expiry must follow issue time")
    _require(expires - issued <= MAX_ATTESTATION_TTL,
             "ATTESTATION_TTL_TOO_LONG", "attestation validity exceeds the 15-minute maximum")
    _require(issued <= now <= expires, "ATTESTATION_EXPIRED_OR_FUTURE",
             "attestation is not currently valid")
    public_key = _load_trusted_key(trust_store, attestation, now)
    try:
        signature = base64.b64decode(attestation["signature"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValidationError("SIGNATURE_ENCODING", "attestation signature is not valid base64") from exc
    claims = {key: value for key, value in attestation.items() if key != "signature"}
    try:
        public_key.verify(signature, DOMAIN + canonical_bytes(claims))
    except InvalidSignature as exc:
        raise ValidationError("SIGNATURE_INVALID", "executor attestation signature is invalid") from exc
    return {"key_id": attestation["key_id"], "executor_id": attestation["executor_id"]}


def _validate_job(job: dict[str, Any]) -> list[str]:
    _require(set(job) == _JOB_KEYS, "JOB_SHAPE", "JobSpec has unexpected or missing fields")
    _require(job.get("schema_version") == 2, "JOB_SCHEMA_VERSION", "unsupported JobSpec v2 schema")
    _require(isinstance(job.get("job_id"), str) and bool(job["job_id"]),
             "JOB_ID_INVALID", "job_id is required")
    _require(job.get("requested_engine") in {"mock", "synthetic", "mt5-demo"},
             "JOB_ENGINE_INVALID", "requested engine is unsupported")
    implementation = job.get("implementation")
    _require(isinstance(implementation, dict) and set(implementation) == {"build_sha256"}
             and isinstance(implementation["build_sha256"], str)
             and _SHA256_RE.fullmatch(implementation["build_sha256"]),
             "JOB_IMPLEMENTATION_INVALID", "JobSpec implementation digest is invalid")
    authorization = job.get("authorization")
    _require(isinstance(authorization, dict) and set(authorization) == {"nonce"}
             and isinstance(authorization["nonce"], str)
             and _NONCE_RE.fullmatch(authorization["nonce"]) is not None,
             "JOB_AUTHORIZATION_INVALID", "JobSpec authorization nonce is invalid")
    expected = job.get("expected_outputs")
    _require(isinstance(expected, list) and 0 < len(expected) <= MAX_ARTIFACT_COUNT,
             "JOB_EXPECTED_OUTPUTS_INVALID", "JobSpec expected_outputs must be a bounded non-empty list")
    for path in expected:
        _relative_parts(path)
    _require(len(set(expected)) == len(expected),
             "JOB_EXPECTED_OUTPUTS_DUPLICATE", "JobSpec expected outputs contain duplicates")
    return expected


def _validate_run(run: dict[str, Any], job: dict[str, Any],
                  expected_outputs: list[str]) -> tuple[str, datetime]:
    _require(set(run) == _RUN_KEYS, "RUN_SHAPE", "RunRecord has unexpected or missing fields")
    _require(run.get("schema_version") == 2, "RUN_SCHEMA_VERSION", "unsupported RunRecord v2 schema")
    _require(isinstance(run.get("run_id"), str) and bool(run["run_id"]),
             "RUN_ID_INVALID", "run_id is required")
    _require(run.get("status") == "COMPLETED", "RUN_NOT_COMPLETED", "only completed runs can be attested")
    _require(run.get("job_id") == job["job_id"], "RUN_JOB_MISMATCH", "RunRecord job_id does not match JobSpec")
    _require(run.get("evidence_level") == job["requested_engine"],
             "RUN_ENGINE_MISMATCH", "RunRecord evidence level does not match requested engine")
    timestamps = run.get("timestamps")
    _require(isinstance(timestamps, dict) and set(timestamps) == {"finished_at_utc"},
             "RUN_TIMESTAMPS_INVALID", "RunRecord timestamps have an invalid shape")
    finished = parse_utc(timestamps.get("finished_at_utc"), "run.timestamps.finished_at_utc")
    inputs = run.get("inputs")
    _require(isinstance(inputs, dict) and set(inputs) == {"job_spec_sha256", "implementation_sha256"},
             "RUN_INPUTS_INVALID", "RunRecord inputs have an invalid shape")
    job_digest = sha256_bytes(canonical_bytes(job))
    _require(inputs.get("job_spec_sha256") == job_digest,
             "RUN_JOB_DIGEST_MISMATCH", "RunRecord does not bind the canonical JobSpec digest")
    _require(inputs.get("implementation_sha256") == job["implementation"]["build_sha256"],
             "RUN_IMPLEMENTATION_MISMATCH", "RunRecord implementation digest does not match JobSpec")
    outputs = run.get("outputs")
    _require(isinstance(outputs, list) and 0 < len(outputs) <= MAX_ARTIFACT_COUNT,
             "RUN_OUTPUTS_INVALID", "RunRecord outputs must be a bounded non-empty list")
    paths = []
    for record in outputs:
        _require(isinstance(record, dict) and set(record) == {"path", "size_bytes", "sha256"},
                 "ARTIFACT_RECORD_SHAPE", "RunRecord output record has an invalid shape")
        path = record.get("path")
        _relative_parts(path)
        paths.append(path)
    _require(len(set(paths)) == len(paths), "ARTIFACT_DUPLICATE_PATH", "duplicate artifact path")
    _require(set(paths) == set(expected_outputs) and len(paths) == len(expected_outputs),
             "RUN_OUTPUT_SET_MISMATCH", "RunRecord outputs do not match the frozen JobSpec expected outputs")
    return sha256_bytes(canonical_bytes(run)), finished


def validate_independently(job: dict[str, Any], run: dict[str, Any],
                           attestation: dict[str, Any], trust_store: dict[str, Any],
                           artifact_root: str | Path, *,
                           now_utc: str | None = None) -> dict[str, Any]:
    """Verify complete frozen JobSpec/RunRecord, executor signature, and output bytes."""
    now = parse_utc(now_utc or datetime.now(timezone.utc).isoformat(), "now_utc")
    expected_outputs = _validate_job(job)
    run_digest, finished = _validate_run(run, job, expected_outputs)
    job_digest = sha256_bytes(canonical_bytes(job))
    _require(run_digest == sha256_bytes(canonical_bytes(run)),
             "RUN_RECORD_DIGEST_INTERNAL", "RunRecord digest could not be reproduced")
    identity = _verify_attestation(attestation, trust_store, job, run,
                                   job_digest, run_digest, now)
    issued = parse_utc(attestation["issued_at_utc"], "attestation.issued_at_utc")
    _require(issued >= finished, "ATTESTATION_PRECEDES_RUN_COMPLETION",
             "executor attestation must be issued after RunRecord completion")

    root_input = Path(artifact_root)
    _require(not root_input.is_symlink(), "ARTIFACT_ROOT_SYMLINK", "artifact root must not be a symlink")
    try:
        root = root_input.resolve(strict=True)
    except OSError as exc:
        raise ValidationError("ARTIFACT_ROOT_MISSING", "artifact root does not exist") from exc
    _require(root.is_dir(), "ARTIFACT_ROOT_INVALID", "artifact root must be a directory")

    verified = []
    for record in run["outputs"]:
        verified.append(_hash_artifact(root, record))
    source_path = Path(__file__).resolve()
    validator_source_sha256 = sha256_bytes(source_path.read_bytes())
    return {
        "schema_version": 2, "validator_version": VALIDATOR_VERSION,
        "validator_source_sha256": validator_source_sha256,
        "valid": True, "decision": "PASS",
        "reason_codes": ["JOB_RUN_BINDING_VALID", "RUN_RECORD_SIGNATURE_BINDING_VALID",
                         "EXECUTOR_SIGNATURE_VALID", "ARTIFACTS_VALID"],
        "job_spec_sha256": job_digest, "run_record_sha256": run_digest,
        "run_id": run["run_id"], "executor_id": identity["executor_id"],
        "key_id": identity["key_id"], "verified_artifact_count": len(verified),
        "verified_artifact_sha256": verified,
        "limitations": [
            "This verifies signed execution claims and declared artifact bytes only; it does not prove engine correctness or profitability.",
            "The CLI must still run under a separate OS identity/host with read-only inputs and trust-store access.",
            "Nonce consumption/replay idempotency remains the external registrar's responsibility.",
            "Trust-store integrity and private-key custody depend on human-controlled provisioning outside the worker's write authority.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hardened OpenFX independent run validator v2")
    parser.add_argument("--job", required=True, help="frozen JobSpec v2 JSON")
    parser.add_argument("--run", required=True, help="RunRecord v2 JSON")
    parser.add_argument("--attestation", required=True, help="signed executor attestation v2 JSON")
    parser.add_argument("--trust-store", required=True, help="externally administered public-key trust store")
    parser.add_argument("--artifact-root", required=True, help="root directory containing declared output artifacts")
    args = parser.parse_args(argv)
    try:
        report = validate_independently(
            _read_json(args.job, "JobSpec"), _read_json(args.run, "RunRecord"),
            _read_json(args.attestation, "executor attestation"),
            _read_json(args.trust_store, "executor trust store"), args.artifact_root,
        )
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
        return 0
    except ValidationError as exc:
        print(json.dumps({"schema_version": 2, "valid": False, "decision": "FAIL",
                          "reason_codes": [exc.reason_code]}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({"schema_version": 2, "valid": False, "decision": "FAIL",
                          "reason_codes": ["VALIDATOR_INTERNAL_ERROR"]}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
