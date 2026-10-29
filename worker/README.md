# OpenFX Windows VPS Worker — prototype

**Status: design/prototype only. Not deployed and not connected to MT5.**

This worker is intended to run on a private Windows VPS after the owner purchases and secures it. It is deliberately deny-by-default.

## Security model
- Polls a configured HTTPS control-plane endpoint; it does not open an inbound listener.
- Reads the bearer token from the `OPENFX_WORKER_TOKEN` environment variable, never from source code.
- Accepts only a narrow JSON job schema and an explicit allow-list of EA identifiers.
- Rejects arbitrary commands, URLs, file paths, executables, and unknown fields.
- Keeps a local JSON audit ledger, deduplicates job IDs, and rejects reused idempotency keys.
- Requires the configured control-plane hostname to match an explicit exact-host allow-list; redirects and placeholder destinations are refused.
- Does not log authorization headers or secrets.
- Contains no live-trading functionality.
- The MT5 adapter is intentionally not implemented; a job is not run until that adapter and a private control plane have been built and independently tested.

## Current limitations
The prototype validates and records jobs only. It cannot run Strategy Tester, download EAs, report back to a server, or claim a backtest has happened. Do not deploy it as a Windows service yet.

## Local validation
Requires Python 3.11+.

```powershell
python openfx_worker.py --self-test
```

The self-test validates example manifests without connecting to any service. The state file is not protected by a cross-process lock, so run only one worker process against a given state file.

## Future configuration
Copy `worker_config.example.json` to a private local configuration file only after reviewing the deployment threat model. Never commit credentials or real server URLs/tokens. The eventual control plane must authenticate workers, validate approvals server-side, rate-limit requests, and return only signed/approved declarative jobs.

## Planned implementation sequence
1. Add schema validation and local audit trail (this prototype).
2. Add unit tests and static checks.
3. Implement a private HTTPS control plane with worker enrollment and job approval.
4. Implement a narrow MT5 Strategy Tester adapter on a disposable/demo-only environment.
5. Verify report completeness, hashes, timeout behavior, duplicate handling, and failure recovery.
6. Run a no-trading smoke test before any unattended testing.
