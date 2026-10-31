# ADR: Authorization verifier dependencies

Status: accepted for a future implementation PR; dependencies are not installed. Date: 2026-10-31.

## Context
The repository has no runtime third-party dependencies. Its development requirements contain jsonschema only, and the project test workflow uses Python 3.12. AuthorizationRecord v1 requires Ed25519 and RFC 8785 JCS. Neither cryptography nor canonicalization should be implemented by hand.

## Decision
1. Use the maintained `cryptography` package for Ed25519. Review and pin an exact release in the implementation PR, including hashes for transitive dependencies. PyPI currently lists 50.0.2 as Production/Stable and supports Python >=3.9 except 3.9.0/3.9.1, including 3.12.
2. Evaluate Trail of Bits' `rfc8785` package (0.1.4) for JCS. It emits UTF-8 bytes and has no runtime dependencies, but PyPI marks it Beta and its latest release is old. Adoption is conditional on passing RFC 8785 Appendix B and upstream test vectors plus local tests for duplicate keys, NaN/Infinity, invalid Unicode, UTF-16 property ordering, and number formatting. Any failure blocks adoption; do not write a custom substitute.
3. This ADR adds no dependency. A separate implementation PR must add a dedicated runtime manifest, exact pins and hash-locked reproducible install; keep it separate from development dependencies and unrelated worker paths.
4. No verifier or worker integration is authorized by this documentation decision. Worker remains validation-only until signature verification, trusted-key policy, and a shared durable replay registrar are implemented and independently reviewed.

## Mandatory implementation tests
- RFC 8032 Ed25519 known-answer vectors and negative cases.
- RFC 8785 Appendix B and upstream JCS corpus, byte-for-byte.
- Reject duplicate JSON keys before canonicalization, non-finite numbers and invalid Unicode.
- Sign exactly the UTF-8 JCS bytes of the complete AuthorizationRecord payload.
- Test timestamp, issuer/key trust, revocation, role, audience, exact JobSpec digest, engine and action binding.
- Atomically consume nonce and authorization ID in a shared durable registrar; fail closed on outage or uncertainty.
- No worker wiring until adversarial replay/concurrency tests, audit behavior and independent security review pass.

## Evidence reviewed
- `requirements.txt`: no runtime third-party dependencies.
- `requirements-dev.txt`: jsonschema only.
- `.github/workflows/main.yml`: Python 3.12.
- PyPI metadata for `cryptography` 50.0.2 and `rfc8785` 0.1.4.
- RFC 8785 normative canonicalization and security requirements.

## Non-claims
This ADR does not implement a verifier, key registry, authorization service, replay registrar, or execution boundary. It does not authorize worker polling, MT5, broker, VPS, or live execution.
