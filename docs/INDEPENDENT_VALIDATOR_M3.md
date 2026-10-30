# M3 Standalone Independent Validator

Status: **implemented as a prototype; not yet an operationally independent trust boundary**.

## What exists

`openfx/independent_validator.py` is a read-only command-line process. It imports no worker, executor, or strategy implementation. It independently:

1. Canonicalizes the frozen JobSpec and recomputes its SHA-256.
2. Recomputes the canonical RunRecord SHA-256, including its complete output manifest, and binds that digest together with job ID, engine/evidence label, job digest, implementation digest, and completion timestamp.
3. Verifies an Ed25519 signature over domain-separated canonical attestation claims.
4. Loads the executor public key from a separately supplied trust-store file, not from the attestation.
5. Checks key ID, executor identity, permitted engine, revocation, key validity window, attestation issue/expiry, and a maximum 15-minute attestation lifetime.
6. Binds the signed attestation to job ID, run ID, canonical JobSpec digest, full RunRecord digest (including artifact paths, sizes, and hashes), implementation digest, and the frozen authorization nonce.
7. Independently opens each declared output artifact, rejects symlinks/path traversal/non-regular files, and recomputes size and SHA-256.
8. Emits a bounded report containing pass/fail reason codes and digests; it does not emit strategy metrics or execute submitted code.

The trust-store and attestation formats are described by:
- `schemas/executor-trust-store-v1.schema.json`
- `schemas/executor-attestation-v1.schema.json`

## Invocation

```bash
python -m pip install -r requirements-dev.txt
python -m openfx.independent_validator \
  --job /secure/input/job.json \
  --run /secure/input/run.json \
  --attestation /secure/input/attestation.json \
  --trust-store /separately-administered/trusted-executors.json \
  --artifact-root /secure/read-only/artifacts
```

Exit code `0` means the signed claims and declared artifact bytes passed these checks. Exit code `2` means validation failed. The optional `--now-utc` exists only for deterministic tests and must not be used to override production time.

## Trust and separation requirements not solved by this code

- The repository does not generate or store executor private keys. Private keys must remain in a protected executor signing environment (preferably hardware-backed or OS-keystore-backed).
- A human administrator must provision, rotate, and revoke public keys in the trust store outside the worker's write authority.
- The validator must run under a separate OS identity or isolated host/container with read-only access to job/run/artifacts and trust store. Running it as the same user on the same machine is process separation only, not strong isolation.
- The authoritative registrar must enforce one-time nonce consumption and idempotency for the same run. This CLI binds the nonce to a frozen job but is intentionally read-only and does not maintain a mutable replay database.
- A signed executor attestation proves that a trusted key signed the bound claims and exact RunRecord/output manifest. It does not prove the executor binary is uncompromised, the requested engine is scientifically correct, or a strategy is profitable.
- Current tests generate ephemeral test keys in memory. They are not production key provisioning or an independent human review.

## Release gate

Do not mark independent validation PASS for real runs until:
1. A separate validator identity/host and read-only artifact mount are demonstrated.
2. Trusted-key provisioning, rotation, revocation, and private-key custody are reviewed by a human.
3. The registrar enforces nonce consumption, replay/idempotency, and immutable run ingestion.
4. Adversarial CI tests and independent code review pass.
5. The validator's own binary/source revision is recorded in every validation report.

No VPS, paid service, MT5 execution, broker credentials, or live trading is authorized by this prototype.
