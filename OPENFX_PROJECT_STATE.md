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

The evolving evidence-backed baseline report is saved at:
`docs/OPENFX_AUDIT_BASELINE_2026-10-29.md`
on branch `openfx-mission-state-docs`, latest report commit `166a80cce48793acdc852d1701170c56508667bd`.

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

### Additional audit branches and verified fixes
- PR #14 `openfx-audit-round1` (base `openfx-transcript-adversarial-checks`): normalizes equivalent Persian/Arabic-Indic digits and common percent/sign glyphs. CI run `40924158772` passed: 109 repository tests and 15 worker tests.
- PR #15 `openfx-schema-validation` (base `openfx-audit-round1`): adds pinned JSON Schema validation and fixtures. CI run `40924445011` passed: 8 dedicated schema tests, 117 repository tests, 15 worker tests.
- PR #16 `openfx-transcript-import-strictness` (base `openfx-audit-round1`): rejects malformed subtitle blocks without timestamps and distinguishes valid cue IDs such as `NOTE`/`STYLE` from metadata. Exact-head CI run `40925335092` passed: 112 repository tests and 15 worker tests. An intermediate failed run `40925250131` exposed the cue-ID bug; it was corrected and the failure remains in GitHub history.
- PR #17 `openfx-rights-gate` (base `openfx-audit-round1`): blocks transcript import unless rights are `reviewed_permitted` or `public_domain` with a reference. After correcting a CLI fixture that still relied on unknown rights, exact-head CI run `40924903871` passed: 111 repository tests and 15 worker tests.
- PR #18 `openfx-local-scan-boundary` (base `main`): skips symlinks and records root-relative paths to disambiguate same-named files. Current-head Project Tests `40925208557`, OpenFX Unit Tests `40925208133`, and CodeQL `40925208196` all passed.
- PR #19 `openfx-ci-least-privilege` (base `main`): adds `contents: read` permissions and five-minute timeouts to the two baseline test workflows. Test runs `40925003750` and `40925003699`, CodeQL `40925003707`, and Gemini review `40925001639` all passed.
- PR #20 `openfx-transcript-critical-conditions` (base `openfx-audit-round1`): adds condition/unit markers and a 24-case synthetic labelled transcript corpus with a confusion-matrix script. Exact-head CI run `40925975774` passed: 115 repository tests, 15 worker tests, and corpus evaluation. Curated matrix TP=18, FN=0, FP=0, TN=6; these 24 hand-selected synthetic cases do not estimate real-world transcript accuracy. Intermediate run `40925884008` failed because the evaluator script lacked the repository root on `sys.path`; fixed in the current head and preserved in history.
- PR #21 `openfx-youtube-key-header` (base `openfx-audit-fixes`): moves the YouTube Data API key from the query string to the `X-Goog-Api-Key` header. Exact-head CI run `40926204432` passed: 104 repository tests and 15 worker tests.
- PR #22 `openfx-result-assertion-labels` (base `openfx-audit-round1`): labels report parsing as CLI-verified only after artifact/report/metric checks, while journal/data/cost/split flags are explicitly marked as declarations not independently verified. Exact-head CI run `40926577896` passed: 109 repository tests and 15 worker tests.
- PR dependency caution: #14 follows #12; #15, #16, #17, and #20 are based on #14's branch; #21 is based on #11. PRs #16 and #17 touch the same transcript-import files and may conflict when sequenced even though each is currently mergeable against its own base.
- None of PRs #14–#22 has been merged by this work.

### Audit limitations
The repository could not be cloned in the local execution container because DNS/network access to GitHub was unavailable. This audit checkpoint uses GitHub connector file/branch/PR/Actions evidence and code review. No local test command, real MT5 run, VPS deployment, or trading backtest is claimed.

## 9. Latest continuation point

**Next action:** refresh current head CI and mergeability of PRs #14–#22, including the latest docs PR checks for head `a9d4a8093fcda7e4803319678d6f88333bbafe7a`. The 24-case synthetic transcript corpus is in PR #20; expand it with independently labelled real-world examples and measure error rates. Then address auditable human-review events, raw transcript artifact provenance, confidence-field semantics, further evidence-specific verification for journal/data/cost/splits, worker failure/recovery and idempotency, artifact verification/MT5 pilot acceptance criteria, and auto-report artifact retention. Review whether to consolidate duplicate workflows. Do not merge any PR without explicit owner approval. Review the PR #11/#12 dependency chain and the inactive nested workflow, but do not merge any PR without explicit owner approval.
