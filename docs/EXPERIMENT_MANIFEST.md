# Experiment manifest v1

OpenFX uses a versioned JSON manifest to describe a proposed experiment independently of the machine that may eventually execute it.

## Required fields

- schema_version: currently 1
- experiment_id: stable, filename-safe identifier
- status: QUEUED, RUNNING, COMPLETED, or FAILED
- Hypothesis and strategy version
- Symbol, timeframe, and data date range
- Parameters frozen before execution
- Execution mode and timestamps
- Result record and artifact list

## Evidence expected for a real MT5 test

A future MT5 executor must record the Git commit, EA source/binary hash, terminal/build version, symbol, timeframe, exact data interval, modeling mode, deposit/currency/leverage, spread/commission/slippage assumptions, parameter set, and the tester report/log hashes. It must also identify development, validation, and untouched final out-of-sample intervals.

## Current limitation

The manifest helper validates strict calendar dates, timezone-aware timestamps, state/timestamp consistency, finite JSON values, and safe relative artifact paths. The mock worker implements only lifecycle smoke testing. They do not run or emulate market trades. The mock worker's output must never be interpreted as evidence of strategy performance.
