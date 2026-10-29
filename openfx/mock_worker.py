"""A safe local mock worker for testing OpenFX's experiment lifecycle.

It never launches MT5, executes user-provided commands, connects to brokers, or trades.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .experiment import load_manifest, save_manifest, transition

logger = logging.getLogger("openfx.mock_worker")


def run_mock(manifest_path: str | Path) -> dict:
    path = Path(manifest_path)
    manifest = load_manifest(path)
    if manifest["status"] != "QUEUED":
        raise ValueError("mock worker only accepts QUEUED experiments")

    running = transition(manifest, "RUNNING")
    running["execution"]["mode"] = "mock"
    running["execution"]["worker_version"] = "openfx-mock-worker/0.1"
    save_manifest(running, path)

    # Deterministic placeholder result; it is explicitly NOT a backtest.
    completed = transition(
        running,
        "COMPLETED",
        result={
            "kind": "mock",
            "is_backtest": False,
            "is_trading_signal": False,
            "message": "Lifecycle smoke test only; no market data or strategy was tested.",
        },
    )
    save_manifest(completed, path)
    logger.info("Mock lifecycle completed for %s", completed["experiment_id"])
    return completed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="Path to a queued JSON experiment manifest")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        result = run_mock(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Mock run failed: %s", exc)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
