# Programmer review — action plan (items 1–5)

Status: evidence-based review and execution plan, 2026-10-30. This document does not claim that a strategy, MT5 run, or Windows worker has been validated.

## 1. Trial registry, statistical gates, and final OOS

**Existing work:** PR #23 adds versioned research contracts, a local JSONL trial ledger, trial-family accounting, a synthetic engine, and a descriptive gate. Its CI runs for commit `06755819b418cff1052ebc2f6109536edbd5e840` completed successfully (Project Tests, OpenFX Unit Tests, CodeQL).

**Not complete:** the ledger is a local prototype and can be rewritten by a privileged actor; the gate explicitly reports that no DSR/PBO/familywise correction is calculated; synthetic calibration is not yet broad enough to bound false-positive rate and power across generator families. Issue #24 already specifies the next calibration protocol (at least 1,000 null seeds per family, confidence intervals, predeclared detectable effect, leakage fixtures, disjoint calibration/regression seeds).

**Decision:** do not start broad strategy parameter optimization or treat a synthetic gate pass as market evidence until Issue #24 is implemented and independently reviewed, and a multiple-testing method is actually calculated—not merely named in metadata. Keep final OOS untouched and access-controlled.

## 2. One state machine and evidence level

**Existing work:** PR #23 defines a richer RunRecord contract with states QUEUED, VALIDATED, APPROVED, RUNNING, VERIFYING, COMPLETED and terminal alternatives FAILED, TIMEOUT, INTERRUPTED, REJECTED, CANCELLED; it separates status from evidence_level (mock, synthetic, mt5-demo).

**Gap found:** the current runtime module `openfx/experiment.py` still implements only QUEUED, RUNNING, COMPLETED, FAILED. The schema/documentation and executable runtime therefore do not yet share one state machine.

**Decision:** before enabling additional execution, align the runtime, schemas, mock worker, CLI, tests, and docs to one versioned transition table. COMPLETED must not imply independently verified evidence. Evidence level must be mandatory and independent of state. Illegal transitions must fail closed. Keep compatibility/migration behavior explicit rather than silently reinterpreting old manifests.

## 3. Independent validator

**Existing work:** PR #29 adds a read-only CLI validator, Ed25519 attestation verification, trust-store schema, job/run/digest/nonce binding, artifact hash/path checks, and adversarial subprocess tests. All three associated CI workflows completed successfully for commit `cb47d8643a024d07a603264f6ee0ee7352a3a3a8` (Project Tests, OpenFX Unit Tests, CodeQL).

**Not complete:** this is process separation, not proven OS isolation. Production key custody, trust-store administration, separate validator identity/host, registrar-enforced one-time nonce consumption/replay prevention, and an independent human security review remain open.

**Decision:** retain PR #29 as a prototype and do not call real runs independently validated until its documented release gates are demonstrated. Do not merge it solely because CI is green.

## 4. Zero-cost Windows local smoke test before VPS

**Repository evidence:** `worker/README.md` says the worker is design/prototype only; the MT5 adapter is not implemented. The documented `--self-test` validates manifests and does not run Strategy Tester.

**What can be done now:** prepare and execute the non-privileged Python/worker self-test on an owner-controlled Windows computer, then record OS/Python versions, exact commands, exit codes, logs, and RDP-disconnect behavior if relevant.

**What cannot be claimed now:** no Windows machine was accessed by this repository review; no Windows test, MT5 installation, Strategy Tester run, VPS deployment, or RDP-disconnect test has been performed. Do not purchase a VPS for this stage. MT5 smoke testing remains blocked until a safe, explicit adapter and test protocol exist.

## 5. Legacy root files and dependencies

The current root contains `data_collection.py` and `evaluation.py`, which belong to the earlier local-file/video-data-collection scope. Their current purpose is not part of the OpenFX strategy-research runtime described by README. `requirements.txt` currently states that the initial version has no third-party runtime dependencies. `main.py` is still the startup/status scaffold, and `create_experiment.py` is an active manifest CLI; they must not be removed as if they were legacy.

**Decision:** do not delete or move legacy files in this pass. First check imports, tests, workflow references, documented commands, and historical compatibility. Then either move them to a clearly labelled `legacy/` area with preserved history or remove them in a separately reviewed PR. Keep runtime dependencies separate from development/test dependencies; explain why `requirements.txt` is intentionally empty.

## Existing work items (do not duplicate)

- PR #23 — research contracts, trial registry, synthetic harness and schemas.
- Issue #24 — quantitative calibration protocol; still open.
- PR #26 — README mission and evidence-first governance wording.
- PR #29 — standalone independent validator prototype.

All four PRs are open draft PRs, not merged into main. Their green CI runs are code/test evidence only; they do not establish statistical calibration, security independence, MT5 execution, or profitability.

## Release order

1. Finish Issue #24 calibration and choose/apply a defensible selection-bias correction.
2. Reconcile runtime state machine with RunRecord schema and evidence_level.
3. Complete independent validator identity, key custody, replay/registrar and clean-room review.
4. Run the documented zero-cost Windows checks on the owner's computer; record results, do not infer them.
5. Decide legacy-file disposition only after reference/dependency audit.
6. Only after these gates: consider any market-data or MT5 demo integration. VPS and paid services require a separate explicit owner decision.
