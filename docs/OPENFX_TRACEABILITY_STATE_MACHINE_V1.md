# OpenFX Traceability Matrix and Fail-Closed State Machine v1

**Status:** working design; not implementation-complete or release-approved.  
**Scope:** Issue #60 process/control-plane deliverable. Synthetic and local-source workflow only.  
**Snapshot:** 2026-10-31. PR status is a point-in-time record and must be rechecked before release.

## 1. Evidence vocabulary

| Label | Meaning | Does not establish |
|---|---|---|
| observed | Exact text or bytes were present in the inspected artifact | Source authenticity, exact speech, legal clearance, or semantic truth |
| source_claim | A source asserts the proposition | Independent confirmation |
| interpretation | An analyst's reading of source material | A source quotation or verified rule |
| hypothesis | A falsifiable proposed rule or explanation | An accepted strategy rule |
| verified_within_scope | A named check passed against named inputs and criteria | General truth outside that check |
| unknown / unresolved | Evidence is absent, ambiguous, or conflicting | Permission to infer a convenient answer |

A hash establishes byte identity relative to the hashed bytes. It does not establish who created the bytes, whether they are truthful, whether the source is authorized, or whether a transcript accurately represents speech.

## 2. Traceability matrix

| Stage | Canonical input → output | Existing implementation / evidence | Required tests or review | Release blocker |
|---|---|---|---|---|
| Source intake | Original source bytes + rights evidence → SourceRecord v1 | Legacy source registry/import bridge proposed in PR #65 | Missing bytes; digest mismatch; rights ambiguity; duplicate IDs; locator integrity | No source-backed claim without source bytes, digest match, and explicit rights decision/evidence |
| Transcript intake | SourceRecord + transcript bytes/segments → timestamped evidence segments | Legacy transcript importer adapted in PR #65 | Quote fidelity; timestamp/locator; extraction method; segment-source binding | Transcript text remains observed, not authenticated speech |
| Claim extraction | Evidence segment → AtomicClaim v1 or HypothesisCard v1 | Canonical bridge PR #65 | Exact quote/hash; classification; negation/number changes; unsupported claim; hypothesis separation | Hypothesis must never be silently promoted to AtomicClaim or verified rule |
| Independent evidence review | Claims + source evidence → review disposition | Process requirement in Issue #60; no completed independent review evidence established by this matrix | Reviewer independence; contradiction; omission; semantic drift; role collision | Proposer cannot self-certify; unresolved claims stay unresolved |
| Strategy specification | Accepted claims + labelled hypotheses → versioned StrategySpec | Canonical M1 contracts referenced by Issue #60 / PR #63 | Rule falsifiability; scope; invalidation; assumptions; source links; version/hash | No implementation from an unfrozen or ambiguous specification |
| Job preparation | StrategySpec + DataProfile + CostProfile + GateConfig → JobSpec v1 | Canonical M1 contract consumed by synthetic adapter PR #63 | Schema; immutable references; split/cost/family-budget validation | Freeze all inputs and family budget before registration/execution |
| Trial registration | JobSpec + trial identity → registry entry | Local JSONL registry used by PR #63 | Duplicate/ambiguous JSON; concurrent append/read; failed-attempt persistence | Every attempted trial, including failed/interrupted/rejected, consumes the registered family budget |
| Execution | Registered JobSpec → RunRecord v1 + artifacts/manifest | Synthetic-only adapter PR #63 | Deterministic fixture replay; safe paths; exact output set; hash/size/type; failure lifecycle | Synthetic execution only until trusted executor and independent validation exist |
| Independent validation | RunRecord + manifest + raw artifacts → validation report | Separate validator work exists in earlier project history; exact current integration must be rechecked | Recompute hashes; verify exact inputs; cost/time/leakage checks; independent reproduction | Same-process replay is not independent replication; local ledger is not a trusted registrar |
| Statistical gate | Frozen family + calibration evidence → GateVerdict | M3 v2.0.3 preregistration PR #44 | Preflight; all calibration cells; independent review; exact pinned provenance | PR #44 explicitly has no benchmark or calibration cells executed; gate remains unavailable |
| Research decision | All evidence + independent review + calibrated gate → bounded decision | Issue #60 defines decision categories | Evidence-level audit; final OOS protection; role separation | No profitability claim from synthetic tests or CI |

### Point-in-time code status

- PR #63 (Add canonical M1 synthetic job adapter) is open, Draft, and unmerged. Its description limits it to synthetic evidence; deterministic same-code replay is not independent replication.
- PR #65 (Add fail-closed canonical source evidence bridge) is open, Draft, and unmerged, stacked on PR #63. It requires original source bytes and explicit rights evidence. Its provenance status observed does not authenticate speech or prove truth.
- PR #44 (Pre-register M3 v2.0.3) is open, Draft, and unmerged. CI is not calibration. Its description states that the performance preflight and all 40 calibration cells have not run.
- This document does not merge, approve, or change those PRs. Recheck their current heads and checks before relying on this snapshot.

