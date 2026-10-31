# Independent review release gate — 2026-10-31

## Purpose and evidence boundary

This record consolidates the independent review archive and the repository follow-up work. It is a release-control record, not a claim that OpenFX is production-ready.

Review archive: `openfx_review_2026-10-31.zip`  
Archive SHA-256: `8a2c7d8f1c5210d1a72324db6c148b6b5e2b0fd55e1df60d2427e458bc2ef8c1`

The archive's seven reference tests passed in its own stubbed harness. They are not a substitute for tests against the repository's real implementations. All CI statements below identify the exact tested commit.

## Current change stack

| PR | Purpose | Current head / base | CI evidence | State |
|---|---|---|---|---|
| #63 | Canonical synthetic adapter; trial identity guard; lifecycle timestamps; registry verification | head `971f58168f99cbf5783cc10578c7113bdc365a08`, base `openfx-foundation-m1-contracts` | OpenFX Unit Tests run 862: success; Project Tests run 1043: success | Draft, unmerged |
| #68 | Effective trial-family cap | head `8ca254225483733ec314be8b06693fb4d25f3cd2`, base PR #63 head | OpenFX Unit Tests run 888: success; Project Tests run 1069: success | Draft, unmerged |
| #69 | Cleanly restacked canonical source-evidence bridge | head `e58e9161731d1082c61e904eaa6029bce56afd75`, base PR #68 head | OpenFX Unit Tests run 895: success; Project Tests run 1076: success | Draft, unmerged |
| #65 | Original source-evidence bridge branch | merge base with current PR #63 is `d3da8b7ca027d975d5d02934a82580f5d84c2936`; current PR #63 is six commits ahead | Prior CI was green for older head; branch is diverged from current stack | Superseded by #69; do not merge |

PR #69 is intentionally a five-file restack. Comparing its head with its base yields exactly five added source-evidence files and five commits; it does not duplicate the synthetic adapter changes.

## Findings fixed

1. **Terminal trial replay:** a trial identity already present in the local registry is rejected under the registry lock before an idempotent event return can authorize another execution.
2. **Interrupt accounting:** a `KeyboardInterrupt` is recorded as `interrupted`, with a terminal timestamp.
3. **Registry integrity:** the adapter verifies the registry after registration and after terminal registration; post-registration verification is within the protected failure lifecycle.
4. **Lifecycle timestamps:** creation, start and finish are captured at their actual lifecycle boundaries; regression coverage checks their ordering and elapsed time.
5. **Source digest continuity:** the source bridge rejects absent, blank, or non-string legacy `content_sha256` and verifies supplied original bytes against the recorded digest.
6. **Trial-family cap:** registration uses `min(JobSpec.budget.max_trials, GateConfig.trial_family_policy.max_trials)`. A test-first run failed with the observed mismatch `2 != 1`; the implementation was then corrected and both CI workflows passed on the corrected head.

## Remaining release blockers

### A. PR #11 worker/security boundary

PR #11 remains Draft and is large (46 files, 146 commits, +4,059/-308). Its existing review identifies blockers that must not be waived:

- A job-provided `approved: true` is self-asserted approval, not a signed AuthorizationRecord.
- The worker accepts a compact envelope, not canonical M1 JobSpec v1 with immutable strategy/data/cost/gate/build/parameter/budget bindings.
- The worker boundary does not enforce canonical evidence, cost and chronological development/validation/final-OOS split identity.
- Local `seen_jobs` state is not an authoritative central registrar or durable nonce-consumption service.
- Filesystem state durability, temporary-file handling and stale-lock recovery need adversarial testing and explicit single-host limitations.
- Date-only job ranges need an explicit market/broker timezone and UTC/DST policy.
- The PR must be split into independently reviewable changes before security-sensitive approval.

### B. CI supply-chain hardening

- Pin third-party GitHub Actions to reviewed full commit SHAs, retaining human-readable version comments.
- Review duplicate test execution in scheduled reporting workflows; either justify it or reduce reporting workflow to report/health duties.
- Keep permissions least-privilege and ensure no privileged self-hosted runner is attached to this public repository.

### C. Evidence and provenance limits

- The local JSONL registry remains a single-host prototype; its hash chain detects edits but is not tamper-proof against a privileged actor.
- A matching SHA-256 proves byte equality to the supplied digest, not source authenticity, authorship, legal rights, or truth.
- Transcript quote matching establishes text traceability, not exact speech fidelity.
- Caller-supplied rights decisions are recorded assertions, not independent legal clearance.
- Same-code deterministic replay is not independent replication.
- The descriptive synthetic gate does not implement DSR, PBO, or family-wise error correction.
- No MT5, market-data, broker, VPS, or profitability validation has been performed by these changes.

### D. Review independence

The current PR author identity and available automation do not establish independent human review. Do not treat self-review, a second model, or green CI as a substitute for an independent reviewer. Before marking security-sensitive PRs ready or merging them, obtain a named human reviewer who did not author the changes and record their review outcome.

## Required merge order

1. Review and accept the M1 foundation branch through its own independent gate.
2. Review PR #63; merge only after an independent human review and fresh CI on its exact head.
3. Review PR #68 against the merged #63 base; re-run CI after rebasing if needed.
4. Review PR #69 against the merged #68 base; re-run CI after rebasing if needed.
5. Retire PR #65 only after #69 is independently reviewed and its replacement is accepted.
6. Keep PR #11 blocked until split into smaller PRs and the worker authorization, canonical contract, evidence, registrar, filesystem and timezone blockers are addressed.

Never merge a stacked PR based only on an earlier green run for a different commit. Re-run required checks against the final merge candidate.

## Explicitly prohibited conclusions

This release gate does not authorize worker polling, MT5 execution, broker/VPS access, live trading, source downloading without rights review, or any profitability claim. A green CI result means only that the checked tests passed on the identified commit.
