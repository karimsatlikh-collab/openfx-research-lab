# OpenFX quick start

This guide runs only local Python checks. It does not need MT5, a VPS, broker credentials, or market data.

## Requirements

Python 3.10 or newer (the CI workflow currently uses Python 3.12).

## 1. Run the tests

From the repository root:

    python -m unittest discover -s tests -v

The tests cover manifest validation, state transitions, file persistence, and the mock lifecycle. They do not measure trading performance.

## 2. Create a sample experiment manifest

    python create_experiment.py --id demo-001 --hypothesis "Synthetic lifecycle check only" --strategy-version "not-implemented" --symbol EURUSD --timeframe M15 --start 2024-01-01 --end 2024-06-30 --parameters-json '{"fixture": true}' --output data/experiments/demo-001.json

This creates a JSON record in QUEUED state. The hypothesis is a label, not a confirmed strategy rule.

## 3. Exercise the mock worker

    python -m openfx.mock_worker data/experiments/demo-001.json

The mock worker changes the record through RUNNING to COMPLETED and records that no backtest occurred. It refuses to re-run a record that is not QUEUED. Use a new experiment ID and output file for another smoke test.

## What these commands do not do

- They do not install or launch MT5.
- They do not download price data.
- They do not compile an EA or run Strategy Tester.
- They do not connect to a broker or place orders.
- They do not establish that a trading strategy is profitable.

After pushing changes, inspect the repository's Actions tab to confirm whether GitHub's CI test run passed.