## 3. Fail-closed lifecycle state machine

### 3.1 Claim and hypothesis

UNSEEN → CAPTURED → LINKED → REVIEW_PENDING → ACCEPTED_SOURCE_CLAIM

Alternative holding/terminal states:

- HYPOTHESIS: proposed interpretation; may link to source-backed claims but is never itself a verified rule.
- UNRESOLVED: missing evidence, contradiction, ambiguous rights, failed quote/locator match, or reviewer disagreement.
- REJECTED: demonstrably unsupported or contradicted under the stated review criteria.

Transitions require stable IDs and immutable source/quote references. Any source, quote, classification, or meaning change creates a new revision and invalidates downstream approvals. No automatic promotion from hypothesis to accepted claim is allowed.

### 3.2 Strategy and job

DRAFT_SPEC → REVIEWED_SPEC → FROZEN_SPEC → FROZEN_JOB

- DRAFT_SPEC: incomplete and not executable.
- REVIEWED_SPEC: rule logic, scope, invalidation, assumptions, and evidence links reviewed.
- FROZEN_SPEC: version and digest fixed; edits require a new version.
- FROZEN_JOB: exact strategy, data profile, cost profile, gate configuration, splits, and family budget fixed.

A material change to any frozen input creates a new spec/job identity. Never mutate an already registered trial's inputs.

### 3.3 Trial and run

NOT_REGISTERED → REGISTERED → RUNNING → COMPLETED

Failure/interrupt paths:

- REGISTERED → FAILED
- RUNNING → FAILED
- RUNNING → INTERRUPTED

Registration must be durable before execution begins. Every terminal outcome is retained; no deletion or silent retry. A retry is a new attempt with a new identity and consumes the frozen family budget. COMPLETED means the executor returned the required artifacts and record; it is not a performance pass.

### 3.4 Validation and decision

RUN_COMPLETED → VALIDATION_PENDING → VALIDATED_WITHIN_SCOPE

Alternative states:

- VALIDATION_FAILED: input, hash, cost, timing, leakage, or reproduction check failed.
- VALIDATION_INCONCLUSIVE: evidence is insufficient or the independent check cannot be completed.
- REPLICATION_CANDIDATE: passed stated checks but still requires a separate independent replication.
- GATE_BLOCKED: required statistical calibration or preregistered gate is unavailable.
- REJECTED: the defined acceptance criteria were not met.

Only a separately reviewed, calibrated statistical gate may issue a bounded gate verdict. A successful CI run, synthetic fixture replay, or validator pass is not a market edge or profitability finding.

## 4. Role separation and conflict controls

| Role | May do | Must not self-certify |
|---|---|---|
| Source analyst | Capture source, rights assertion, transcript and locators | Legal clearance or semantic truth |
| Evidence analyst | Split exact claims and hypotheses | Independent review of own extraction |
| Independent reviewer | Challenge source/quote/classification and contradictions | Review work where they were proposer or implementer |
| Strategy architect | Freeze rule logic and assumptions | Promote hypotheses by wording alone |
| Implementer | Implement frozen specification | Change rules silently or hide failed trials |
| Registrar / experiment manager | Freeze job and register every attempt | Alter a registered trial after execution |
| Executor | Produce raw run evidence | Issue a research-performance verdict |
| Independent validator | Verify inputs, artifacts, costs, leakage and reproducibility | Validate work they proposed or implemented |
| Statistical reviewer | Assess calibration and gate validity | Treat CI or unexecuted calibration as evidence |

If one person or agent occupies multiple roles, declare the collision. A logically independent review must be performed by a different reviewer/process with access to the frozen evidence, not merely a second label assigned to the same actor.

## 5. Minimum end-to-end acceptance trace

A release candidate must provide one reproducible trace containing:

1. Stable source ID, original bytes digest, rights decision/evidence, and source locator.
2. Transcript/segment ID, exact quote, quote digest, transcript digest, extraction method, and timestamp locator.
3. AtomicClaim ID or HypothesisCard ID with explicit epistemic status and reviewer disposition.
4. StrategySpec version/digest with claim links, hypotheses, falsifiable conditions, scope, and invalidation rules.
5. JobSpec v1 digest with exact data/cost/gate profiles, splits, and family budget.
6. Durable trial registration before execution, including failed/interrupted attempts.
7. RunRecord v1, exact artifact manifest, raw artifacts, and verified hashes.
8. Independent validation report bound to the exact run and artifacts.
9. Statistical calibration/gate evidence, if a gate is claimed.
10. Final decision with explicit evidence level, unresolved limitations, and no overstatement.

## 6. Adversarial test matrix

