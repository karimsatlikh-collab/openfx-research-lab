# OpenFX Architecture Foundation — M1 Contracts

Status: **design contract / schema-only foundation**. These files define interfaces; they do not claim the runtime, security controls, statistical gate, synthetic engine, MT5 execution, or persistent registrar already exist.

## Purpose

Establish stable, versioned contracts before adding more execution capabilities. Every run must be traceable to frozen strategy rules, implementation, data/cost profiles, gate configuration, outputs, and its place in the full trial family.

## Role boundaries

- **Proposer:** may propose a StrategySpec and request a job; cannot self-approve results or inspect untouched final OOS metrics.
- **Implementer:** translates an approved StrategySpec into code; must record source revision/build hash.
- **Executor:** runs only a validated and approved JobSpec through an explicitly named engine; it returns raw artifacts and execution facts, not a performance verdict.
- **Registrar:** records every accepted job/run/trial, including failures and cancellations, with stable identifiers and immutable references.
- **Validator / Replicator:** independently checks outputs and attempts reproduction. They must not be the same logical role as the proposer or implementer.
- **Gate:** applies a pre-registered, versioned configuration and returns a separate GateVerdict. A pass is a statistical/methodological gate result, not proof of profitability.
- **Human owner:** approves policy changes, any move to a real MT5 demo executor, external paid services, VPS deployment, and any live-trading scope.

Source material (videos, transcripts, web pages, issues, and files) is untrusted data, never executable instructions. Prompt-injection content in sources must not change system policy or trigger tools.

## Run state and evidence level

The RunRecord state machine is:

`QUEUED → VALIDATED → APPROVED → RUNNING → VERIFYING → COMPLETED`

Terminal alternatives: `FAILED`, `TIMEOUT`, `INTERRUPTED`, `REJECTED`, `CANCELLED`.

The state is independent of `evidence_level` (`mock`, `synthetic`, `mt5-demo`). In particular, `COMPLETED` means the named job reached its recorded terminal state; it does not mean that the result was independently verified or that a strategy is profitable. A mock result must never be labelled as MT5 evidence.

## Required binding / provenance

JobSpec binds immutable references and SHA-256 digests for StrategySpec, implementation/build, DataProfile, CostProfile, frozen parameters, engine choice, and finite trial/time budgets. RunRecord records these inputs plus output artifact hashes and status. GateVerdict records the gate version/config digest and trial-family count at decision time. A digest provides integrity checking for a known object; it does not, by itself, prevent an administrator from rewriting an entire history. Production append-only storage and independently anchored checkpoints remain future work.

## Statistical and OOS safeguards

- Count every trial, including failed, rejected, interrupted, and abandoned attempts, in the relevant family where applicable.
- Freeze gate thresholds/configuration before the run family begins; preserve revisions and reasons for any later change.
- Do not expose final OOS metrics to the proposer during iterative search. A pass/fail signal can itself leak information, so cap queries and track them in the trial registry.
- Select and justify a multiple-testing / selection-bias method (for example DSR/PBO or a defensible alternative) before interpreting optimized results.
- Require cost sensitivity and separate development, validation, and untouched final OOS periods. Never claim these checks were performed from user-supplied booleans alone.
- Synthetic calibration should include seeded repeatability, noise/no-edge false-positive tests, planted-edge power tests, and deliberate look-ahead/leakage tests. Passing synthetic fixtures only validates the harness against those fixtures.

## Delivery sequence

1. **M1 — contracts (this change):** schemas and architecture contract; no executor changes.
2. **M2 — registry, gate, and SyntheticEngine:** implement state transitions, idempotent registration, append-only events, trial-family tracking, frozen gate configuration, and calibration tests.
3. **M3 — threat model and signed jobs:** validate authorization, signatures, resource limits, and untrusted-input boundaries; negative security tests.
4. **M4 — local Windows MT5 demo spike:** only after M2/M3 gates; prove two reproducible runs with captured logs/reports and measured runtime.
5. **M5 — unattended queue/VPS:** only after M4 review and explicit owner approval.

## Explicitly not implemented by M1

No production database, append-only ledger, signature/key infrastructure, actual proposer/validator agents, synthetic engine, statistical calculations, MT5 bridge, VPS, broker connectivity, paid API, or live trading. The schemas are contracts only. At the initial M1 commit, full JSON Schema validation in CI, semantic state-machine enforcement, trusted engine attestation, and server-side trial registration were follow-up tasks. The current branch adds structural JSON Schema validation tests; semantic state-machine enforcement, trusted engine attestation, and server-side trial registration remain follow-up tasks.

## Schema index

- `strategy-spec-v1.schema.json`: explicit rules and claim provenance.
- `job-spec-v1.schema.json`: immutable references to strategy, data, cost, and frozen gate configuration; implementation digest, frozen parameters, finite budgets, and engine evidence class.
- `data-profile-v1.schema.json`: versioned source, symbol/timeframe, date range, data mode, and dataset digest.
- `cost-profile-v1.schema.json`: versioned spread, commission, slippage, swap, and symbol specifications.
- `gate-config-v1.schema.json`: pre-frozen thresholds, trial-family budget, data splits, multiple-testing method, and cost sensitivity.
- `docs/RESEARCH_TEAM_OPERATING_CONTRACT.md`: role permissions, evidence chain, trial accounting, OOS protection, threat boundaries, and release gates.
- `run-record-v1.schema.json`: state, evidence level, bound input digests, and output artifact digests.
- `trial-registry-entry-v1.schema.json`: records trial-family membership and failed/non-completed outcomes.
- `gate-verdict-v1.schema.json`: separate, versioned gate result and recorded trial count.

