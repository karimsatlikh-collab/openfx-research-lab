# MT5 backtest result contract

## Purpose

`schemas/backtest-result-v1.schema.json` and `openfx/backtest_result.py` define a reproducible record for a future MT5 Strategy Tester run. They require:

- Source commit, EA binary hash, data hash, terminal build, symbol/timeframe, and date range.
- Modeling mode, deposit/currency/leverage, and explicit spread, commission, and slippage assumptions.
- Non-overlapping chronological development, validation, and final out-of-sample intervals.
- Trade count, net/gross P&L, profit factor, expected payoff, and drawdown metrics.
- SHA-256/size/path records for tester report, journal log, EA binary, and data manifest.
- Explicit verification attestations for report parsing, journal completeness, data coverage, costs, and split boundaries.

## Validation semantics

Run validation from Python:

```python
from openfx.backtest_result import validate_backtest_result

review = validate_backtest_result(result_dict)
print(review)
```

- `ready_for_independent_review` means only that required metadata/artifact declarations and verification attestations are present and internally consistent.
- `incomplete` includes blockers such as missing artifacts or unverified costs/logs.
- Warnings identify selected metric inconsistencies, such as profit factor not matching gross profit divided by gross loss.
- This validator does **not** inspect artifact bytes, parse a real MT5 report, verify that attestations are truthful, prove that the tester actually ran, or establish profitability. Those are still required before any result is considered independently verified.

A synthetic test fixture exists only in the unit tests; it is not a real backtest. Do not fabricate artifact hashes, set verification flags to true without evidence, or mark mock-worker output as an MT5 result.
