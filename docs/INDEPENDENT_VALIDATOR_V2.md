# OpenFX Independent Validator v2

Status: **hardened prototype; not yet an operationally independent trust boundary**.

This v2 is a separate schema and module from the original PR #29 v1 prototype. Do not use v1 as a trusted execution attestation validator. V2 closes the RunRecord binding gap and uses directory-descriptor-relative no-follow artifact opening.

## Security changes in v2

1. **Complete RunRecord signature binding**
   - The executor attestation must include run_record_sha256.
   - The digest is SHA-256 over the complete canonical RunRecord v2, including status, timestamps, input bindings, output paths, sizes, and artifact hashes.
   - The Ed25519 signature covers run_record_sha256.
   - Any post-signing RunRecord mutation fails with ATTESTATION_RUN_RECORD_MISMATCH.

2. **Frozen expected output set**
   - JobSpec v2 contains a bounded expected_outputs list.
   - RunRecord outputs must match that exact set; omitted or substituted outputs fail.
   - JobSpec digest and RunRecord digest are both signed/bound.

3. **Race-resistant artifact opening**
   - The artifact root is opened as a directory descriptor.
   - Every intermediate component is traversed relative to the pinned descriptor using O_DIRECTORY and O_NOFOLLOW.
   - The final file is opened relative to its parent descriptor using O_NOFOLLOW.
   - The validator fails closed if the platform lacks dir_fd/openat, O_NOFOLLOW, or O_DIRECTORY support.
   - File identity, device, inode, size, mtime, and ctime are compared before and after reading.

4. **Resource bounds**
   - Job/Run/attestation/trust-store JSON inputs: 16 MiB maximum each.
   - Output artifacts: 512 MiB maximum each.
   - Output count and trust-store key count: 1,000 maximum.
   - Relative artifact paths: 1,024 characters and 32 components maximum.

5. **No caller-supplied CLI clock**
   - The production CLI always uses the system clock.
   - Neither the CLI nor the in-process validation API accepts a caller-supplied clock.
   - The CLI no longer accepts --now-utc.

6. **Validator provenance**
   - Successful reports include validator version and SHA-256 of the validator source file.

## Versioned schemas

- JobSpec: `schemas/independent-job-v2.schema.json`
- RunRecord: `schemas/independent-run-v2.schema.json`
- Attestation: `schemas/executor-attestation-v2.schema.json`
- Trust store: reuses `schemas/executor-trust-store-v1.schema.json`

The v2 attestation uses a new domain separator: `OPENFX_EXECUTOR_ATTESTATION_V2\n`. V1 signatures are not accepted by the v2 validator.

## Invocation

Install dependencies with `python -m pip install -r requirements-dev.txt`, then run:

```bash
python -m openfx.independent_validator_v2 \
  --job /secure/input/job-v2.json \
  --run /secure/input/run-v2.json \
  --attestation /secure/input/attestation-v2.json \
  --trust-store /separately-administered/trusted-executors.json \
  --artifact-root /secure/read-only/artifacts
```

Exit code 0 means the complete signed job/run binding and declared artifact bytes passed these checks. Exit code 2 means validation failed.

## Remaining trust-boundary requirements

- The repository does not generate or store executor private keys. Keep private keys in a protected executor signing environment, preferably hardware-backed or OS-keystore-backed.
- A human administrator must provision, rotate, and revoke public keys in a trust store outside worker write authority.
- The validator must run under a separate OS identity or isolated host/container with read-only access to job, run, artifacts, and trust store. Same-user/same-host process separation is not strong isolation.
- The authoritative registrar must enforce one-time nonce consumption, replay protection, idempotency, and immutable ingestion of the signed RunRecord.
- V2 proves that a trusted key signed a specific JobSpec and complete RunRecord and that declared output bytes match. It does not prove the executor binary is uncompromised, the engine is scientifically correct, or a strategy is profitable.
- The v2 safe artifact opener requires POSIX-style directory-relative open primitives and fails closed on unsupported platforms. A Windows-native handle implementation would require a separately reviewed adapter.

## Release gate

Do not use v2 to mark real execution as independently validated until:
1. Separate validator identity/host and read-only artifact mount are demonstrated.
2. Trust-store provisioning, rotation, revocation, and private-key custody are reviewed by a human.
3. The registrar enforces nonce consumption/replay/idempotency and immutable run ingestion.
4. The v2 adversarial CI suite passes, including post-signing RunRecord mutation and intermediate symlink tests.
5. The validator source revision and source hash are recorded and independently verified.
6. An independent security reviewer reviews the implementation and deployment boundary.

No VPS, MT5 execution, broker credentials, paid service, or live trading is authorized by this prototype.
