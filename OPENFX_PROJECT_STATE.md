# OpenFX Project State and Continuation Ledger

**Last reconciled:** 2026-10-29  
**Repository:** `karimsatlikh-collab/openfx-research-lab`  
**Default branch observed:** `main`  
**Purpose:** Preserve evidence-backed project state and a precise continuation point across chats.

> This ledger is a checkpoint, not proof that a feature works. Re-check the live repository and workflow runs before relying on any status below.

## 1. Mission and governing constraints

The standing mission is defined in `OPENFX_MISSION.md`: build a source-traceable, reproducible AI-assisted Forex research and validation platform. Do not confuse source extraction, hypotheses, mock workflows, metadata checks, historical backtests, and independent validation.

Owner approval is required before paid services/API/cloud compute, VPS purchase/deployment, production worker activation, broker access, live trading, material public commitments, or merging any PR into `main`.

## 2. Repository state observed on 2026-10-29

- The GitHub repository is `karimsatlikh-collab/openfx-research-lab`.
- The `main` branch was listed at commit `25c1366097c2ddf3a7951111ca9e9a1e6e4928b6` during this reconciliation.
- Branches observed included `openfx-audit-fixes` at `28161cb4622e4bd92ba356508b97409f6149a1af` and `openfx-transcript-adversarial-checks` at `649631de5f3a08be1ca0941ede4ff3646b346063`.
- PR #11, “Harden OpenFX experiment and worker validation,” was reported open and not merged by the connector at the time checked. Its declared scope includes stricter experiment/worker validation and explicitly excludes a production control plane, video discovery/transcription, semantic evidence tracing, and an MT5 execution adapter.
- PR #12, “Flag percentage changes in transcript fidelity checks,” was reported open and not merged by the connector at the time checked. Its head is `openfx-transcript-adversarial-checks`, based on `openfx-audit-fixes`.
- A historical project checkpoint reported OpenFX CI run `40921649710` as successful for the transcript-percentage changes. This is a historical report, not confirmation of the current workflow state; refresh the Actions run before relying on it.
- Do not merge either PR without explicit owner approval.

## 3. Verified limits and current capability boundaries

The following boundaries are explicitly documented in the repository and/or were visible in inspected code during this reconciliation:

- The worker at `worker/openfx_worker.py` is a validation/audit prototype. Its module documentation and implementation state that it does not invoke MT5 or execute jobs.
- The mock worker simulates experiment lifecycle behavior; it is not a market backtest and does not establish strategy performance.
- A source registry or transcript-quality heuristic is not the same as fully autonomous source discovery, complete transcript extraction, or semantic verification.
- Numeric, date, percentage, and negation checks are heuristics. They can flag suspicious changes but cannot prove that meaning was preserved.
- MT5 report metadata validation is not equivalent to independently validating the original report bytes, reproducing the Strategy Tester run, or verifying profitability.
- The repository's Windows VPS/MT5 planning documents state that no VPS purchase/deployment or MT5 VPS installation/backtest has been confirmed.
- No live trading is authorized by this ledger.

## 4. Reconciliation cautions

Repository documents and implementation may have advanced on non-main branches and may not describe the same revision. Before making claims about a feature:

1. Identify the exact branch and commit containing it.
2. Read the relevant implementation and tests at that same revision.
3. Check whether the branch is merged into `main`.
4. Inspect the latest relevant Actions run and its individual jobs.
5. State exactly what the evidence proves and what it does not prove.

If README, roadmap, checkpoint, code, or CI status disagree, record the disagreement as a finding and resolve it based on current evidence. Do not silently treat a PR's contents as part of `main`.

## 5. Work completed in this documentation reconciliation

- Created this continuity ledger and the standing mission charter on the task branch `openfx-mission-state-docs`, based on the observed `main` branch.
- No existing source code, strategy code, workflow, or open PR was merged or modified by this documentation task.
- The documentation branch itself is not the main branch; its files must be reviewed before merging.

The commit SHA for the first file creation is recorded in the GitHub action result; record the second file's commit SHA in the final task report.

## 6. Priority backlog for the next audit cycle

These are proposed priorities, not claims that the work has been completed.

### P1 — Establish an evidence-backed baseline
- Refresh PR #11 and #12 status and all relevant Actions runs, including individual job results.
- Inventory the actual tree on `main` and relevant feature branches.
- Compare README, ROADMAP, CHANGELOG, schemas, tests, worker behavior, and docs at matching commits.
- Produce a capability matrix with branch/commit and evidence for each claim.

### P1 — Source/evidence integrity
- Inspect `openfx/evidence.py`, source registry schemas, claim-register schema, transcript importer, and transcript-quality checks on the correct branch.
- Verify that source-confirmed claims require the expected human verification and exact segment/quote linkage.
- Test Persian/Latin digits, signed numbers, dates, units, percentages, dropped negation, changed values, and benign formatting differences.
- Measure both false positives and false negatives on a small labelled adversarial fixture set.

