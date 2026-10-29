# Project Checkpoint — MT5 Windows Backtesting — 2026-10-29

## User-confirmed priority
The highest-priority operational goal is continuous, unattended backtesting of trading strategies designed for the user, including broad parameter optimization across many combinations.

The user selected option **B**: in addition to ordinary backtests, run optimization over many parameter combinations. This means CPU capacity, usable processor cores, test throughput, queueing, result retention, and protection against overfitting must be considered in the architecture.

## Two items explicitly carried forward to the next checkpoint
1. **Compatibility review:** verify the practical compatibility and provider requirements for running the desktop MetaTrader 5 (MT5) terminal and Strategy Tester in a Windows VPS environment, including supported Windows Server versions, installation, data/history storage, unattended operation, and remote/local tester agents.
2. **Backtesting environment setup:** after the compatibility and procurement checks, prepare and install the MT5 backtesting environment on the selected Windows server, then run a controlled smoke test before claiming it works. No server has yet been purchased or provisioned, and no MT5 installation or backtest on a VPS has been performed.

## Planning budget (not a purchase approval)
A preliminary market-review range for a base Windows VPS is **approximately 2,000,000–3,500,000 Iranian toman per month**. This is a planning estimate only, not a verified final quote or authorization to buy. Before purchase, verify:
- Final monthly and renewal price, VAT/fees, Windows licensing inclusion, and setup charges.
- CPU allocation (dedicated vs shared/vCPU), sustained CPU performance, number of usable cores, RAM, SSD/NVMe capacity, traffic, and fair-use limits.
- Supported Windows Server version, RDP access, administrator access, restart/recovery console, and provider rules for continuous MT5 optimization workloads.
- Backup/snapshot pricing, uptime terms, and cancellation/refund terms.

Any cloud-compute usage, MQL5 Cloud Network spending, AI/API usage, extra storage, or other paid add-on requires separate explicit approval. Do not purchase or activate paid services without the user's approval.

## Architecture direction to evaluate
- Compare a single Windows VPS running MT5 plus a lightweight job queue/reporting manager against a split architecture (lightweight Linux coordinator + separate Windows backtest host).
- Do not assume that a Linux VPS running Wine is a suitable production Strategy Tester host without a separate compatibility test.
- MT5 Strategy Tester supports multithreaded optimization using local agents and can connect remote agents or the MQL5 Cloud Network; all extra-agent/cloud costs and practical speedups must be evaluated rather than assumed.
- Start with a bounded pilot and benchmark a representative EA/optimization workload before scaling hardware.

## Research and engineering safeguards
- Keep strategy/code version, symbol, timeframe, date range, data/modeling mode, spread, commission, slippage assumptions, parameter grid, and run status with every result.
- Separate development, validation, and out-of-sample periods; do not select a strategy solely by the best optimization result.
- Preserve failed and negative results; record failures and resume jobs safely after restarts.
- A continuously running scheduler or successful MT5 installation alone does not establish strategy profitability or validation.

## Current state and next action
- The Linux VPS around 600,000 toman/month was previously accepted only as a possible lightweight coordinator; it is not purchased or deployed.
- The Windows VPS range above is a preliminary planning estimate and needs fresh vendor comparison and exact quote verification.
- **Next action:** research supported Windows Server/MT5 compatibility and compare at least two current Windows VPS offers, then prepare an installation-and-smoke-test checklist. Do not purchase until the user explicitly approves a specific offer.
