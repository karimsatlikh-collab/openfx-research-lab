"""Deterministic synthetic research harness; not a market simulator or backtest."""
from __future__ import annotations
import hashlib
import random
from typing import Any


def seeded_returns(*, seed: int, n: int, edge: float = 0.0, noise: float = 1.0) -> list[float]:
    """Generate a repeatable stream of synthetic trade returns in arbitrary units."""
    if n < 1:
        raise ValueError("n must be >= 1")
    if noise < 0:
        raise ValueError("noise must be >= 0")
    rng = random.Random(seed)
    return [edge + rng.gauss(0.0, noise) for _ in range(n)]


def summarize_returns(returns: list[float]) -> dict[str, Any]:
    if not returns:
        raise ValueError("returns must not be empty")
    equity = peak = max_drawdown = 0.0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    mean = sum(returns) / len(returns)
    digest = hashlib.sha256(",".join(format(x, ".17g") for x in returns).encode()).hexdigest()
    return {
        "sample_size": len(returns),
        "mean_return": mean,
        "positive_fraction": sum(x > 0 for x in returns) / len(returns),
        "max_drawdown_units": max_drawdown,
        "returns_sha256": digest,
        "evidence_level": "synthetic",
        "is_market_backtest": False,
    }


def run_synthetic(*, seed: int, n: int, edge: float = 0.0, noise: float = 1.0) -> dict[str, Any]:
    returns = seeded_returns(seed=seed, n=n, edge=edge, noise=noise)
    return {"seed": seed, **summarize_returns(returns)}