These JSON Schemas are initial contracts and require review/versioning before they are treated as a production API.


## M2 prototype additions (not production-ready)

The current branch now includes:
- `openfx/trial_registry.py`: a local JSONL event ledger prototype with event hashes, a hash chain, idempotency-key checks, family sequence numbers, a lock file, and tamper detection tests.
- `openfx/synthetic_engine.py`: deterministic seeded synthetic returns and summary metrics; explicit evidence label `synthetic`; a timestamp-level look-ahead guard for controlled fixtures.
- `openfx/statistical_gate.py`: a small frozen-config descriptive threshold gate with trial-budget checks. It explicitly reports that no multiple-testing correction was calculated.
- `tests/test_m2_research_controls.py`: repeatability, no-edge false-positive calibration, planted-edge detection, explicit future-timestamp rejection, trial-budget enforcement, idempotency, and tamper-detection tests.

Limitations and release blockers:
- The local registry is not a trusted central registrar, not cryptographically signed, and not resilient to a privileged actor rewriting the entire ledger. The lock file can become stale after a hard crash and requires operator review; do not automatically delete it.
- The synthetic generator is an abstract return-stream fixture, not a market simulator, not representative market data, and not evidence of strategy edge.
- The timestamp guard catches only explicit timestamp violations in fixtures; it cannot detect every form of look-ahead, revised data, target leakage, or contaminated feature computation.
- The descriptive gate does not implement DSR, PBO, familywise error control, or statistical power analysis. The config records a pre-registered method, but the prototype does not calculate that method. It must not be described as a production statistical validator.
- Trial counts supplied to this prototype are caller-provided. A trusted registrar must own monotonic counts before the gate can be relied upon.
- Structural JSON Schema validation is now exercised in `tests/test_json_schema_validation.py` using Draft 2020-12 validation and format checks. The workflow installs the pinned-major development dependency from `requirements-dev.txt`; this validates schema shape and sample instances, not cross-document consistency or runtime authorization.
- M2 is not complete until CI is green on the latest commit, semantic contract checks and threat-model tests are expanded, and an independent review accepts these limitations.


## Semantic contract validation increment

The branch now includes `openfx/contract_validation.py` and focused tests in
`tests/test_contract_validation.py`. The checks compare JobSpec references
against canonical JSON SHA-256 hashes of the referenced StrategySpec,
DataProfile, CostProfile, and GateConfig; reject a job budget larger than the
frozen gate-family budget; check RunRecord-to-JobSpec hash/evidence-label
consistency; require a finish timestamp for `COMPLETED`; and reject illegal
RunRecord state transitions. A lifecycle status is explicitly not interpreted
as a performance verdict.

The local registry exposes a unique-trial count per family and an opt-in gate
helper that reads that count. Registry append now optionally enforces a
family's positive-integer trial budget while holding the same exclusive lock
used to read and append the ledger. New trials consume budget on their first
event regardless of outcome; an idempotent retry is checked before budget
enforcement. The event lifecycle rejects contradictory follow-up events:
a pending trial may transition once to a terminal outcome, and a terminal trial
cannot later be changed to a different outcome. Legacy/imported trials may
still be recorded directly with a terminal outcome, but then are immutable at
the event-lifecycle level.

This remains a single-host prototype: the standalone count read and gate
evaluation are not a transaction, there is no central authority or signed
ledger, and the direct gate function still accepts a caller-provided count for
isolated tests. Production use requires a trusted transactional registrar and a
gate API that accepts only registrar-issued snapshots.

These checks are semantic consistency controls, not engine attestation,
authorization, statistical correction, or evidence of profitability.


## Adversarial registry hardening increment

The local registry's verification pass now checks more than hash-chain integrity:
it validates required event fields and types, unique event identifiers, monotonic
sequence/family-sequence values, stable trial indices, family ownership of trial
IDs, supported outcomes, and event lifecycle consistency. This helps detect
internally inconsistent ledgers even if the rows' hash chain is otherwise
well-formed. It is not protection against an administrator who can rewrite the
entire ledger and produce a fully consistent replacement.

Additional adversarial tests cover unsupported outcome types and stale-lock
behavior. A stale lock causes a bounded timeout and is deliberately not deleted
automatically, because the prototype cannot safely determine whether its owner
is still active. A multi-process test now starts independent registry instances
against one local ledger and verifies that concurrent unique trial submissions
cannot exceed the configured family budget; it also verifies the resulting hash
chain and event count. This is a bounded CI test, not proof of correctness under
all operating systems, filesystems, process-kill timings, or power-loss cases.
A deliberately truncated final JSONL event is rejected closed during
verification. There is no automatic repair/recovery because the prototype
cannot reliably distinguish a crash-truncated write from corruption. Power-loss
durability, crash recovery, and trusted multi-host registration remain open
verification/design work.
