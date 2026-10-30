"""Fail-closed provenance binding for M3 v2 synthetic calibration."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    paths = [p.relative_to(ROOT).as_posix() for p in (plan_file, runner_file, engine_file)]
    for path in paths:
        worktree_blob = _git("hash-object", path)
        committed_blob = _git("rev-parse", f"HEAD:{path}")
        if worktree_blob != committed_blob:
            raise ValueError(f"working file differs from checked-out commit: {path}")
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
    }
