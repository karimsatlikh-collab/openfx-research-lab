# RunRecord v1 lifecycle contract

The legacy `openfx.experiment` manifest and its four-state lifecycle remain
unchanged for backward compatibility. New orchestration code can use
`openfx.run_record` and `schemas/run-record-v1.schema.json`.

## Lifecycle

```text
QUEUED -> VALIDATED -> APPROVED -> RUNNING -> VERIFYING -> COMPLETED
   |          |           |          |           |
   +-> REJECTED           +-> CANCELLED          +-> FAILED
   +-> CANCELLED                     +-> TIMEOUT
                                     +-> INTERRUPTED
```

Allowed transitions are enforced in code. `FAILED`, `TIMEOUT`,
`INTERRUPTED`, and `REJECTED` require a non-empty error. All terminal
states receive `finished_at_utc`; execution states beginning at `RUNNING`
require `started_at_utc`.

## Evidence semantics and limitations

- `evidence_level` is mandatory and restricted to `mock`, `synthetic`,
  or `mt5-demo`.
- The level is preserved unchanged by the transition function. The hashes
  binding the run's inputs are likewise preserved.
- This field is a declaration, not provenance. The factory does not prove
  that a run actually used MT5, synthetic data, or a mock worker. In
  particular, `mt5-demo` must not be treated as trusted evidence until a
  separately authenticated adapter and attestation path exist.
- `APPROVED` is a lifecycle state, not proof of human identity or authority.
  Role enforcement and approval signatures are not implemented here.
- `COMPLETED` means the run reached the end of its `VERIFYING` stage. It
  does not mean an independent validator passed, statistical gates passed,
  or a strategy is profitable.
- The Python validator is dependency-free and checks the explicitly
  implemented RunRecord v1 constraints. It is not a general JSON Schema
  engine and does not implement every JSON Schema keyword or format rule.
- The transition function returns an in-memory copy. It is not an atomic,
  concurrency-safe persistence mechanism and does not prevent two writers
  from racing.
- No MT5 adapter, Strategy Tester execution, broker connection, VPS worker,
  or live trading is introduced by this change.

## Compatibility

The existing `openfx.experiment`, `openfx.mock_worker`, and
`create_experiment.py` interfaces are intentionally untouched. The old
four-state manifest remains a legacy format and is not silently migrated.
