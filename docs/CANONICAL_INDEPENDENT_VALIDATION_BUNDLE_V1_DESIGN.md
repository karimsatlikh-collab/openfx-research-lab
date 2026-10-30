# Canonical Independent Validation Bundle v1 — Integration Design

**Status:** design proposal only; not an executable contract or security certification.  
**Depends on:** canonical JobSpec v1 (M1/PR #23), canonical RunRecord v1 (PR #31), independent verifier prototype (PR #29), and the RunRecord-signature correction (PR #45).  
**Purpose:** resolve Issue #46 without redefining either canonical v1 contract or silently accepting the compact PR #29 envelopes as canonical.

## 1. Decision

The independent validator must consume the canonical M1 JobSpec v1 and canonical RunRecord v1 unchanged. The compact `independent-job-v1` and `independent-run-v1` objects from PR #29 are legacy prototype envelopes; they must not be renamed or represented as the canonical contracts.

Introduce a separately versioned **IndependentValidationBundle v1**. It is a transport/verification envelope around canonical documents and external artifact locations. It does not replace JobSpec or RunRecord.

The bundle contains:
1. the exact canonical JobSpec v1 document;
2. the exact canonical RunRecord v1 document;
3. an immutable authorization record (separate from JobSpec);
4. a separately versioned artifact-location manifest;
5. the executor attestation;
6. a trust-store reference (the trust store itself remains externally administered).

No worker, strategy, executor, or backtest implementation code may be imported by the independent validation boundary. Static canonical schemas and generic cryptographic/file-verification utilities are allowed.

## 2. Canonical input binding — all six RunRecord digests

Let `J` be the canonical JobSpec object and `R` the canonical RunRecord object. Hashes are SHA-256 over the repository's explicitly frozen canonical JSON byte representation (UTF-8, sorted keys, compact separators, no NaN/Infinity). Hash strings must be normalized to lowercase before comparison.

The six required `R.inputs` values are resolved as follows:

| RunRecord input | Required exact value |
|---|---|
| `job_spec_sha256` | SHA-256 of canonical bytes of the complete JobSpec `J` |
| `strategy_spec_sha256` | `J.strategy_spec_ref.sha256` |
| `implementation_sha256` | `J.implementation.build_sha256` |
| `data_profile_sha256` | `J.data_profile_ref.sha256` |
| `cost_profile_sha256` | `J.cost_profile_ref.sha256` |
| `gate_config_sha256` | `J.gate_config_ref.sha256` |

The validator must fail closed unless all six values match exactly. It must also require `R.job_id == J.job_id`, a valid canonical schema for each document, and a terminal RunRecord state appropriate to the bundle's declared verification operation. A completed-artifact verification path must require `R.status == COMPLETED` and a non-null completion timestamp; other terminal states are failure evidence, not successful run evidence.

The referenced StrategySpec, DataProfile, CostProfile, and GateConfig documents should be supplied as immutable content-addressed documents or independently retrievable from an approved immutable store. Their canonical hashes must be checked against the corresponding JobSpec references before their semantic fields are trusted. Merely accepting the four digest strings in JobSpec does not prove the referenced documents exist.

## 3. Artifact-location manifest — separate from RunRecord

Canonical RunRecord v1 output items are `{name, sha256, optional media_type}`. They deliberately do not carry filesystem paths or file sizes. Do not add those fields to RunRecord v1.

Define a distinct `ArtifactLocationManifest v1` with:
- `schema_version: 1`;
- `job_id` and `run_id`;
- an array of entries, each containing `name`, safe relative POSIX `path`, non-negative integer `size_bytes`, and lowercase `sha256`;
- no unknown fields.

Validation requirements:
- names are unique; paths are unique;
- paths are relative, contain no empty, dot, parent, backslash, drive, or absolute components, and resolve beneath a read-only artifact root;
- the manifest entry-name set is exactly equal to the RunRecord output-name set (not merely a subset);
- for every name, the manifest SHA-256 exactly equals the RunRecord output SHA-256;
- every file is a regular non-symlink file; its measured size and streamed SHA-256 equal the manifest values;
- reject missing, extra, duplicate, aliased, or unreferenced output entries;
- defend against path traversal and time-of-check/time-of-use races; a read-only, immutable snapshot or file-descriptor-based verification is required.

The manifest is independently canonicalized and hashed. The signed attestation must bind its digest, so a party cannot substitute paths or sizes after signing even when the logical RunRecord outputs remain unchanged.

## 4. Authorization and replay protection

Canonical JobSpec v1 has no nonce/authorization field. Do not inject PR #29's `authorization.nonce` into JobSpec or silently extend its v1 schema.

Use a distinct, immutable AuthorizationRecord v1 containing at least:
- authorization ID and nonce (cryptographically random, one-use, minimum 128 bits);
- JobSpec digest and job ID;
- authorized engine and implementation digest;
- issuer identity/role and UTC issue/expiry timestamps;
- explicit permitted action/evidence level and any execution budget/limits required by policy.

The executor attestation binds the AuthorizationRecord digest. A trusted registrar must atomically consume the nonce and record the accepted bundle ID before a bundle is accepted. Duplicate/replayed nonces fail closed. A stateless verifier alone cannot guarantee one-time use; replay protection is an operational registrar responsibility and must be explicit in the API boundary.

The trust-store reference must identify the trust-store version/digest used for verification. Trust-store administration, key custody, revocation, and issuer authorization remain external controls and require a separate documented owner and audit trail.

## 5. Attestation v2 — signed claim set

Do not silently change the meaning of the existing PR #29/45 attestation schema v1. Define a new domain-separated attestation version (for example, `OPENFX_INDEPENDENT_BUNDLE_ATTESTATION_V2\n`) and schema.

At minimum, the signed claims bind:
- bundle schema/version and unique bundle ID;
- JobSpec SHA-256;
- RunRecord SHA-256;
- AuthorizationRecord SHA-256;
- ArtifactLocationManifest SHA-256;
- job ID, run ID, engine, implementation SHA-256, evidence level;
- executor identity, key ID, nonce/authorization ID;
- issued-at and expiry timestamps;
- trust-store identity/version or immutable trust-store digest.

The verifier recomputes every digest from the supplied canonical bytes before signature verification and then verifies the signature against the externally trusted key and policy. A valid signature proves only that the trusted key signed these exact claims; it does not prove the strategy is correct, the source data is licensed, the engine is honest, or the results are profitable.

## 6. Independent validation sequence

1. Enforce size/depth/field-count limits before parsing untrusted JSON.
2. Parse with duplicate-key rejection; reject non-finite JSON numbers and non-canonical digest encodings.
3. Validate the canonical JobSpec v1 and RunRecord v1 schemas using pinned schema versions; do not import their producer modules.
4. Recompute JobSpec and RunRecord canonical digests.
5. Resolve and hash the four immutable referenced documents; verify all six RunRecord input bindings.
6. Validate AuthorizationRecord schema, scope, expiry, JobSpec binding, engine and implementation binding.
7. Validate ArtifactLocationManifest schema and exact one-to-one correspondence with RunRecord outputs.
8. Recompute manifest digest; verify attestation v2 claims and Ed25519 signature against the externally managed trust store.
9. Verify artifact paths, file types, sizes and hashes from a read-only immutable snapshot.
10. Atomically consume the nonce through the trusted registrar; reject replay. Persist a bounded decision record with reason codes and all input digests.
11. Return a bounded PASS/FAIL report. Never emit strategy metrics or infer statistical approval from artifact integrity.

Order may be adjusted only if the security review demonstrates equivalent fail-closed behavior. In particular, no artifact path is opened before path and manifest validation.

## 7. Required adversarial tests

Minimum test groups before implementation can be considered reviewable:

- **Contract mismatch:** compact PR #29 envelopes supplied where canonical JobSpec/RunRecord are required; missing/extra fields; wrong schema versions.
- **Six-way binding:** mutate each of the six RunRecord input hashes independently; mutate each JobSpec immutable reference; substitute an implementation digest; all must fail.
- **Referenced documents:** absent document, wrong content hash, wrong schema, mismatched ID/version, duplicate reference identity.
- **Canonicalization:** duplicate JSON keys, NaN/Infinity, alternate digest case, Unicode/serialization edge cases, reordered object keys, malformed UTF-8.
- **Artifact bijection:** missing/extra/duplicate names, duplicate paths, mismatched digest, mismatched size, path traversal, absolute path, symlink at each path component, hard-link/alias policy, non-regular file, file mutation during verification.
- **Signature binding:** independently mutate each signed digest and identity field; old v1 signatures must not validate as v2.
- **Authorization/replay:** wrong job, wrong engine, wrong implementation, expired/future authorization, reused nonce, concurrent duplicate submission, revoked/expired key, unknown trust-store version.
- **Lifecycle:** incomplete RunRecord, terminal failure/cancellation, missing timestamps, inconsistent evidence level.
- **Isolation:** prove validator package import graph excludes worker/strategy/executor modules; test read-only artifact mount and separate OS identity in the deployment design.

## 8. Compatibility and migration

- Preserve PR #23 JobSpec v1 and PR #31 RunRecord v1 as canonical contracts.
- Preserve PR #45's RunRecord digest correction as a useful security fix, but do not treat it as sufficient for the new bundle: the new attestation must also bind the artifact manifest and authorization record.
- Introduce new bundle, manifest, authorization and attestation schemas with explicit names/versions.
- Keep compact PR #29 fixtures only as legacy tests until canonical integration tests replace them; label them clearly as legacy envelope fixtures.
- Do not merge the integration until the dependent canonical contract PRs are reconciled and CI passes on the exact combined head.

## 9. Explicit non-goals and blockers

This design does not establish:
- OS/process isolation merely by using a separate Python process;
- secure key custody, trusted human identity, or trust-store governance;
- nonce replay protection without a trusted atomic registrar;
- data rights, source authenticity, or data quality;
- correctness of the worker/engine, absence of look-ahead, statistical validity, selection-bias control, or profitability;
- MT5, VPS, broker, or live-trading authorization.

**Release status remains blocked** until implementation, independent security review, adversarial CI, external key/registrar design, and end-to-end integration are complete.