| Attack / failure | Expected fail-closed behavior |
|---|---|
| Missing original source bytes | Block source-backed conversion |
| Digest mismatch or substituted source | Reject conversion and preserve diagnostic |
| Ambiguous/unknown rights | Block; do not infer permission from public visibility or legacy labels |
| Quote omission, changed number, changed negation | Flag mismatch; do not accept the claim |
| Timestamp or segment points to another source | Reject source/segment link |
| Hypothesis labelled as verified by legacy metadata | Preserve as hypothesis; never upgrade |
| Prompt injection inside source/transcript | Treat as untrusted content, never as workflow instruction |
| Reviewer is proposer/implementer | Declare role collision; require distinct reviewer |
| Parameter or source revision changes after freeze | Reject as same trial; create new version/attempt |
| Trial omitted after a failed run | Detect registry/run mismatch; block validation |
| Final OOS data exposed during iteration | Block final-OOS claim; require protected holdout process |
| Artifact path traversal, symlink, extra/missing output | Reject artifact bundle |
| Same-code replay described as independent replication | Reject the claim of independence |
| CI pass described as calibration or profitability | Reject evidence classification |
| Worker request without signed authorization and nonce controls | Keep worker polling disabled |

## 7. Execution boundary and host decision

The Android phone currently used to communicate with ChatGPT is **not an approved M3 research host**. It may be useful for reviewing GitHub and lightweight communication, but the M3 preflight requires a stable, explicitly selected environment with pinned Python/NumPy/Numba/platform/CPU-count provenance, sustained CPU execution, and enough storage. Mobile background limits, thermal throttling, and environment reproducibility make a phone unsuitable for the current benchmark acceptance contract.

This is a project suitability decision, not a claim that Android can never execute Python. No benchmark has been run on the phone. Do not start the 3-family preflight or 40-cell campaign on it. A dedicated computer or provisioned cloud research host must be selected and its resource budget approved first.

Until then:
- Continue source/evidence, code, documentation, and CI review through GitHub.
- Keep M3 preflight and all 40 cells blocked.
- Keep broad optimization, market data, MT5, broker, VPS worker polling, paid APIs, and live trading disabled.

## 8. Release checklist

- [ ] Every stage has stable input/output IDs and hashes.
- [ ] Source bytes and rights evidence are present where required.
- [ ] Hypotheses remain explicitly unverified.
- [ ] Independent reviewer/validator role collisions are resolved.
- [ ] StrategySpec and JobSpec are frozen before trial registration.
- [ ] Failed/interrupted trials are retained and consume family budget.
- [ ] RunRecord and artifact manifest are bound to exact bytes.
- [ ] Independent validator is separate from proposer/implementer.
- [ ] M3 preflight and calibration evidence are complete and independently reviewed before gate use.
- [ ] CI evidence is tied to exact commit SHA and named test runs.
- [ ] No market-performance or profitability claim exceeds the evidence.


## 9. Independent review update — 2026-10-31

### Exact-head CI evidence rechecked

- PR #63 head `d3da8b7ca027d975d5d02934a82580f5d84c2936`: OpenFX Unit Tests run 811 and Project Tests run 992 both completed successfully.
- PR #65 head `3d0a02788f1b33f3a6967d15fae0ddbf135de446`: OpenFX Unit Tests run 842 and Project Tests run 1023 both completed successfully.
- PR #44 head `2211b4d537642dd2b86414860a426403b54cfda9`: OpenFX Unit Tests run 722 and Project Tests run 902 both completed successfully. These are code/contract checks, not the M3 preflight or calibration campaign.
- PR #66 head `06ea241a8ff9da8bbf7aa208150d60b0a9efcdaf`: OpenFX Unit Tests run 845, Project Tests run 1026, and CodeQL security analysis run 267 all completed successfully. Documentation CI does not validate the correctness or completeness of the workflow design.

### Code-review observation requiring follow-up

A source-level review of PR #63 found that the adapter assigns the same timestamp value to `created_at_utc`, `started_at_utc`, and `finished_at_utc`, after both replay executions have already completed. This makes the RunRecord lifecycle timestamps non-observational and can misrepresent elapsed execution time/order. Before treating RunRecord timing as evidence, capture each timestamp at its actual lifecycle boundary and add a regression test proving the ordering and non-negative duration. The current synthetic result must not be used for runtime benchmarking.

The local JSONL registry remains a declared trust limitation; this review did not establish atomicity under concurrent writers, tamper resistance, or trusted central registration. Those are separate implementation/release blockers, not assumed solved by the passing CI.

PR #65 source-level review confirms conservative classification and explicit rights-evidence inputs in the bridge, but those caller-supplied rights decisions remain assertions and are not independent legal determinations. Transcript quote matching and byte hashes establish structural linkage only, not authenticity of the source or accuracy of speech recognition.

### Current release position

All three relevant PRs (#63, #65, #44) remain Draft/unmerged in the current fetched snapshots. PR #66 remains Draft/unmerged. No PR was merged or approved by this review. M3 benchmark and 40-cell campaign remain unexecuted and blocked pending a selected research host and approved resource budget.
