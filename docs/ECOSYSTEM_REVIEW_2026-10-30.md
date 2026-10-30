# Evidence-Based Forex Research Ecosystem Review

Review date: 2026-10-30  
Scope: read-only public GitHub discovery; no code execution, dependency installation, forks, issues, PRs, or maintainer contact.  
Purpose: identify reusable lessons for OpenFX research architecture. This is not a recommendation to copy or incorporate third-party code.

## Executive decision

No external repository should be integrated into OpenFX at this stage. The most useful candidates are:
1. **EarnForex MT5 EA Template** — MQL5 structural reference for order handling, sizing, ATR stops, spread/slippage settings, and partial close; Apache-2.0, but its latest inspected commit is from June 2025 and no automated test suite was established in this limited review.
2. **QuantStats** — optional post-trade reporting/analytics reference; Apache-2.0 with a visible test suite and recent maintenance. It is not a backtester and does not provide selection-bias correction.
3. **QuantConnect LEAN** — long-term architecture reference for event-driven multi-asset execution and Forex support; Apache-2.0, actively maintained, but very large and operationally expensive to adopt.
4. **MQPy** — a Python-to-MT5 template/bridge reference, MIT, but its current code is not suitable as an execution worker without substantial safety work.

The best immediate learning path is to inspect EarnForex's MQL5 patterns and QuantStats' analytics separately, while keeping OpenFX's own execution contracts, costs, provenance, and statistical gates authoritative.

## Candidate register

