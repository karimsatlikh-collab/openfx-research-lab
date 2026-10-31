"""Fail-closed source provenance and minimal claim-to-hypothesis binding.

This is a local contract prototype. It does not grant legal permission, discover
sources, authenticate human reviewers, or establish semantic correctness.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PROVENANCE = {
    "observed",
    "test_confirmed",
    "independently_reproduced",
    "code_reviewed_only",
    "hypothesis",
    "unknown",
}
_RIGHTS = {"owner_created", "explicit_permission", "public_domain", "licensed"}
_AMBIGUOUS_RIGHTS = {"unknown", "ambiguous", "not_reviewed"}


class ProvenanceError(ValueError):
    """Raised when provenance or claim binding is incomplete or inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProvenanceError(message)


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def content_sha256(content: bytes) -> str:
    if not isinstance(content, bytes):
        raise TypeError("source content must be bytes")
    return hashlib.sha256(content).hexdigest()


def build_source_record(
    *,
    source_id: str,
    identity: str,
    rights_basis: str,
    permission_evidence: str,
    retrieved_at_utc: str,
    exact_locator: str,
    capture_method: str,
    content: bytes,
    provenance_state: str = "observed",
    human_approval: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a record; ambiguous rights require a named, reasoned human approval."""
    record = {
        "source_id": source_id,
        "identity": identity,
        "rights_basis": rights_basis,
        "permission_evidence": permission_evidence,
        "retrieved_at_utc": retrieved_at_utc,
        "exact_locator": exact_locator,
        "capture_method": capture_method,
        "content_sha256": content_sha256(content),
        "provenance_state": provenance_state,
        "human_approval": human_approval,
    }
    validate_source_record(record, content)
    return record


def validate_source_record(record: dict[str, Any], content: bytes) -> dict[str, Any]:
    """Validate admissibility and verify the supplied bytes against the recorded hash."""
    _require(isinstance(record, dict), "source record must be an object")
    for field in ("source_id", "identity", "rights_basis", "permission_evidence",
                  "exact_locator", "capture_method"):
        value = record.get(field)
        _require(isinstance(value, str) and bool(value.strip()),
                 f"{field} is required")
    _require(bool(_ID_RE.fullmatch(record["source_id"])), "invalid source_id")
    _require(_valid_timestamp(record.get("retrieved_at_utc")),
             "retrieved_at_utc must be a timezone-aware ISO-8601 timestamp")
    _require(record["rights_basis"] not in _AMBIGUOUS_RIGHTS,
             "rights basis is ambiguous or unreviewed")
    _require(record["rights_basis"] in _RIGHTS,
             "rights_basis is not an admissible recognized basis")
    approval = record.get("human_approval")
    if record["rights_basis"] == "explicit_permission":
        _require(isinstance(approval, dict), "explicit permission requires human approval evidence")
        for key in ("actor_id", "approved_at_utc", "reason"):
            _require(isinstance(approval.get(key), str) and approval[key].strip(),
                     f"human_approval.{key} is required")
        _require(_valid_timestamp(approval["approved_at_utc"]),
                 "human_approval.approved_at_utc must be timezone-aware ISO-8601")
    digest = record.get("content_sha256")
    _require(isinstance(digest, str) and bool(_SHA256_RE.fullmatch(digest)),
             "content_sha256 must be a lowercase SHA-256 hex digest")
    _require(isinstance(content, bytes), "source content must be bytes")
    _require(content_sha256(content) == digest, "source content hash mismatch")
    _require(record.get("provenance_state") in _PROVENANCE,
             "invalid provenance_state")
    return {
        "valid": True,
        "source_id": record["source_id"],
        "content_sha256": digest,
        "provenance_state": record["provenance_state"],
        "limitations": [
            "Rights basis is recorded, not a legal opinion or independent rights verification.",
            "Source identity and exact locator are asserted metadata, not externally authenticated.",
        ],
    }


def build_atomic_claim(
    *,
    claim_id: str,
    source_record: dict[str, Any],
    source_content: bytes,
    exact_locator: str,
    statement: str,
    provenance_state: str = "observed",
) -> dict[str, Any]:
    """Bind one atomic source claim to an admissible source and exact locator."""
    validate_source_record(source_record, source_content)
    _require(isinstance(claim_id, str) and bool(_ID_RE.fullmatch(claim_id)),
             "invalid claim_id")
    _require(isinstance(exact_locator, str) and exact_locator.strip(),
             "claim exact_locator is required")
    _require(exact_locator == source_record["exact_locator"],
             "claim locator does not exactly match source record locator")
    _require(isinstance(statement, str) and statement.strip(),
             "claim statement is required")
    _require(provenance_state in _PROVENANCE - {"hypothesis", "unknown"},
             "source-backed claim requires an evidential provenance state")
    return {
        "claim_id": claim_id,
        "statement": statement.strip(),
        "source_ref": {
            "source_id": source_record["source_id"],
            "exact_locator": exact_locator,
            "content_sha256": source_record["content_sha256"],
        },
        "provenance_state": provenance_state,
        "claim_kind": "source_backed",
    }



def _canonical_json_bytes(value: Any) -> bytes:
    """Canonical local JSON encoding for content-addressed provenance records."""
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProvenanceError("record is not canonical-JSON serializable") from exc


def _store_immutable(path: Path, payload: bytes) -> None:
    """Create a content-addressed file once; never silently overwrite it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != payload:
            raise ProvenanceError("content-addressed registry collision or tampering")


def register_claim_record(
    registry_root: str | Path,
    claim: dict[str, Any],
    source_record: dict[str, Any],
    source_content: bytes,
) -> str:
    """Persist a claim and its source as content-addressed local records.

    This supplies integrity and referential checks, not trusted authorship:
    the local registry has no external signature, registrar, or access control.
    """
    validate_source_record(source_record, source_content)
    _require(isinstance(claim, dict), "claim must be an object")
    _require(claim.get("claim_kind") == "source_backed", "claim is not source-backed")
    claim_id = claim.get("claim_id")
    _require(isinstance(claim_id, str) and bool(_ID_RE.fullmatch(claim_id)),
             "invalid claim_id")
    _require(claim.get("source_ref") == {
        "source_id": source_record["source_id"],
        "exact_locator": source_record["exact_locator"],
        "content_sha256": source_record["content_sha256"],
    }, "claim source reference does not match validated source record")
    _require(isinstance(claim.get("statement"), str) and claim["statement"].strip(),
             "claim statement is required")
    source_bytes = _canonical_json_bytes(source_record)
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    content_digest = content_sha256(source_content)
    claim_record = {
        "schema_version": 1,
        "claim": claim,
        "source_record_sha256": source_digest,
        "source_content_sha256": content_digest,
    }
    claim_bytes = _canonical_json_bytes(claim_record)
    claim_digest = hashlib.sha256(claim_bytes).hexdigest()
    root = Path(registry_root)
    _store_immutable(root / "source-records" / f"{source_digest}.json", source_bytes)
    _store_immutable(root / "source-content" / f"{content_digest}.bin", source_content)
    _store_immutable(root / "claim-records" / f"{claim_digest}.json", claim_bytes)
    index_bytes = _canonical_json_bytes({
        "schema_version": 1,
        "claim_id": claim_id,
        "claim_record_sha256": claim_digest,
    })
    _store_immutable(root / "claim-index" / f"{claim_id}.json", index_bytes)
    return claim_digest


def resolve_claim_record(registry_root: str | Path, claim_id: str) -> dict[str, Any]:
    """Resolve a claim ID and verify its content-addressed source chain."""
    _require(isinstance(claim_id, str) and bool(_ID_RE.fullmatch(claim_id)),
             "invalid claim_id")
    root = Path(registry_root)
    try:
        index_path = root / "claim-index" / f"{claim_id}.json"
        if index_path.is_symlink():
            raise ProvenanceError("claim registry index must not be a symlink")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        _require(isinstance(index, dict)
                 and set(index) == {"schema_version", "claim_id", "claim_record_sha256"}
                 and index.get("schema_version") == 1
                 and index.get("claim_id") == claim_id,
                 "claim registry index schema mismatch")
        digest = index["claim_record_sha256"]
        _require(isinstance(digest, str) and bool(_SHA256_RE.fullmatch(digest)),
                 "claim registry index digest is invalid")
        claim_path = root / "claim-records" / f"{digest}.json"
        if claim_path.is_symlink():
            raise ProvenanceError("claim record must not be a symlink")
        claim_bytes = claim_path.read_bytes()
        _require(hashlib.sha256(claim_bytes).hexdigest() == digest,
                 "claim record content hash mismatch")
        record = json.loads(claim_bytes)
        _require(_canonical_json_bytes(record) == claim_bytes,
                 "claim record is not canonically encoded")
        _require(record.get("schema_version") == 1, "unsupported claim record schema")
        claim = record.get("claim")
        _require(isinstance(claim, dict) and claim.get("claim_id") == claim_id,
                 "claim ID does not match registry record")
        source_digest = record.get("source_record_sha256")
        _require(isinstance(source_digest, str) and bool(_SHA256_RE.fullmatch(source_digest)),
                 "source record digest is invalid")
        source_path = root / "source-records" / f"{source_digest}.json"
        content_digest = record.get("source_content_sha256")
        _require(isinstance(content_digest, str) and bool(_SHA256_RE.fullmatch(content_digest)),
                 "source content digest is invalid")
        content_path = root / "source-content" / f"{content_digest}.bin"
        if source_path.is_symlink() or content_path.is_symlink():
            raise ProvenanceError("source registry objects must not be symlinks")
        source_bytes = source_path.read_bytes()
        _require(hashlib.sha256(source_bytes).hexdigest() == source_digest,
                 "source record content hash mismatch")
        source_record = json.loads(source_bytes)
        _require(_canonical_json_bytes(source_record) == source_bytes,
                 "source record is not canonically encoded")
        source_content = content_path.read_bytes()
        _require(content_sha256(source_content) == content_digest,
                 "source content hash mismatch")
        _require(source_record.get("content_sha256") == content_digest,
                 "source record does not bind stored source bytes")
        validate_source_record(source_record, source_content)
        _require(claim.get("source_ref") == {
            "source_id": source_record["source_id"],
            "exact_locator": source_record["exact_locator"],
            "content_sha256": source_record["content_sha256"],
        }, "claim source reference does not match registered source")
        _require(isinstance(claim.get("statement"), str) and claim["statement"].strip(),
                 "registered claim statement is invalid")
        _require(claim.get("claim_kind") == "source_backed", "registered claim kind is invalid")
        _require(claim.get("provenance_state") in _PROVENANCE - {"hypothesis", "unknown"},
                 "registered claim provenance state is invalid")
        return {
            "claim": claim,
            "claim_record_sha256": digest,
            "source_record_sha256": source_digest,
            "source_content_sha256": content_digest,
            "record_integrity_verified": True,
            "provenance_authenticated": False,
        }
    except ProvenanceError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ProvenanceError(f"claim registry resolution failed: {type(exc).__name__}") from exc


def build_hypothesis_card(
    *,
    hypothesis_id: str,
    title: str,
    falsifiable_statement: str,
    linked_claims: list[dict[str, Any]],
    predicted_mechanism: str,
    invalidation_criteria: str,
    claim_registry_root: str | Path | None = None,
) -> dict[str, Any]:
    """Create a hypothesis and explicitly mark linked-claim provenance as unverified.

    This function validates claim shape only. It deliberately does not represent
    caller-supplied claim dictionaries as registry-authenticated provenance.
    """
    _require(isinstance(hypothesis_id, str) and bool(_ID_RE.fullmatch(hypothesis_id)),
             "invalid hypothesis_id")
    for name, value in (("title", title), ("falsifiable_statement", falsifiable_statement),
                        ("predicted_mechanism", predicted_mechanism),
                        ("invalidation_criteria", invalidation_criteria)):
        _require(isinstance(value, str) and value.strip(), f"{name} is required")
    _require(isinstance(linked_claims, list) and bool(linked_claims),
             "at least one linked atomic claim is required")
    claim_refs = []
    seen_claim_ids: set[str] = set()
    registry_resolved = 0
    registry_integrity_verified = 0
    for claim in linked_claims:
        _require(isinstance(claim, dict) and claim.get("claim_kind") == "source_backed",
                 "hypothesis links must reference source-backed atomic claims")
        claim_id = claim.get("claim_id")
        _require(isinstance(claim_id, str) and bool(_ID_RE.fullmatch(claim_id)),
                 "hypothesis link contains an invalid claim_id")
        _require(claim_id not in seen_claim_ids, "hypothesis links contain duplicate claim IDs")
        seen_claim_ids.add(claim_id)
        claim_state = claim.get("provenance_state")
        _require(isinstance(claim_state, str) and claim_state in _PROVENANCE - {"hypothesis", "unknown"},
                 "hypothesis links must preserve a source-backed claim provenance state")
        ref = claim.get("source_ref")
        _require(isinstance(ref, dict)
                 and all(isinstance(ref.get(k), str) and ref[k].strip()
                         for k in ("source_id", "exact_locator", "content_sha256")),
                 "linked claim source reference is incomplete")
        _require(bool(_ID_RE.fullmatch(ref["source_id"])),
                 "linked claim source ID is malformed")
        _require(bool(_SHA256_RE.fullmatch(ref["content_sha256"])),
                 "linked claim source hash is malformed")
        resolved_claim = claim
        if claim_registry_root is not None:
            resolved = resolve_claim_record(claim_registry_root, claim_id)
            _require(_canonical_json_bytes(resolved["claim"]) == _canonical_json_bytes(claim),
                     "caller-supplied claim does not match content-addressed registry record")
            resolved_claim = resolved["claim"]
            registry_resolved += 1
            registry_integrity_verified += int(resolved["record_integrity_verified"])
        claim_refs.append({
            "claim_id": claim_id,
            "source_ref": dict(resolved_claim["source_ref"]),
            "claim_provenance_state": resolved_claim.get("provenance_state"),
        })
    return {
        "hypothesis_id": hypothesis_id,
        "title": title.strip(),
        "falsifiable_statement": falsifiable_statement.strip(),
        "linked_claims": claim_refs,
        "predicted_mechanism": predicted_mechanism.strip(),
        "invalidation_criteria": invalidation_criteria.strip(),
        "epistemic_status": "hypothesis",
        "is_verified_rule": False,
        "claim_link_validation": {
            "shape_valid": True,
            "registry_records_resolved": registry_resolved,
            "record_integrity_verified": (
                registry_integrity_verified == len(claim_refs)
                if claim_registry_root is not None else False
            ),
            "provenance_verified": False,
            "status": (
                "content_addressed_local_registry_integrity_only_not_authenticated"
                if claim_registry_root is not None else "metadata_only_unverified"
            ),
            "reason": (
                "Content-addressed claim and source bytes were resolved and hashed, "
                "but this local registry has no external signature or trusted registrar."
                if claim_registry_root is not None
                else "Caller-supplied claim dictionaries were shape-checked, but no "
                     "content-addressed registry record was resolved."
            ),
        },
        "limitations": [
            "A source-backed claim does not prove that the proposed mechanism is true.",
            "Caller-supplied claim dictionaries are metadata, not authenticated registry records.",
            "Source identity, locator, and rights are not independently authenticated by this function.",
            "Reviewer identity, role separation, and approval events are not runtime-enforced.",
        ],
    }