### P1 — Reproducible experiment integrity
- Audit manifest/result schemas and CLI validation against malformed, incomplete, inconsistent, or forged records.
- Verify artifact hashes against actual files in a trusted root.
- Separate metadata consistency checks from independent report parsing and actual tester reproduction.
- Add synthetic cases for costs, order timing, missing bars, gaps, and look-ahead leakage.

### P1 — Worker and security boundary
- Review URL validation, redirect behavior, host allowlists, idempotency, retries, persistence, and failure recovery.
- Check GitHub Actions permissions, external pull-request handling, prompt-injection exposure, and secret boundaries.
- Do not deploy or enable real execution until a separate control plane, threat model, and owner approval are in place.

### P1 — MT5 validation plan
- Keep the Windows host compatibility and procurement work as planning only until the owner approves a specific purchase.
- Define a controlled non-trading smoke test and required raw artifacts.
- Do not report a real MT5 test until a compatible host actually runs it and the report/logs are retained.

### P2 — Maintainability and cost
- Identify duplicated workflows, stale docs, nested/misplaced workflow files, unpinned dependencies/actions, and unnecessary complexity.
- Prefer the smallest architecture that meets measured needs.
- Preserve negative results and avoid expanding infrastructure before the pilot demonstrates a need.

## 7. Continuation protocol

At the start of each continuation:
1. Read `OPENFX_MISSION.md` and this file.
2. Refresh live GitHub branch, PR, commit, and Actions status.
3. Confirm the last documented action against actual repository evidence.
4. Pick the highest-priority unblocked task and proceed without asking the owner to restate the mission.
5. Update this file only with evidence-backed state, and keep plans clearly labelled as plans.

At the end of each meaningful work cycle, add:
- date and branch/commit;
- files changed;
- tests actually executed and exact outcomes;
- links/IDs for relevant runs or artifacts;
- unresolved risks and decisions needed;
- the next precise action.

## 8. Audit checkpoint — 2026-10-29

The first evidence-backed baseline report is saved at:
`docs/OPENFX_AUDIT_BASELINE_2026-10-29.md`
on branch `openfx-mission-state-docs`, commit `09f909f756fbda2afe37b6d96b2f06ebaeb52a0e`.

### Findings established so far
- Main is at `25c1366097c2ddf3a7951111ca9e9a1e6e4928b6`; research/evidence modules introduced by PR #11/#12 are not in main.
- PR #11 and PR #12 are an open dependency chain; PR #13 contains only the mission/state documentation based on main.
- No real MT5 execution adapter, VPS deployment, or independently reproduced trading result is established.
- The nested path `.github/workflows/.github/workflows/.github/workflows/test.yml` is an inactive duplicate candidate because it is not directly under `.github/workflows`.
- Feature-branch source-confirmed claims record a `human_verified` status but do not preserve an auditable reviewer identity/time event.
- JSON syntax checks are not JSON Schema validation; main's experiment schema is looser than the strict feature-branch Python validator.
- Transcript numeric glyph normalization has been implemented on `openfx-audit-round1`, PR #14, with regression tests for Persian/Arabic-Indic digits, percent glyphs, and Unicode signs. Exact-head OpenFX CI run `40924158772` completed successfully: 109 repository tests and 15 worker regression tests passed; JSON syntax validation and worker offline self-test also passed. This does not establish semantic equivalence.

### Actions evidence refreshed
- PR #11: run `40921215811` (OpenFX CI) success; run `40921215571` (CodeQL) success for head `28161cb4622e4bd92ba356508b97409f6149a1af`.
- PR #12: run `40921649710` (OpenFX CI) success for head `649631de5f3a08be1ca0941ede4ff3646b346063`.
- PR #13: runs `40923717266` (OpenFX Unit Tests), `40923717250` (Project Tests), and `40923717315` (CodeQL) success for docs head `9c360866b744ac83b4f8d720019d964f1b0d85b1`.
- PR #14 exact-head check ID `123625086035` completed successfully in run `40924158772`; logs show 109 repository tests and 15 worker tests passed, JSON syntax validation passed, and worker offline self-test passed.

### Audit limitations
The repository could not be cloned in the local execution container because DNS/network access to GitHub was unavailable. This audit checkpoint uses GitHub connector file/branch/PR/Actions evidence and code review. No local test command, real MT5 run, VPS deployment, or trading backtest is claimed.

## 9. Latest continuation point

**Next action:** add executable JSON Schema validation and negative fixtures on a feature branch, then verify schema/Python-validator parity. Continue afterward with auditable human-review events for claims, a labelled transcript adversarial corpus, worker failure/recovery and idempotency, and artifact verification/MT5 pilot acceptance criteria. Review the PR #11/#12 dependency chain and the inactive nested workflow, but do not merge any PR without explicit owner approval.
