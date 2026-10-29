# Contributing to OpenFX Research Lab

Thank you for considering a contribution to OpenFX. We welcome contributions that improve reproducibility, research quality, data provenance, test engineering, reliability, security, and documentation.

## Before you start

1. Read the project mission and current status in [README.md](README.md).
2. Check existing issues and research notes to avoid duplicating work.
3. For a substantial change, open an issue describing the question, proposed approach, expected evidence, risks, and acceptance criteria.
4. Keep a contribution focused and small enough to review.

## Useful contribution areas

- Python tooling, schemas, validation, and automated tests.
- MQL5/MetaTrader 5 testing patterns and diagnostics.
- Synthetic fixtures for fills, timing, costs, and edge cases.
- Data and transcript extraction quality evaluation.
- Research-tool ecosystem reviews and license/security analysis.
- Documentation, onboarding, and reproducibility improvements.

## Evidence and research standards

- Distinguish verified observations, source-author claims, hypotheses, and untested assumptions.
- Include reproduction steps, environment details, and test output where applicable.
- Preserve failed and negative results; do not remove them to make a result look better.
- Avoid look-ahead bias, future-bar leakage, survivorship bias, and repeated tuning against the final out-of-sample set.
- A profitable historical backtest is not, by itself, evidence of a durable trading edge.
- Do not claim a test, compile, deployment, or extraction completed unless the supporting logs or artifacts exist.

## Code and pull requests

- Explain what changed, why it is needed, and how it was checked.
- Add or update tests for behavior changes.
- Keep credentials, private keys, broker logins, tokens, and sensitive personal data out of commits, issues, logs, and examples.
- Do not introduce arbitrary shell/PowerShell execution, unreviewed remote code execution, or unrestricted worker commands.
- Pin and review third-party actions and dependencies before using them in privileged workflows.
- Do not attach a persistent self-hosted runner to this public repository.
- Review external project licenses before copying code or adding dependencies.
- Avoid changes that silently alter confirmed strategy rules, validation splits, or baseline results.

## Strategy claims and live trading

OpenFX is a research and validation project, not a signal service or profit guarantee. Any strategy-performance claim should identify the code revision, data and date range, symbol/timeframe, modeling mode, costs, parameter-selection process, and out-of-sample/robustness evidence. Live trading is outside the default scope and requires separate explicit authorization.

## Communication

Be respectful, specific, and evidence-oriented. If something is uncertain, say so. A useful report of a failed experiment is welcome when it helps the project learn.
