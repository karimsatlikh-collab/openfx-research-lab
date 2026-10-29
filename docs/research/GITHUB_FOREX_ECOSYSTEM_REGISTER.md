# GitHub Forex Strategy & Research Ecosystem Register

**Review date:** 2026-10-29  
**Work item:** [WORK-2026-003](https://github.com/karimsatlikh-collab/video-research-team/issues/3)  
**Review mode:** Remote source/document inspection through GitHub API and public pages. No repository code was executed, installed, compiled, or independently backtested during this review.

## Executive summary

The most useful near-term approach is to learn from projects for different purposes rather than select a single “best EA”:

1. **MT5/MQL implementation and test-pipeline patterns:** EA31337.
2. **Fast parameter-grid research and signal exploration:** VectorBT, subject to a significant license restriction review before commercial use.
3. **Simple MIT-licensed MT5 EA examples with linked result artifacts:** geraked/metatrader5.
4. **Event-driven execution semantics, point-in-time correctness, and cross-framework parity concepts:** ml4t/backtest.

None of these reviews establishes a profitable trading edge. The most promising engineering lessons concern reproducible tests, execution assumptions, cost modeling, independent validation, and the separation of rapid hypothesis screening from final MT5 validation.

## Evidence labels

- **Observed:** directly present in a file or public repository page inspected on the review date.
- **Author claim:** the project's own description or documentation; not independently verified by us.
- **Reviewer assessment:** our interpretation of the inspected evidence.
- **Not tested:** no local build, code execution, or independent reproduction was performed.

Repository commit SHAs below are the latest commit results returned by GitHub commit search during this review; they are provenance anchors, not claims that every listed file was read at that exact commit. File blob SHAs are recorded where inspected. For a formal reuse decision, pin and re-review a specific commit/tag.

## Shortlist

| Priority | Project | Best use for our company | License / reuse gate | Current recommendation |
|---|---|---|---|---|
| 1 | [EA31337/EA31337](https://github.com/EA31337/EA31337) | MQL4/5 architecture, configurable strategy framework, CI compile and MT5 test workflow | GPL-3.0; copyleft obligations need legal review before copying or distributing derivatives | Study architecture and test orchestration; do not import code into proprietary components yet |
| 2 | [ml4t/backtest](https://github.com/ml4t/backtest) | Event-driven simulation semantics, point-in-time handling, trade/fill exports, framework-parity validation | MIT in inspected LICENSE | Study test design and audit fields; evaluate only in an isolated research environment before dependency adoption |
| 3 | [geraked/metatrader5](https://github.com/geraked/metatrader5) | Concrete MQL5 EA examples, indicator wiring, linked per-strategy report artifacts | MIT in inspected LICENSE | Use as a reference/test-fixture source after reviewing an individual EA and its report; never infer profitability from README alone |
| 4 | [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | Fast vectorized research and broad parameter sweeps | LICENSE.md says Apache 2.0 with Commons Clause; “Sell” restriction is a material commercial-use issue | Learn methodology/API concepts; no commercial embedding, redistribution, or service use until legal review clarifies intended use |

## Detailed reviews

### 1. EA31337 — MT5/MQL framework and automated test patterns

- Repository: https://github.com/EA31337/EA31337
- Review date: 2026-10-29
- Latest commit-search result: `9b9bd38c4e49dd6916f4fe3936e50e97fca7a692`
- Inspected README blob SHA: `07229ea1ad1c84e4559ad06d9ceacce269aabd55`
- Inspected LICENSE blob SHA: `94a9ed024d3859793618152ea559a168bbcbb5e2`
- Inspected test workflow blob SHA: `17c6ddf9bb959e68d190b53b1530209060ad5b4e`
- License observed: GNU GPL v3.
- Observed: README describes an MT4/MT5 Forex EA framework with multiple strategies and tunable parameters. The test workflow invokes a compile workflow and then a matrix of MT5 tests for several EA modes and selected years; the inspected configuration uses EURUSD, M1, and short date windows (January 1–14 for 2022 and 2024).
- Author claim: settings have been optimized for EURUSD and the framework supports strategy testing/optimization. This is not evidence of a durable edge.
- Reviewer assessment: this is the most directly relevant source for learning how to structure MQL code and wire an automated MT5 test job. Its short test windows are useful as smoke tests, not sufficient validation of profitability or robustness.
- Security/supply-chain note: the workflow calls a third-party tester action using a moving `@master` reference. Before adapting this workflow, pin third-party actions to reviewed immutable commit SHAs and keep credentials in scoped secrets. Do not copy workflow secrets or run unknown actions blindly.
- Reuse gate: GPL-3.0 obligations need legal review before code copying, modification, or distribution in a proprietary product.
- Decision: **LEARN / ARCHITECTURE REVIEW**. Next task: map the EA build/test workflow and identify ideas that can be recreated independently in our own test harness.

Evidence:
- README: https://github.com/EA31337/EA31337/blob/master/README.md
- License: https://github.com/EA31337/EA31337/blob/master/LICENSE
- Test workflow: https://github.com/EA31337/EA31337/blob/master/.github/workflows/test.yml
- Commit: https://github.com/EA31337/EA31337/commit/9b9bd38c4e49dd6916f4fe3936e50e97fca7a692

### 2. ml4t/backtest — event-driven engine and parity/audit concepts

- Repository: https://github.com/ml4t/backtest
- Review date: 2026-10-29
- Latest commit-search result: `76f716e7ce0a4636177cf082ddb891f0740c024a`
- Inspected README blob SHA: `978ca6a8ade97d1d90747c5c22cb1d04305f0b88`
- Inspected LICENSE blob SHA: `092521ff178aeedc4759e14b9a90741a22e771bd`
- License observed: MIT.
- Observed: README describes event-driven order/position handling, configurable same-bar vs next-bar fills, quote-aware execution, risk controls, trade/fill/portfolio exports, and framework-parity profiles. It provides a synthetic-data quick start and says the same Strategy class can be used by its live companion library.
- Author claims: point-in-time correctness/no look-ahead and framework parity validation. We did not execute the tests or independently audit these guarantees.
- Reviewer assessment: particularly relevant to our experiment manifest and independent validation requirements. Trade/fill-level ledgers and explicit execution semantics are valuable even if our final production/backtest path remains MT5.
- Limitation: it is a Python event-driven engine, not a substitute for proving MetaTrader 5 Strategy Tester compatibility, broker-specific costs, or MQL5 behavior. Do not assume framework parity from documentation alone.
- Decision: **LEARN / ISOLATED PROTOTYPE CANDIDATE**. Next task: inspect its tests and parity fixtures; choose a small synthetic scenario and independently reproduce expected fills before considering it as a dependency.

Evidence:
- README: https://github.com/ml4t/backtest/blob/main/README.md
- License: https://github.com/ml4t/backtest/blob/main/LICENSE
- Commit: https://github.com/ml4t/backtest/commit/76f716e7ce0a4636177cf082ddb891f0740c024a

### 3. geraked/metatrader5 — MQL5 examples and result-artifact organization

- Repository: https://github.com/geraked/metatrader5
- Review date: 2026-10-29
- Latest commit-search result: `d3eb29c382acf715727d5cd6a0414151e821fc2d`
- Inspected README blob SHA: `c98adf129b19e500ba99e52fae3d1b774769f3ad`
- Inspected LICENSE blob SHA: `828e454b066827da5692fda4cbcf669b3770160b`
- License observed: MIT.
- Observed: README indexes multiple MQL5 EAs and indicators, links source files, video walkthroughs, and per-strategy test/report folders. It explicitly warns that some EAs combine grid techniques and that optimal parameters may depend on symbol, timeframe, broker, and account.
- Author claim: the linked report artifacts document backtesting for the listed EAs. We have not opened and audited each individual report, its tick model, date span, spread/commission, or out-of-sample design.
- Reviewer assessment: useful for learning how to make strategy code, explanation, and test evidence navigable together. The README itself is not a validation report.
- Decision: **LEARN / SELECTIVE TEST-FIXTURE CANDIDATE**. Next task: choose one non-grid EA, inspect its code and the corresponding report folder, and document data period, tick model, costs, and whether any OOS evidence exists before drawing conclusions.
- Safety: do not install or run compiled binaries or scripts from the repository without source review and an isolated environment.

Evidence:
- README: https://github.com/geraked/metatrader5/blob/master/README.md
- License: https://github.com/geraked/metatrader5/blob/master/LICENSE
- Commit: https://github.com/geraked/metatrader5/commit/d3eb29c382acf715727d5cd6a0414151e821fc2d

### 4. VectorBT — high-throughput hypothesis screening

- Repository: https://github.com/polakowo/vectorbt
- Review date: 2026-10-29
- Latest commit-search result: `70da8fe7c2a57948ca065ac362fc416bcf31458c`
- Inspected README blob SHA: `dde730f3668dfb6c05e063c0181e8cf26f961c39`
- Inspected LICENSE.md blob SHA: `1ecf7675862c3caede8c26bed7150c6c41036d45`
- Observed license text: “Apache 2.0 with Commons Clause”; the added condition excludes the right to “Sell” the software as defined in that license. This is not an ordinary unrestricted Apache-2.0-only grant.
- Observed: README describes vectorized research over assets/timeframes and broad parameter grids, with pandas/NumPy/Numba and an optional Rust engine. It also distinguishes the community edition from VectorBT PRO.
- Reviewer assessment: conceptually aligned with rapid parameter screening. But a vectorized engine can differ from MT5 in fill timing, spread, tick-level stops, slippage, margin, and intrabar order. Results should be treated as screening signals until reproduced under the final execution model.
- Reuse gate: the Commons Clause restriction is material for a commercial research service or product whose value derives substantially from the software. **Do not embed, redistribute, or offer it as a paid service before legal review.** Reading concepts and independently implementing a method are separate from copying code.
- Decision: **LEARN / LICENSE REVIEW REQUIRED / NO DEPENDENCY APPROVAL**.

Evidence:
- README: https://github.com/polakowo/vectorbt/blob/master/README.md
- License: https://github.com/polakowo/vectorbt/blob/master/LICENSE.md
- Test workflow: https://github.com/polakowo/vectorbt/blob/master/.github/workflows/tests.yml
- Commit: https://github.com/polakowo/vectorbt/commit/70da8fe7c2a57948ca065ac362fc416bcf31458c

## Cross-project conclusions

1. Keep **hypothesis screening** and **final execution-model validation** separate. A fast Python sweep may shortlist ideas; it cannot by itself validate an MQL5/MT5 EA.
2. A successful compile or short CI smoke test is a software check, not a profitability finding.
3. Every strategy result should include exact source/data version, timeframe, tick model, date boundaries, parameter set, spread, commission, slippage assumptions, trade/fill ledger, and out-of-sample status.
4. Do not accept author claims, stars, screenshots, or a single best parameter set as evidence of a robust edge.
5. Preserve negative findings and test failures as first-class research outputs.
6. Review license and supply-chain risk before reuse. In particular, GPL-3.0 and Apache-2.0-with-Commons-Clause require different decisions; do not treat all “open source” as interchangeable.
7. No code from these projects was run during this review, and no external contribution or maintainer contact has been made.

## Follow-up work

- [ ] Inspect a specific EA31337 release/commit and map its compile + test pipeline, including action pinning and test artifacts.
- [ ] Select one non-grid EA from geraked/metatrader5 and audit its source plus actual report files.
- [ ] Inspect ml4t/backtest tests and one parity fixture; reproduce a tiny deterministic case independently.
- [ ] Ask legal review to decide whether any intended VectorBT use is compatible with its Commons Clause.
- [ ] Compare the above lessons against the company's MT5 Windows VPS proof-of-concept. This ecosystem work does not replace the priority task of proving continuous MT5 Strategy Tester execution and large parameter optimization on a compatible Windows environment.
