"""Synthetic-only end-to-end G0-G2 reproduction prototype.

Runs a frozen deterministic fixture twice, stores byte-identical run records,
and compares their hashes. This is not a market simulator or independent human
reproduction; both executions use the same code and process.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from openfx.source_provenance import validate_source_record
from openfx.synthetic_engine import run_synthetic
from openfx.trial_registry import LocalTrialRegistry
from openfx.statistical_gate import evaluate_registered_synthetic_summary


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def freeze_trial(*, source_record: dict[str, Any], source_content: bytes,
                 claim: dict[str, Any], hypothesis: dict[str, Any],
                 family_id: str, trial_id: str, seed: int, n: int,
                 edge: float, noise: float, gate_config: dict[str, Any]) -> dict[str, Any]:
    """Bind provenance, hypothesis, engine parameters and gate config into one digest."""
    validate_source_record(source_record, source_content)
    if claim.get("claim_kind") != "source_backed":
        raise ValueError("frozen trial requires a source-backed claim")
    ref = claim.get("source_ref", {})
    expected_ref = {
        "source_id": source_record["source_id"],
        "exact_locator": source_record["exact_locator"],
        "content_sha256": source_record["content_sha256"],
    }
    if ref != expected_ref:
        raise ValueError("claim/source binding mismatch")
    if hypothesis.get("epistemic_status") != "hypothesis" or hypothesis.get("is_verified_rule") is not False:
        raise ValueError("hypothesis status must remain explicitly unverified")
    if not hypothesis.get("linked_claims") or not any(
        item.get("claim_id") == claim.get("claim_id") and item.get("source_ref") == expected_ref
        for item in hypothesis["linked_claims"]
    ):
        raise ValueError("hypothesis does not bind the supplied claim")
    if not family_id or not trial_id:
        raise ValueError("family_id and trial_id are required")
    if isinstance(seed, bool) or not isinstance(seed, int) or isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("seed must be an integer and n must be a positive integer")
    if not isinstance(edge, (int, float)) or not isinstance(noise, (int, float)) or noise < 0:
        raise ValueError("edge/noise parameters are invalid")
    if gate_config.get("frozen_before_trials") is not True:
        raise ValueError("gate configuration must be frozen before trials")
    body = {
        "schema_version": 1,
        "evidence_level": "synthetic",
        "source_ref": expected_ref,
        # Bind the complete provenance and epistemic documents, not only their IDs.
        "source_record_sha256": sha256_bytes(canonical_bytes(source_record)),
        "claim_sha256": sha256_bytes(canonical_bytes(claim)),
        "hypothesis_sha256": sha256_bytes(canonical_bytes(hypothesis)),
        "claim_id": claim["claim_id"],
        "hypothesis_id": hypothesis["hypothesis_id"],
        "hypothesis_status": "hypothesis",
        "family_id": family_id,
        "trial_id": trial_id,
        "engine": "openfx.synthetic_engine.run_synthetic",
        "engine_parameters": {"seed": seed, "n": n, "edge": edge, "noise": noise},
        "gate_config": gate_config,
    }
    body["frozen_sha256"] = sha256_bytes(canonical_bytes(body))
    return body


def verify_frozen_trial(frozen: dict[str, Any]) -> str:
    supplied = frozen.get("frozen_sha256")
    body = {key: value for key, value in frozen.items() if key != "frozen_sha256"}
    expected = sha256_bytes(canonical_bytes(body))
    if not isinstance(supplied, str) or supplied != expected:
        raise ValueError("frozen trial hash mismatch")
    if frozen.get("evidence_level") != "synthetic":
        raise ValueError("this runner accepts synthetic trials only")
    return expected


def _execute_once(frozen: dict[str, Any], workspace: Path) -> dict[str, Any]:
    verify_frozen_trial(frozen)
    workspace.mkdir(parents=True, exist_ok=True)
    params = frozen["engine_parameters"]
    result = run_synthetic(**params)
    record = {
        "schema_version": 1,
        "frozen_sha256": frozen["frozen_sha256"],
        "trial_id": frozen["trial_id"],
        "evidence_level": "synthetic",
        "engine": frozen["engine"],
        "engine_parameters": params,
        "result": result,
    }
    raw = canonical_bytes(record) + b"\n"
    artifact = workspace / "run_record.json"
    artifact.write_bytes(raw)

    # Verify the persisted bytes, not merely the in-memory buffer. Re-open the
    # exact path, compare bytes, parse JSON, and enforce the v1 record contract.
    persisted = artifact.read_bytes()
    if persisted != raw:
        raise ValueError("persisted run artifact bytes differ from expected bytes")
    try:
        decoded = json.loads(persisted)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("persisted run artifact is not valid JSON") from exc
    required = {
        "schema_version", "frozen_sha256", "trial_id", "evidence_level",
        "engine", "engine_parameters", "result",
    }
    if not isinstance(decoded, dict) or set(decoded) != required:
        raise ValueError("persisted run artifact does not match the strict v1 record shape")
    if decoded.get("schema_version") != 1 or decoded.get("evidence_level") != "synthetic":
        raise ValueError("persisted run artifact has unsupported schema/evidence level")
    if decoded != record:
        raise ValueError("persisted run artifact content differs from execution record")
    persisted_hash = sha256_bytes(persisted)
    return {
        "record": decoded,
        "artifact_path": str(artifact),
        "artifact_sha256": persisted_hash,
        "record_sha256": sha256_bytes(canonical_bytes(decoded)),
    }


def run_synthetic_reproduction(*, frozen: dict[str, Any], registry: LocalTrialRegistry,
                               workspace: str | Path, max_trials: int = 1) -> dict[str, Any]:
    """Register first, replay twice in separate workspaces, compare, then close trial."""
    frozen_hash = verify_frozen_trial(frozen)
    root = Path(workspace)
    first = root / "replay_a"
    second = root / "replay_b"
    family_id, trial_id = frozen["family_id"], frozen["trial_id"]
    registry.append(
        event_id=f"{trial_id}-registered", family_id=family_id, trial_id=trial_id,
        outcome="pending", payload={"frozen_sha256": frozen_hash, "evidence_level": "synthetic"},
        max_trials=max_trials,
    )
    try:
        a = _execute_once(frozen, first)
        b = _execute_once(frozen, second)
        if a["artifact_sha256"] != b["artifact_sha256"] or a["record_sha256"] != b["record_sha256"]:
            raise ValueError("independent replay artifacts differ")
        if a["record"] != b["record"]:
            raise ValueError("independent replay records differ")
        registry.append(
            event_id=f"{trial_id}-completed", family_id=family_id, trial_id=trial_id,
            outcome="completed",
            payload={
                "frozen_sha256": frozen_hash,
                "replay_a_sha256": a["artifact_sha256"],
                "replay_b_sha256": b["artifact_sha256"],
                "reproduced": True,
                "evidence_level": "synthetic",
            },
        )
        summary = a["record"]["result"]
        verdict = evaluate_registered_synthetic_summary(
            summary, frozen["gate_config"], registry=registry, family_id=family_id
        )
        return {
            "status": "synthetic_reproduced",
            "evidence_level": "synthetic",
            "is_market_backtest": False,
            "frozen_sha256": frozen_hash,
            "replay_a_sha256": a["artifact_sha256"],
            "replay_b_sha256": b["artifact_sha256"],
            "replay_hashes_equal": a["artifact_sha256"] == b["artifact_sha256"],
            "registry": registry.verify(),
            "gate_verdict": verdict,
            "limitations": [
                "Both replays use the same implementation and are not independent human/code reproductions.",
                "The local JSONL registry is not tamper-proof or a trusted central registrar.",
                "The descriptive gate applies no multiple-testing correction.",
                "Synthetic evidence does not establish market validity or profitability.",
            ],
        }
    except Exception as exc:
        registry.append(
            event_id=f"{trial_id}-failed", family_id=family_id, trial_id=trial_id,
            outcome="failed",
            payload={"frozen_sha256": frozen_hash, "error": str(exc)[:500],
                     "evidence_level": "synthetic"},
        )
        raise
