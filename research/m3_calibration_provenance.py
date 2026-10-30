"""Fail-closed provenance binding for M3 v2 synthetic calibration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_ENGINE_REVISION = "087e66622f27350f1999d2e5b2ec82a9ead78982"
EXPECTED_GIT_BLOBS = {
    "docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md": "c88a2a9c5e74d988feac70465e04e5689eb53492",
    "research/m3_hac_mbb_v2_calibration.py": "0a952e210e38db28e319b2d43e8e1ec776173ee3",
    "openfx/selection_bias_v2.py": "72a69166e8121e7d866baa7cb77479975dd04161",
    "research/aggregate_m3_hac_mbb_v2.py": "931db864ad41d70dbc41029a2937aa697ddd7f83",
    "research/validate_m3_v2_reference.py": "5eee54aedcb0054e07f2f23fe7551057106d396a",
    "research/benchmark_m3_v2_family.py": "885d748eeb211cf62bbc86b5f590bf87ac393c73",
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
