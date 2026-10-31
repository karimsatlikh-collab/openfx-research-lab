# Source Claim Registry v1 — local content-addressed integrity

**Status:** draft implementation contract. This registry is a local integrity mechanism, not an identity, rights, or truth authority.

## Purpose

Hypothesis cards must not treat caller-supplied dictionaries as registry-backed claims merely because their fields look plausible. When `build_hypothesis_card(..., claim_registry_root=...)` is used, each claim ID must resolve to a content-addressed record and the supplied claim must match that record exactly.

## Stored objects

The implementation stores four classes of objects beneath the caller-provided registry root:

- `claim-index/<claim_id>.json`: maps one claim ID to a claim-record SHA-256.
- `claim-records/<sha256>.json`: canonical JSON containing the claim, source-record digest, and source-content digest.
- `source-records/<sha256>.json`: canonical source metadata record.
- `source-content/<sha256>.bin`: exact source bytes.

Canonical JSON uses UTF-8, sorted keys, compact separators, no NaN/Infinity. Each object is re-hashed during resolution. The source metadata's content hash, the stored source bytes, and the claim's source ID/locator/hash must agree.

## API

1. Build and validate a source record with `build_source_record`.
2. Build an atomic claim with `build_atomic_claim`.
3. Register the claim and its source bytes with `register_claim_record(root, claim, source_record, source_content)`.
4. Resolve a claim with `resolve_claim_record(root, claim_id)`.
5. Require resolution during hypothesis-card creation by passing `claim_registry_root=root`.

If no registry root is passed, linked claim dictionaries remain metadata-only and unverified. If a registry root is passed, missing or mismatched records fail closed.

## Threat-model limits

This local registry provides content integrity and referential consistency against accidental changes and simple record tampering. It does **not** provide:

- authenticated authorship or trusted issuer identity;
- protection from a privileged or same-user actor who can replace registry files or directories;
- protection against symlinked ancestor directories or local filesystem TOCTOU races (the current checks are final-component checks, not a hardened directory-descriptor traversal);
- atomic multi-host registration or replay protection;
- independent authentication of source identity or exact locator;
- copyright/licensing/legal permission verification;
- semantic verification that a claim is true.

Therefore `provenance_verified` deliberately remains `false`, even after successful local registry resolution. The status `content_addressed_local_registry_integrity_only_not_authenticated` must not be shortened to “verified provenance”.

A future trusted service must add externally administered signing keys, role policy, signed registry events, immutable audit storage, revocation, and independent review before source claims can be described as authenticated provenance.
