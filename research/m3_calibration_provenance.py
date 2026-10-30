"""Fail-closed provenance binding for M3 v2 synthetic calibration."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_ENGINE_REVISION = "087e66622f27350f1999d2e5b2ec82a9ead78982"
EXPECTED_GIT_BLOBS = {
    "docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md": "62b852f958caa7b767c35d1e7cd47a73c5c067ad",
    "research/m3_hac_mbb_v2_calibration.py": "c2716d85c22a3eb415996ac7a26883276c7c63ba",
    "openfx/selection_bias_v2.py": "72a69166e8121e7d866baa7cb77479975dd04161",
    "research/aggregate_m3_hac_mbb_v2.py": "0e8639be7316d177ab2064f302cbaa3cc24a36cb",
    "research/validate_m3_v2_reference.py": "0ce7599e5e4ba3f17f4f10001da96103314f080b",
    "research/benchmark_m3_v2_family.py": "3f71a48d7fd1adfaea08f7bbc8383dfd3e6e1e0c",
}


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.PIPE
    ).strip()


def verify_execution_bindings(
    plan_file: Path,
    engine_revision: str,
    runner_file: Path,
    engine_file: Path,
) -> dict:
    """Bind the run to the exact clean checkout, plan bytes, and engine tree."""
    plan_file = plan_file.resolve()
    runner_file = runner_file.resolve()
    engine_file = engine_file.resolve()
    if engine_revision != FROZEN_ENGINE_REVISION:
        raise ValueError("engine revision differs from the pre-registered frozen revision")
    aggregator_file = ROOT / "research" / "aggregate_m3_hac_mbb_v2.py"
    reference_file = ROOT / "research" / "validate_m3_v2_reference.py"
    paths = [p.relative_to(ROOT).as_posix() for p in
             (plan_file, runner_file, engine_file, aggregator_file, reference_file, ROOT / "research" / "benchmark_m3_v2_family.py")]
    for path in paths:
        worktree_blob = _git("hash-object", path)
        committed_blob = _git("rev-parse", f"HEAD:{path}")
        if worktree_blob != committed_blob:
            raise ValueError(f"working file differs from checked-out commit: {path}")
        if committed_blob != EXPECTED_GIT_BLOBS[path]:
            raise ValueError(f"frozen source blob mismatch: {path}")
    for command in (("diff", "--quiet", "HEAD", "--", *paths),
                    ("diff", "--cached", "--quiet", "HEAD", "--", *paths)):
        subprocess.check_call(["git", *command], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    runner_revision = _git("rev-parse", "HEAD")
    engine_commit = _git("rev-parse", "--verify", f"{engine_revision}^{{commit}}")
    current_engine_blob = _git("hash-object", paths[2])
    frozen_engine_blob = _git("rev-parse", f"{engine_commit}:{paths[2]}")
    if current_engine_blob != frozen_engine_blob:
        raise ValueError("engine file does not match the supplied engine revision")
    plan_sha256 = hashlib.sha256(plan_file.read_bytes()).hexdigest()
    return {
        "plan_sha256": plan_sha256,
        "engine_revision": engine_commit,
        "runner_revision": runner_revision,
        "plan_git_blob": _git("rev-parse", f"HEAD:{paths[0]}"),
        "engine_git_blob": current_engine_blob,
        "runner_git_blob": _git("rev-parse", f"HEAD:{paths[1]}"),
        "aggregator_git_blob": _git("rev-parse", f"HEAD:{paths[3]}"),
        "reference_check_git_blob": _git("rev-parse", f"HEAD:{paths[4]}"),
        "benchmark_git_blob": _git("rev-parse", f"HEAD:{paths[5]}"),
    }



def verify_benchmark_report(
    report_file: Path,
    provenance: dict,
    runtime: dict,
    max_cpu_hours: float,
) -> dict:
    """Require a same-host, same-source, hashed performance preflight."""
    if (isinstance(max_cpu_hours, bool) or not isinstance(max_cpu_hours, (int, float))
            or not math.isfinite(float(max_cpu_hours)) or float(max_cpu_hours) <= 0):
        raise ValueError("max_cpu_hours must be a finite positive number")
    report = json.loads(Path(report_file).read_text(encoding="utf-8"))
    claimed = report.get("benchmark_sha256")
    unhashed = dict(report)
    unhashed.pop("benchmark_sha256", None)
    canonical = json.dumps(unhashed, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode("utf-8")
    actual = hashlib.sha256(canonical).hexdigest()
    if claimed != actual:
        raise ValueError("benchmark report hash is invalid")
    if (report.get("evidence_class") != "performance_preflight_only_not_calibration"
            or report.get("plan_id") != "M3-HAC-MBB-CALIBRATION-V2-3"):
        raise ValueError("benchmark report is not the required v2.0.3 performance preflight")
    provenance_keys = (
        "plan_sha256", "engine_revision", "runner_revision", "plan_git_blob",
        "engine_git_blob", "runner_git_blob", "aggregator_git_blob",
        "reference_check_git_blob", "benchmark_git_blob",
    )
    if any(report.get(key) != provenance.get(key) for key in provenance_keys):
        raise ValueError("benchmark report source/plan provenance does not match this checkout")
    if report.get("runtime") != runtime or report.get("platform") != runtime.get("platform"):
        raise ValueError("benchmark and calibration runtime/platform must match exactly")
    if (report.get("timed_bootstrap_replicates") != 9999
            or isinstance(report.get("timed_families"), bool)
            or not isinstance(report.get("timed_families"), int)
            or report["timed_families"] < 3):
        raise ValueError("benchmark must time at least three full 9999-replicate families")
    estimate = report.get("estimated_campaign_cpu_hours")
    if isinstance(estimate, bool) or not isinstance(estimate, (int, float)) or not math.isfinite(estimate) or estimate <= 0:
        raise ValueError("benchmark CPU-hour estimate is missing or invalid")
    if estimate > float(max_cpu_hours):
        raise ValueError("benchmark CPU-hour estimate exceeds the explicitly approved budget")
    return {
        "benchmark_sha256": claimed,
        "benchmark_estimated_cpu_hours": float(estimate),
        "approved_max_cpu_hours": float(max_cpu_hours),
    }
