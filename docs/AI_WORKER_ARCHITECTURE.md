# OpenFX AI orchestration and MT5 worker architecture

## Purpose

Provide a secure, auditable path from a research request to reproducible MT5 Strategy Tester evidence. This is a design specification, not a claim that the services are deployed.

## Recommended separation

1. **Public research repository** — source code intended for public viewing, docs, tests, source citations, and reproducible non-secret artifacts. It has a rights-reserved notice; public visibility is not permission to reuse original materials.
2. **Private control repository or private service** — approved experiment specifications, deployment configuration, and workflow definitions. Never place broker credentials or API keys in source control.
3. **Orchestrator** — a small service using the OpenAI API for model reasoning and tool calling. ChatGPT Plus is not itself a persistent VPS process; API use has separate setup, credentials, and billing.
4. **Private Windows VPS** — MT5 terminal and Strategy Tester, plus a narrowly scoped OpenFX worker. The worker polls for approved declarative jobs over outbound HTTPS. Do not expose an arbitrary remote shell.
5. **Evidence store** — reports, logs, configuration snapshots, code hashes, data revision, and artifact hashes. Store sensitive material separately from public reports.

## Job contract

A job should specify only allow-listed fields:
- unique experiment ID and idempotency key;
- approved EA source/build identifier and SHA-256;
- symbol, timeframe, date interval, tester/modeling mode;
- initial deposit/currency and relevant account/test settings;
- spread, commission, swap, slippage assumptions where supported;
- frozen parameter set;
- development, validation, and untouched final out-of-sample intervals;
- artifact expectations and timeout/resource limits.

Reject arbitrary commands, arbitrary download URLs, path traversal, unknown EA identifiers, unbounded date ranges, and duplicate completed jobs.

## Execution lifecycle

QUEUED -> VALIDATED -> APPROVED -> RUNNING -> VERIFYING -> COMPLETED / FAILED

A completed job is not automatically a successful strategy. It means only that the run and its required evidence passed integrity checks. Performance acceptance is a separate research decision.

## Approvals

- Routine local tests and static checks may run automatically.
- Public-source ingestion may run with domain, rate, license, and output limits.
- New code or strategy changes require tests and review before execution.
- MT5 Strategy Tester jobs may run only for allow-listed EAs and bounded parameter/date budgets.
- Any action affecting live trading, broker orders, money, or account settings is excluded from the automated worker. No live trading credentials should be installed for the research phase.
- Changing security controls, secrets, billing limits, access permissions, or production infrastructure requires owner approval.

## Network and identity

- The Windows worker initiates outbound HTTPS polling; do not expose a general-purpose inbound command endpoint.
- Restrict RDP to a VPN or a known administrator IP, enforce MFA at the provider/identity layer where available, and use a dedicated non-administrator Windows account for routine execution.
- Keep the worker service identity separate from the human administrator.
- Use short-lived credentials or a managed secret store where available; rotate credentials and log administrative changes.
- Use a private GitHub control plane for any privileged automation. Never attach a persistent privileged self-hosted runner to this public repository. GitHub explicitly warns that public-repository pull requests can compromise self-hosted runners.
- Keep API credentials out of prompts, commits, terminal output, screenshots, reports, and public artifacts.

## AI model roles

The OpenAI-powered orchestrator can plan work, call explicitly defined tools, and summarize evidence. A separately authorized Claude integration may act as an independent reviewer or research assistant through its own connector permissions. The two products do not share permissions automatically; granting a connector to Claude does not grant ChatGPT access to it.

Recommended initial Claude scope: read-only access to approved repository/docs/issues, with optional branch/PR creation only after a separate review. Do not give either model VPS administrator access, broker secrets, unrestricted shell access, or permission to place live orders.

## Cost and usage controls

- Set API project budget/usage alerts and hard limits where available.
- Apply per-job timeouts, concurrency caps, optimization pass limits, and daily quotas.
- Cache source retrieval and unchanged artifacts; avoid repeated downloads and duplicate experiments.
- Record model, API usage, estimated cost, tester duration, and artifact size for every job.
- Stop on quota exhaustion, missing evidence, anomalous spend, or repeated worker failure.

## Deployment stages

### Stage 0 — repository only
Complete documentation, tests, schema validation, source provenance, and CI. No MT5 or secrets.

### Stage 1 — local/mock worker
Run synthetic jobs, verify state transitions, idempotency, hashes, and failure recovery.

### Stage 2 — private demo VPS
Owner provisions the Windows VPS and MT5 demo terminal. Install a reviewed worker, configure restricted accounts/networking, and run a non-trading connectivity smoke test.

### Stage 3 — demo Strategy Tester automation
Run one allow-listed EA and one fixed configuration. Confirm the terminal report, log, code hash, and job manifest agree. Repeat a fixed run to check reproducibility.

### Stage 4 — bounded research automation
Enable scheduled research/backtests, parameter sweeps with strict budgets, validation splits, and independent report checks.

Live trading is not part of these stages.