| Repository | Latest inspected commit | Last commit date | License observed | Scope and evidence | Decision |
|---|---|---:|---|---|---|
| [EarnForex/MT5-Expert-Advisor-Template](https://github.com/EarnForex/MT5-Expert-Advisor-Template) | `170b79555c02336e300803e67b567be1d8d71b38` | 2025-06-20 | Apache-2.0 | MQL5 EA template; README describes position sizing, ATR-based SL/TP, and basic error handling. Source includes max positions, risk base, spread/slippage, ATR stops, and partial-close controls. | Study as MQL5 reference only. No code reuse yet. |
| [Joaopeuko/Mql5-Python-Integration](https://github.com/Joaopeuko/Mql5-Python-Integration) | `4d488d1bfc2ea567bd99e29b928b1a22561e78dc` | 2025-04-29 | MIT | MQPy generates Python strategy templates and calls MetaTrader5 package APIs; README requires Windows, Python 3.8+, and MT5 installed. | Reject as a core engine; useful only as a bridge-design reference after security review. |
| [kernc/backtesting.py](https://github.com/kernc/backtesting.py) | `ca2e2611621e472542ba90f7243a1fa06a7d7108` | 2026-08-05 | AGPL-3.0 | Python bar-based backtesting; includes EURUSD sample data, tests, and CI. Latest inspected commit fixed shared-memory sizing for RangeIndex optimization and added a regression test. | Strong test/research reference, but no incorporation without separate AGPL legal review. |
| [QuantConnect/Lean](https://github.com/QuantConnect/Lean) | `c16df853745b06e2ea09471963c72d8bef85ee55` | 2026-10-30 | Apache-2.0 | Large event-driven algorithmic trading engine. Inspected BasicTemplateAlgorithm source explicitly documents AddForex and Forex resolutions; repository is very large (about 587 MB reported by GitHub metadata). | Architecture reference only; adoption is disproportionate to current OpenFX needs. |
| [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) | `9ef4c6d0a4ffe7831f6ebba6a5824fd33a90c05a` | 2026-09-27 | Apache-2.0 | Portfolio analytics library; inspected stats module and tests for returns, win rate, drawdown, and related metrics. | Candidate for reporting concepts only, after OpenFX's own return/evidence contracts are stable. |
| [polakowo/vectorbt](https://github.com/polakowo/vectorbt) | `70da8fe7c2a57948ca065ac362fc416bcf31458c` | 2026-10-28 | Apache-2.0 + Commons Clause | Vectorized research/backtesting framework with current CI and active commits. The repository's LICENSE.md adds a Commons Clause restriction on selling the software or services deriving substantially from it. | Do not incorporate without specific legal review; reference only. |
| [mementum/backtrader](https://github.com/mementum/backtrader) | `b853d7c90b6721476eb5a5ea3135224e33db1f14` | 2023-04-19 | GPL-3.0 | Event-driven Python backtesting/live-trading platform; README describes Oanda REST feed, multiple timeframes, commission/slippage and order types. | Not preferred: stale relative to current candidates and strong copyleft. |
| [sre888/forex-backtesting-engine](https://github.com/sre888/forex-backtesting-engine) | `a159c09b56721f27d3bc1577a62bf335da0b52bb` | 2025-11-10 | No LICENSE file found | README claims SMA-crossover Forex backtesting, SL/TP, sizing, analytics and optimization; latest inspected commit says it was created using Colab. | Reject for reuse: no explicit license and no independent evidence of robust testing. |

## Detailed review: MQPy (Joaopeuko/Mql5-Python-Integration)

### What was inspected
- README and MIT license.
- `pyproject.toml`, `setup.py`.
- `mqpy/template.py`, `mqpy/trade.py`, `mqpy/rates.py`, `mqpy/tick.py`, `mqpy/logger.py`, and `mqpy/__main__.py`.
- Latest inspected commit: `4d488d1bfc2ea567bd99e29b928b1a22561e78dc` (2025-04-29).

### What it actually provides
MQPy is not a backtesting engine or a research orchestrator. It generates Python EA templates and exposes wrappers around MetaTrader5 APIs for ticks, rates, and trade operations. The generated templates include moving-average, RSI, MACD, and Bollinger examples.

### Concrete findings
1. `pyproject.toml` declares package version `0.6.11`, while the inspected `setup.py` still declares `0.6.9`. This is a packaging/release-consistency issue.
2. `pyproject.toml` declares no runtime dependencies, but `mqpy.trade`, `mqpy.rates`, and `mqpy.tick` import `MetaTrader5` directly. The README says MT5 must be installed on Windows, but a fresh environment also needs the Python MetaTrader5 package.
3. The generated moving-average template defaults to a fixed 1.0 lot, uses fixed stop/take-profit point values, and loops continuously without an explicit sleep/backoff. It is an example template, not a risk-controlled research worker.
4. `Trade.open_position` sends live MT5 deal requests through `Mt5.order_send`. The class contains helper methods for trade-mode restrictions, but the inspected `open_position` path does not call those helpers before sending orders.
5. `Tick` reads fields from `Mt5.symbol_info_tick(symbol)` without first checking for a `None` response. `Rates` does check for missing data and raises a ValueError.
6. `Trade.request_result` is annotated as receiving an integer but treats the value as an MT5 result object with `.retcode`; it also assumes the result is not `None`.
7. The project has optional pytest development dependencies, but the inspected test path `tests/test_mqpy.py` and a conventional `.github/workflows/ci.yml` were not found. This is not proof that no tests exist elsewhere; a full tree audit was not completed.

### Assessment
MQPy may help demonstrate the shape of a Python-to-MT5 bridge, but it should not be adopted as OpenFX's worker. It performs live order submission, lacks the research-job state/evidence contracts OpenFX requires, and the inspected order path has safety gaps. Do not install it on a trading terminal or run its templates as part of this research project.

## Detailed review: EarnForex MT5 EA Template

### What was inspected
- README, Apache-2.0 license, and `Experts/MT5-EA-Template.mq5`.
- Latest inspected commit: `170b79555c02336e300803e67b567be1d8d71b38` (2025-06-20).

### Useful design patterns
- Explicit risk base (equity, balance, free margin) and fixed-vs-risk-based position sizing.
- Minimum/maximum lot limits and maximum position count.
- Explicit spread and slippage inputs.
- Separate fixed/ATR stop-loss and take-profit modes.
- Partial-close controls and tick-size normalization.
- Error descriptions and order-result checks through a standard Trade object.

### Limitations
- It is a template, not a proven strategy or a research/backtesting engine.
- The source includes `MQLTA ErrorHandling.mqh` and `MQLTA Utils.mqh`; dependency provenance and their licenses must be checked before any reuse.
- The latest inspected commit is more than a year old at review date.
- No automated compile/backtest or test suite was verified in this limited review.
- README/code warnings explicitly disclaim guaranteed behavior.

### Assessment
Use it as a reference for MQL5 implementation conventions only. It does not validate the statistical method, market edge, broker-specific fill behavior, or OpenFX's execution contracts.

## Research and validation lessons

- A backtesting engine's optimization API is not a selection-bias correction. OpenFX must keep its own complete trial registry, pre-registration, M3 gate, OOS isolation, and cost model.
- Performance analytics libraries can calculate Sharpe, drawdown, win rate, and tear sheets, but these metrics do not prove a strategy edge and do not replace DSR/PBO or family-wise error controls.
- MT5 bridge libraries that can submit orders are execution-risk components, not harmless data connectors. They require a restricted worker, allowlisted operations, demo-only controls, and an independent validator.
- Public visibility is not permission to copy. License compatibility, copyright notices, attribution, dependency licenses, and the project's rights-reserved notice must be reviewed before any code reuse.
- No external repository code was executed, installed, forked, or copied during this review.

## Recommendation and next step

1. Keep OpenFX's own schemas, registry, validation gate, and worker contract authoritative.
2. If the owner authorizes a deeper review, prioritize:
   - EarnForex MQL5 template for risk/order-management patterns;
   - MQPy only for a read-only bridge/API design review, not for live order submission;
   - QuantStats for post-run reporting concepts.
3. Do not incorporate backtesting.py, vectorbt, or backtrader without separate license/legal approval.
4. Do not use any repository's claimed backtest results as evidence of profitability.
5. Before any integration, produce a file-level review, license/dependency inventory, security review, isolated test plan, and explicit owner approval.

Status: curated discovery and first-pass source review completed; no code reuse or external collaboration authorized.
