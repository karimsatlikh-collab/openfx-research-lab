# OpenFX Research Lab

**Short name:** OpenFX  
**Tagline:** *Research. Test. Validate. Improve.*  
**Project type:** Open, evidence-driven research and engineering for Forex trading strategies.

> **OpenFX is a research project, not a promise of trading profits.** Its purpose is to build a reproducible process for discovering, implementing, testing, and independently validating strategies. A backtest or optimization result alone does not establish a durable trading edge.

## Mission

Build an AI-assisted platform that can discover research sources, formalize trading ideas into precise rules, implement them, run reproducible experiments, and evaluate results independently. The long-term priority is reliable, repeatable Forex strategy research and large-scale backtesting/parameter optimization—not video collection for its own sake.

## Main workstreams

1. **Strategy research and validation — primary**
   - Define explicit, reviewable hypotheses and trading rules.
   - Implement research prototypes and MetaTrader 5 / MQL5 Expert Advisors.
   - Run baseline backtests, then controlled parameter searches.
   - Validate with realistic trading costs, out-of-sample periods, walk-forward analysis, sensitivity checks, and independent review.
   - Preserve negative, failed, interrupted, and superseded experiments.

2. **Source discovery and knowledge acquisition — supporting**
   - Find permitted educational videos, transcripts, papers, documentation, datasets, and public code.
   - Record source provenance, timestamps, licenses, permissions, and uncertainty.
   - Check extraction quality before treating extracted text as evidence.
   - Separate source-confirmed rules from interpretations and team hypotheses.

3. **Backtest operations and reliability**
   - Design versioned experiment manifests, job queues, result records, and artifact checks.
   - Prepare for unattended MT5 Strategy Tester runs and broad parameter optimization on a compatible Windows host.
   - Design secure, constrained communication with future infrastructure.
   - Never report a test as run unless logs and artifacts demonstrate that it ran.

4. **Open-source collaboration**
   - Welcome useful contributions in MQL5, Python, testing, data quality, research methodology, documentation, and security.
   - Prefer small, reproducible contributions with clear evidence.
   - Review license and security implications before adopting external code or dependencies.

## Research lifecycle

Research question → source and evidence review → explicit rule specification → implementation → baseline test → controlled optimization → independent validation → documented decision.

Every material claim should be labelled as one of:
- **Observed / verified:** directly checked evidence.
- **Source claim:** asserted by an external author or source, not independently reproduced.
- **Hypothesis:** a proposed idea that still needs testing.
- **Not tested / unknown:** no adequate execution or evidence yet.

## Current status

The repository currently contains project specifications, research notes, workflow/templates, and early code skeletons. The project is still under development; not every documented capability is implemented or operational.

- The future Windows VPS purchase and MT5 installation are deferred until separately approved.
- No VPS worker or ChatGPT-to-VPS connection is currently deployed.
- Public GitHub research has identified projects worth reviewing, but those reviews do not prove strategy profitability.
- A persistent self-hosted GitHub Actions runner must **not** be attached to this public repository. Any future privileged execution system must use a suitably restricted control plane and reviewed security design.

## How to contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Good first contributions include:
- Reproducible synthetic-data tests and bug reports.
- Improving MQL5/Python test diagnostics and report provenance.
- Reviewing public research tools and licenses.
- Improving transcript extraction quality checks.
- Documentation, experiment schemas, and artifact-validation tests.

Please do not submit broker credentials, access tokens, private keys, account details, or other secrets. Do not include proprietary strategy details without authorization. Do not claim profitability without independently reproducible evidence.

## Principles

- Reproducibility over impressive screenshots.
- Independent validation over self-confirmation.
- Preserve negative results.
- No look-ahead bias or hidden future information.
- Realistic spread, commission, slippage, and execution assumptions.
- Separate development, validation, and untouched final out-of-sample data.
- No live trading unless separately and explicitly authorized.
- Respect licenses, access controls, privacy, and source terms.
- Never claim access, execution, compilation, or deployment without evidence.

## Project identity

The conversational invocation name is **OpenFX**. The formal project name is **OpenFX Research Lab**. The intended repository name is `openfx-research-lab`; the current GitHub repository URL may continue to contain the previous name until its owner changes it in GitHub repository settings.

