# AuthorizationRecord v1 — security contract

Status: **proposed contract; not an implemented authorization system**.

This contract defines the minimum signed authorization envelope required before a worker may accept a JobSpec. It is deliberately separate from JobSpec: a job describes requested work; an AuthorizationRecord proves that a trusted authority authorized one exact job for one exact worker audience and action.

## Trust rule

A field such as `approved: true`, a valid JobSpec, a bearer token used to poll, or a matching SHA-256 digest is **not** execution authorization. The worker must reject a job unless it receives a structurally valid AuthorizationRecord and a trusted verifier accepts its signature and policy.

## Envelope

The normative structural schema is `schemas/authorization-record-v1.schema.json`.

The signed `payload` binds:
- `authorization_id`: globally unique authorization identifier;
- `issuer_id` and `key_id`: identity of the trusted authorization issuer and its signing key;
- `audience`: exactly `openfx-worker`;
- `job_id` and `job_sha256`: the exact JobSpec identity and digest;
- `action`: exactly `execute_job`;
- `requested_engine`: the engine authorized for this job;
- `issued_at_utc` and `expires_at_utc`: bounded validity interval;
- `nonce`: 256-bit random value encoded as unpadded base64url.

The signature uses Ed25519. The signature is over the UTF-8 bytes of the RFC 8785 JSON Canonicalization Scheme representation of the complete `payload` object, not the outer envelope. The signature value is the unpadded base64url encoding of the 64-byte Ed25519 signature. The public key is never supplied by the AuthorizationRecord itself.

## Mandatory verifier policy

A production verifier must fail closed unless all checks pass:

1. Validate this schema and parse timestamps as timezone-aware UTC instants.
2. Resolve `issuer_id + key_id` only from an out-of-band trusted key registry. Reject unknown, disabled, expired, or revoked keys. Never trust a public key embedded in the job or authorization.
3. Require an explicitly configured issuer-to-role policy granting permission for the requested action and engine. The proposer/implementer cannot authorize their own job.
4. Verify Ed25519 over the canonical payload bytes.
5. Require `audience == openfx-worker`, exact job ID, exact canonical JobSpec SHA-256, exact engine, and action match.
6. Enforce `issued_at_utc <= now + 30 seconds`, `expires_at_utc > now - 30 seconds`, and a maximum authorization lifetime of five minutes. Reject inverted or overlong intervals.
7. Atomically consume `nonce` and `authorization_id` in a trusted central registrar, scoped to issuer and audience. Consumption must be durable and shared across all workers/hosts. A local JSON file or worker cache is not sufficient. A failed or interrupted attempt must not make the authorization replayable.
8. Record the authorization ID, issuer/key IDs, payload digest, job digest, nonce digest (not the raw nonce), decision, and timestamp in an append-only audit event. Do not log private keys or bearer tokens.

The registrar must reject reuse of either the nonce or authorization ID, even if the same authorization is presented to another worker. Retries must use an explicit server-side retry policy; they must not silently bypass nonce consumption.

## Key lifecycle and operations

- Private signing keys remain outside the public repository and outside worker machines.
- Prefer a managed KMS/HSM or equivalent protected signing service; never place private keys in Git, prompts, worker configuration, or logs.
- Publish/rotate public keys through a separately authenticated administrative process. Maintain key status, validity windows, issuer roles, and revocation history.
- Define clock synchronization and alert on clock drift. The 30-second tolerance is not permission to extend the five-minute lifetime.
- The authorization service must issue a record only after an authenticated human or separately approved policy decision. The approval event itself must be auditable.
- Do not permit live-trading authorization in v1. `mt5-demo` is the highest permitted engine class in this contract.

## Explicit non-claims and implementation gates

This schema and document do **not** implement cryptographic verification, trusted-key provisioning, role separation, a central nonce registrar, durable replay protection, worker integration, or secure key operations. JSON Schema validation checks structure only.

Before any worker can poll or accept executable work, a separate implementation PR must provide:
- a tested Ed25519 verifier using a maintained cryptographic library;
- trusted issuer/key configuration and revocation handling;
- RFC 8785 canonicalization test vectors;
- expiry, audience, job/engine binding, and malformed-signature negative tests;
- transactional, cross-host nonce and authorization-ID consumption;
- mandatory integration at the worker's acceptance boundary (no fallback to `approved: true`);
- audit events and adversarial replay/concurrency tests;
- independent security review.

Until then, the existing worker remains validation-only. No MT5 execution, VPS deployment, broker connectivity, or live trading is authorized.
