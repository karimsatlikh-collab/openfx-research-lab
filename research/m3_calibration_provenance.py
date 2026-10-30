"""Fail-closed provenance binding for M3 v2 synthetic calibration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_ENGINE_REVISION = "087e66622f27350f1999d2e5b2ec82a9ead78982"
EXPECTED_GIT_BLOBS = {
    "docs/M3_HAC_MBB_V2_CALIBRATION_PLAN.md": "059baa1472aa9311d3fa5a1769484ce15901b535",
    "research/m3_hac_mbb_v2_calibration.py": "7b1d6d628cddf42ac126be7a6378583727d8e5e8",
    "openfx/selection_bias_v2.py": "72a69166e8121e7d866baa7cb77479975dd04161",
    "research/aggregate_m3_hac_mbb_v2.py": "42265c3396c3233181ac88f1c3aa213c9ab83032",
    "research/validate_m3_v2_reference.py": "6c5af70028babcf454d922e7c85a1bd01a67b4b7",
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
             (plan_file, runner_file, engine_file, aggregator_file, reference_file)]
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
    }
