# Zero-cost Windows local checks — pre-VPS

**Status:** runbook only. No Windows execution or MT5 Strategy Tester run is claimed by this document.

## Purpose

Verify only the existing Python scaffold and worker prototype on an owner-controlled Windows computer before considering any VPS expense. These checks do not validate a trading strategy and do not execute MT5.

## Preconditions

- Windows 10/11 computer controlled by the project owner.
- Python 3.11 or newer available in PowerShell.
- A clean clone of the OpenFX repository.
- No broker credentials, API keys, live account, or privileged runner.
- Do not run scripts downloaded from an unreviewed branch. Use the exact reviewed commit/branch and record its SHA.

## Procedure

Open PowerShell in the cloned repository:

```powershell
git status --short
git rev-parse HEAD
python --version
python -m compileall -q .
python -m unittest discover -s tests -v
```

If the worker directory has its own self-test entrypoint, inspect its CLI help/source first, then run only the documented non-network self-test from `worker/README.md`:

```powershell
python .\worker\openfx_worker.py --self-test
```

Do not run a worker service, configure a real control-plane URL, add a bearer token, connect a broker, or install MT5 as part of this smoke test.

## Evidence to record

- Date/time and Windows edition/build.
- Python version and architecture.
- Git commit SHA and clean/dirty status.
- Exact commands, exit codes, stdout/stderr.
- Test count and pass/fail/skip totals.
- Whether the worker self-test made any network request (expected: none).
- Any exception, timeout, file-permission, or path issue.
- If the session is accessed through RDP, whether disconnecting/reconnecting affects only the interactive session or terminates the process. Do not claim this test unless actually performed.

## Pass criteria

- Syntax compilation exits 0.
- Unit tests exit 0.
- Worker self-test exits 0 without network access or secret configuration.
- Logs and outputs are preserved with the tested commit SHA.
- No MT5 terminal, broker, or live-trading functionality is invoked.

A pass establishes only local Python/test compatibility. It does not establish Windows service reliability, MT5 adapter correctness, backtest validity, or strategy profitability.

## Blockers

The current worker documentation states that the MT5 adapter and private control plane are not implemented. Therefore no Strategy Tester or MT5 demo test is currently authorized by this runbook. VPS purchase remains deferred.
