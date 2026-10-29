# Feasibility Roadmap: AI Forex Research Company

Status: planning document; no claim that a 24/7 host or MetaTrader test runner is operational yet.

## Mission
Build a small, auditable research operation that discovers strategy evidence, extracts rules with source traceability, implements reproducible tests, and evaluates strategies with costs and out-of-sample validation. The objective is not to promise profitability; it is to establish a repeatable process that can reject weak ideas and validate strong ones.

## Governance and roles
- President / final decision-maker: the user. Approves mission, budget, risk policy, and any live-trading decision.
- Research and execution lead: ChatGPT-assisted workflow. Coordinates work, prepares research plans, writes/updates code and reports, and clearly labels unverified claims.
- Watchdog / independent reviewer: checks evidence, source provenance, look-ahead bias, data leakage, overfitting, reproducibility, and whether claims match test logs. The watchdog must be logically separate from the strategy proposer.
- Data collection team: finds permitted sources, records URLs/licensing/access constraints, extracts transcripts and market data, and measures extraction errors.
- Strategy engineering and test team: translates explicit rules into code, runs historical and walk-forward/out-of-sample tests, includes spread/commission/slippage, and archives configs/results.

## Infrastructure decision
Do not use GitHub Codespaces or ordinary GitHub-hosted Actions as a permanent 24/7 server:
- Codespaces are development environments; they time out on inactivity and have a maximum 12-hour lifetime.
- GitHub-hosted Actions jobs have a 6-hour execution limit and are workflow jobs, not persistent servers.
- Keep GitHub as source control, issue tracking, CI, and report metadata.
- Use a separate Linux VPS for durable scheduled collection and research orchestration.
- Treat MetaTrader 5 as a separate execution/test component. MT5 can run on Linux through Wine according to MetaQuotes documentation, but compatibility and unattended operation must be tested on the chosen VPS before relying on it.
- Keep large raw videos/tick data out of Git history. Store compact manifests, hashes, metadata, test configs, and small reports in Git; use a separate data volume/object store for large files. Use SQLite for the first prototype unless concurrent access requires PostgreSQL.

## Staged feasibility gates
1. Repository audit: inventory current files, workflow results, secrets exposure, dependencies, and test coverage.
2. Free-cloud feasibility: test a short-lived Linux/Python worker, disk persistence, restart behavior, scheduled tasks, outbound network access, and usage limits. No 24/7 claim until measured.
3. Persistent-host comparison: compare a low-cost VPS, MT5's own virtual hosting, and other permitted options by cost, region/network access, disk persistence, restart recovery, and unattended operation. Oracle free capacity is not assumed available.
4. Orchestrator prototype: one scheduled task, a durable job queue or SQLite ledger, structured logs, retry rules, and a health report.
5. MT5 integration gate: prove terminal installation, broker/demo connection, Strategy Tester availability, EA launch, report export, and recovery after reboot. Linux/Wine is a candidate, not yet validated.
6. Research pipeline: source registry -> transcript/data extraction -> structured rule cards -> independent review -> strategy implementation -> cost-aware test -> out-of-sample evaluation.
7. Company formation feasibility: first identify jurisdiction, residency/work authorization, planned activity (research/software vs. financial advice/asset management), expected revenue, liability, tax/accounting cost, and whether any financial-regulatory permission is triggered. Do not incorporate or pay fees before this analysis.
8. Pilot decision: proceed only if the prototype is reproducible, costs are understood, and the watchdog can independently reproduce results.

## Minimum evidence required before declaring 24/7 readiness
- A continuous soak test of at least 72 hours on the selected host.
- Successful automatic restart after a simulated process failure and host reboot.
- No lost job records or corrupted outputs.
- Disk usage and cost monitoring with a hard budget/stop rule.
- Alerts for missed schedules, failed jobs, disk exhaustion, and MT5 disconnection.
- At least one reproducible demo Strategy Tester run with exported report and configuration.

## Current repository assessment (2026-10-29)
The repository currently demonstrates a small Python skeleton and CI checks, not a deployed autonomous research team. Existing successful Actions runs are evidence that limited checks ran, not evidence of 24/7 hosting, data extraction, or MetaTrader testing. The root-level `auto_report.yml` is not in GitHub's standard `.github/workflows/` location and therefore should be moved/merged only after a careful workflow audit.

## Immediate next actions
1. Verify exact Codespaces and Actions quotas for the linked account in GitHub billing/settings.
2. Add a small Linux worker smoke test and persist its report as an artifact.
3. Compare VPS options and determine the jurisdiction for company formation before any account creation or payment.
4. Build a no-trading-risk MT5 demo/Strategy Tester proof of concept.
