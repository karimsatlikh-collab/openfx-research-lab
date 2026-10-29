# OpenFX Research Lab

**Short name:** OpenFX  
**Tagline:** *Research. Test. Validate. Improve.*  
**Project type:** Publicly visible, rights-reserved research and engineering repository for Forex trading strategies.

> **OpenFX is a research project, not a promise of trading profits.** A backtest or optimization result alone does not establish a durable trading edge.

## Copyright and use permission

This repository is public for viewing and project transparency, but its original materials are **not offered under an open-source license**. The root `LICENSE` file reserves all rights. Public visibility does not grant general permission to copy, modify, redistribute, or commercially use the project's original code. Third-party components, if any, remain subject to their own licenses. External code contributions are not accepted for incorporation unless the project owner first establishes written contribution terms and grants the necessary permission.

## Mission

Build an AI-assisted platform that can discover research sources, formalize trading ideas into precise rules, implement them, run reproducible experiments, and evaluate results independently. The priority is reliable, repeatable Forex strategy research and large-scale backtesting/parameter optimization.

## Current implementation

The repository now includes:
- A Python startup/status scaffold.
- Versioned experiment manifests with basic validation and state transitions.
- A deterministic mock worker for testing the experiment lifecycle without MT5 or market data.
- Unit tests for manifest validation, legal transitions, persistence, and mock-worker behavior.
- A GitHub Actions workflow for running the standard-library test suite.
- Documentation for experiment evidence requirements and the future secure execution boundary.

The mock worker does **not** run a backtest, test a trading strategy, connect to a broker, or place trades. Do not treat its successful lifecycle as trading evidence. CI execution should be checked in the Actions tab before describing the tests as passed.

## Research lifecycle

Research question → source/evidence review → explicit rule specification → implementation → baseline test → controlled optimization → independent validation → documented decision.

Claims should be labelled as:
- **Verified:** directly checked evidence.
- **Source claim:** asserted by a source, not independently reproduced.
- **Hypothesis:** a proposed idea requiring testing.
- **Unknown / not tested:** evidence or execution is not yet available.

## Main workstreams

1. **Strategy research and validation:** precise hypotheses, MQL5/MT5 implementation, cost-aware backtests, out-of-sample validation, walk-forward analysis, robustness checks.
2. **Source discovery:** permitted videos, transcripts, papers, documentation, datasets, and public code; preserve provenance and licensing information.
3. **Backtest operations:** experiment IDs, frozen manifests, queue state, logs, artifact hashes, and future unattended Strategy Tester runs on a compatible Windows host.
4. **Project collaboration:** Python, MQL5, testing, data quality, methodology, documentation, and security, subject to the rights-reserved notice and explicit written permission.

## Experiment states

QUEUED → RUNNING → COMPLETED or FAILED

The current worker is mock-only. A future MT5 worker must record verifiable tester reports and logs, code/build hashes, data revision, symbol/timeframe, exact date range, modeling mode, costs, parameters, and development/validation/final out-of-sample splits. Failed, interrupted, and negative results must be retained.

## Security boundaries

- Do not commit credentials, broker logins, tokens, private keys, or personal data.
- Do not attach a persistent self-hosted runner with secrets or broker access to this public repository.
- Do not allow arbitrary shell or executable commands from public issues, pull requests, or job manifests.
- Keep real remote execution disabled until a private, least-privilege control plane and threat model are reviewed.
- Live trading is outside the default scope and requires separate explicit authorization.

Start with [docs/QUICKSTART.md](docs/QUICKSTART.md). See [CONTRIBUTING.md](CONTRIBUTING.md), [docs/EXPERIMENT_MANIFEST.md](docs/EXPERIMENT_MANIFEST.md), [docs/SECURE_EXECUTION.md](docs/SECURE_EXECUTION.md), and [docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md).

## Status and next boundary

The future Windows VPS purchase and MT5 installation are intentionally deferred. No VPS worker or ChatGPT-to-VPS connection is deployed. Never claim that code was compiled, MT5 was run, or a backtest was completed unless logs and artifacts verify it.

## Principles

- Reproducibility over screenshots.
- Independent validation over self-confirmation.
- Preserve negative results.
- No look-ahead bias or future-bar leakage.
- Realistic spread, commission, slippage, and execution assumptions.
- Separate development, validation, and untouched final out-of-sample data.
- Review third-party licenses and security before adopting code or dependencies.
