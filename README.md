# OpenFX Research Lab

**Short name:** OpenFX  
**Tagline:** *Research. Test. Validate. Improve.*  
**Project type:** Publicly visible, rights-reserved research and engineering repository for Forex trading strategies.

> **OpenFX is a research project, not a promise of trading profits.** A backtest or optimization result alone does not establish a durable trading edge.

## Copyright and use permission

This repository is public for viewing and project transparency, but its original materials are **not offered under an open-source license**. The root `LICENSE` file reserves all rights. Public visibility does not grant general permission to copy, modify, redistribute, or commercially use the project's original code. Third-party components, if any, remain subject to their own licenses. External code contributions are not accepted for incorporation unless the project owner first establishes written contribution terms and grants the necessary permission.

## Mission

Build an AI-assisted platform that can discover authorized research sources, preserve evidence provenance, formalize trading ideas into falsifiable hypotheses and precise rules, implement them, run reproducible experiments, and evaluate results independently. The priority is a trustworthy research process and a defensible, repeatable trading edge—not code volume or large-scale optimization.

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

Research question → authorized source/evidence review → atomic claims → pre-registered Hypothesis Card → explicit rule specification → frozen experiment plan and trial-family registration → implementation → controlled development tests → validation → untouched final OOS → independent validation → documented decision.

Claims should be labelled as:
- **Verified:** directly checked evidence.
- **Source claim:** asserted by a source, not independently reproduced.
- **Hypothesis:** a proposed idea requiring testing.
- **Unknown / not tested:** evidence or execution is not yet available.

## Main workstreams

1. **Strategy research and validation:** source-linked hypotheses, explicit falsification criteria, MQL5/MT5 implementation, cost-aware tests, separate development/validation/final OOS, robustness and independent replication.
2. **Source discovery:** permitted videos, transcripts, papers, documentation, datasets, and public code; preserve provenance and licensing information.
3. **Backtest operations:** experiment IDs, frozen manifests, queue state, logs, artifact hashes, and future unattended Strategy Tester runs on a compatible Windows host.
4. **Research governance and engineering:** trial accounting, statistical calibration, data quality, security, documentation, and independent review. Functional team labels do not imply separate agents or independent credentials.


## Research controls and priority gates

- Every strategy idea must have a versioned Hypothesis Card written and frozen before its results are inspected: source-linked rationale, falsifiable statement, predicted mechanism, exact rules/parameters, invalidation criteria, primary metrics, costs, data splits, trial-family ID, and trial budget.
- Register every attempted trial, including failed, rejected, interrupted, and abandoned attempts. Do not reset a trial family to hide prior searches.
- Calibrate the synthetic research harness against pre-registered null/no-edge generators, planted effects, and deliberate leakage fixtures. Report denominators and confidence intervals; a small green test suite is not statistical calibration.
- Do not run broad parameter grids or select a winner until trial accounting, calibration, and selection-bias controls have passed independent review. Any multiple-testing method must actually be applied, not merely named in metadata.
- Keep development, validation, and final out-of-sample data separate. The final OOS set remains inaccessible to the proposing/optimizing process; cap and log any validator feedback.
- Separate author, executor, approver, and independent validator duties. An AI or worker must not approve its own job or certify its own result. Human-controlled approval must be bound to the exact frozen job/config/source/data/cost digests.
- Treat mock and synthetic runs as harness evidence only. A CI pass, synthetic reproduction, or successful worker lifecycle is not an MT5 backtest and does not establish market edge or profitability.
- Start with zero-cost local reproducibility. VPS, paid APIs/compute, broker credentials, and live trading remain disabled until separately approved.

## Experiment states

QUEUED → RUNNING → COMPLETED or FAILED

The current worker is mock-only. A future MT5 worker must record verifiable tester reports and logs, code/build hashes, data revision, symbol/timeframe, exact date range, modeling mode, costs, parameters, and development/validation/final out-of-sample splits. Failed, interrupted, and negative results must be retained.

## Security boundaries

- Do not commit credentials, broker logins, tokens, private keys, or personal data.
- Do not attach a persistent self-hosted runner with secrets or broker access to this public repository.
- Do not allow arbitrary shell or executable commands from public issues, pull requests, or job manifests.
- Keep real remote execution disabled until a private, least-privilege control plane and threat model are reviewed.
- Live trading is outside the default scope and requires separate explicit authorization.

For the current Windows VPS worker prototype, see [worker/README.md](worker/README.md) and [docs/OWNER_NEXT_STEPS_AI_TOOLS.md](docs/OWNER_NEXT_STEPS_AI_TOOLS.md). Start with [docs/QUICKSTART.md](docs/QUICKSTART.md). See [docs/OWNER_PREREQUISITES.md](docs/OWNER_PREREQUISITES.md), [docs/AI_WORKER_ARCHITECTURE.md](docs/AI_WORKER_ARCHITECTURE.md), [docs/CLAUDE_REVIEWER.md](docs/CLAUDE_REVIEWER.md), [CONTRIBUTING.md](CONTRIBUTING.md), [docs/EXPERIMENT_MANIFEST.md](docs/EXPERIMENT_MANIFEST.md), [docs/SECURE_EXECUTION.md](docs/SECURE_EXECUTION.md), and [docs/OPEN_DECISIONS.md](docs/OPEN_DECISIONS.md).

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
