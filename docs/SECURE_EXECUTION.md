# Secure execution boundary (pre-VPS)

## Current status

This repository does not currently have a deployed VPS worker or a ChatGPT-to-VPS connection. The mock worker only changes a local JSON manifest through a deterministic lifecycle; it does not start MT5, access a broker, or place orders.

## Required design before any real worker

- Keep the public GitHub repository separate from privileged execution infrastructure.
- Never attach a persistent self-hosted runner with secrets or broker access to this public repository.
- Do not accept arbitrary shell, PowerShell, Python, MQL5, or executable commands from issues, pull requests, workflow inputs, or public job files.
- Treat a submitted experiment as declarative data: allow-listed strategy/build identifiers, symbol, timeframe, bounded date range, frozen parameters, data revision, and cost assumptions.
- Validate schemas, limits, paths, and artifact size before scheduling.
- Use an authenticated private control plane, short-lived credentials, least privilege, outbound-only communication where practical, and explicit operator approval for privileged actions.
- Separate research/test accounts from live accounts. Live trading must remain disabled unless separately authorized.
- Store credentials in a secret manager, never in Git, logs, artifacts, manifests, or prompts.
- Use immutable experiment IDs and record repository commit, EA binary hash, data hash, terminal/build version, configuration, logs, and result artifact hashes.
- Preserve failed, interrupted, and negative runs. A missing artifact or incomplete log must never be reported as a successful test.
- Make job retries idempotent; a completed or failed job must not silently run again under the same ID.
- Restrict network access and file-system paths; do not let the worker download and execute unreviewed code.
- Review the threat model and test it before enabling any remote execution.

## Planned lifecycle

QUEUED -> RUNNING -> COMPLETED or FAILED

Only the mock lifecycle is implemented in this phase. COMPLETED means only that the mock lifecycle completed unless the manifest explicitly records independently verifiable MT5 execution evidence. A mock result is not a backtest result.
