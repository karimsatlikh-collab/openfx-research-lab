# OpenFX M3 Threat Model — Initial Audit

Status: **initial code-reviewed threat register**, not a security certification. This document distinguishes observed implementation behavior from controls that remain design requirements. No production executor or authorization boundary is claimed.

## Assets and trust boundaries

- Frozen StrategySpec, JobSpec, DataProfile, CostProfile, and GateConfig documents.
- Trial-family membership, unique trial accounting, run state, raw artifacts, and their hashes.
- The distinction between mock, synthetic, and mt5-demo evidence.
- Final out-of-sample results and gate feedback.
- Local files and CI workflows used to validate the prototype.

Inputs from users, source documents, transcripts, repositories, and generated model output are untrusted. A matching JSON field or SHA-256 digest establishes consistency/integrity of a known byte sequence; it does not establish who created it, whether a named engine ran, or whether the history is complete.

## Initial threat register

| Threat | Current evidence / control | Residual risk and required follow-up |
|---|---|---|
| Forged job fields or stale document references | validate_job_bundle compares canonical document hashes, IDs, versions, and budgets; unit tests cover wrong hashes and budget mismatch. | It is a helper, not yet a mandatory submission boundary. Add signed/authorized job envelopes before any real executor. |
| Boolean accepted as an integer budget | Initial audit found Python's bool is a subclass of int; gate-family max_trials=True could pass the semantic check. The validator now rejects booleans and a regression test covers it. | Re-run CI on the current head; review all numeric schema/runtime checks for the same type confusion. |
| Evidence-label spoofing | `validate_run_against_job` remains a consistency-only check. New `validate_attested_run` fails closed unless an attestation and external verifier are supplied; it binds job ID, run ID, requested engine, and implementation digest before delegating signature/policy verification. Negative tests cover missing verifier, mismatched claims, and verifier rejection. | The repository does not yet provide the trusted-key store, signature algorithm, executor identity provisioning, or mandatory integration point. The test verifier is a test double, not cryptographic proof. Do not treat a label or this helper alone as production authorization or proof of MT5 execution. |
| Role confusion / self-approval | The operating contract specifies proposer, implementer, executor, registrar, and independent validator separation. | Runtime permissions and identity enforcement are not implemented. Documentation is not access control. |
| Replay / duplicate submission | Local trial registry checks event-id idempotency, rejects reused keys with changed content, and counts unique trials under a local lock. | This does not provide server-side idempotency or a trusted central registrar. Cross-host replay is not addressed. |
| Prompt injection in source material | The operating contract says source media/transcripts are untrusted data, not executable instructions. | No isolated source-ingestion agent or automated prompt-injection adversarial suite is established by this prototype. |
| Artifact substitution | artifact_record records a relative path, size, and SHA-256 and rejects paths resolving outside the configured root. | A hash records bytes at check time; it does not make the file immutable or prove the artifact came from the claimed engine. Test symlink and post-record substitution cases and bind artifact hashes into a trusted run record. |
| Ledger tampering / history rewrite | Local JSONL hash-chain and semantic verification detect many accidental edits and internally inconsistent histories. | A privileged writer can rewrite the whole ledger and recompute hashes. There is no signature, external checkpoint, or independent anchor. |
| Concurrent local trial submissions | A bounded multi-process CI test checked 12 independent registry instances against a six-trial budget; six were accepted and six rejected, with the final ledger verified. | This is one CI scenario, not proof across filesystems, process-kill timing, power loss, or multiple hosts. |
| Crash-truncated ledger | A deliberately truncated final JSONL event is rejected during verification. | No automatic repair/recovery is implemented. Operator review is required; do not silently discard the damaged tail. |
| Final-OOS leakage through repeated verdict queries | Policy requires frozen splits, bounded verdict queries, and withholding final-OOS metrics. | The current prototype does not implement access control or enforce OOS secrecy. Do not use it for a real optimization campaign. |

## Release boundary

Before any real execution, the project must implement and independently review:
1. A mandatory submission path that validates the complete bundle and freezes its canonical hashes.
2. An authorization decision bound to an immutable job ID, implementation digest, engine, resource budget, and expiry/nonce.
3. Trusted executor attestation that cannot be supplied merely by copying the requested evidence label.
4. Registrar-owned idempotency, trial-family counts, and durable event storage.
5. Artifact provenance and substitution checks.
6. Role permissions and final-OOS access controls.
7. Adversarial tests for replay, forged status/engine fields, prompt injection, symlink/path attacks, altered artifacts, and whole-history rewrites.
8. Independent reproduction and a documented security review.

Until those conditions are met, the mock worker is a lifecycle smoke-test tool only. It does not execute shell commands, run MT5, connect to brokers, or trade. A green CI run is evidence only for the test cases actually executed; it is not a security certification, statistical validation, or evidence of profitability.


## Attestation boundary increment

`openfx.contract_validation.validate_attested_run` is a fail-closed boundary helper layered above the existing consistency validator. It requires a non-empty attestation carrying executor ID, job/run IDs, engine, implementation digest, issue timestamp, and signature field; it checks the claims against the frozen job/run and delegates authenticity/policy decisions to an externally configured verifier. Missing verifier, mismatched claims, verifier exceptions, and verifier rejection fail closed.

This is intentionally not described as a complete signature system: trusted public-key provisioning, signature format/algorithm, revocation/expiry/nonce policy, and mandatory wiring into an executor/registrar are not implemented. Unit tests use a verifier test double and establish only the helper's control flow. Until a real trusted verifier is independently reviewed and enforced at the run-ingestion boundary, all run records remain untrusted assertions.
