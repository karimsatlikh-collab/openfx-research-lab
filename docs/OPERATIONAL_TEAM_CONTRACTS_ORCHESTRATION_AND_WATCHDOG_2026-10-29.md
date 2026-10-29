# Operational Team Contracts: Central Research Orchestration and Independent Validation
Date: 2026-10-29
Status: DESIGN SPECIFICATION — not deployed or operationally staffed
Repository: karimsatlikh-collab/video-research-team

## 1. Purpose and boundaries

This document turns two critical functions into operationally testable contracts:
1. Central Research Orchestration (the control tower).
2. Independent Validation / Research Watchdog (the challenge function).

They are functional roles, not claims that separate autonomous agents have been deployed. The assistant may coordinate work and use available tools, but every action must be reported according to evidence. A proposed action, a tool call, a successful file write, a code compile, and a completed MT5 backtest are different states and must never be conflated.

The company project is an AI-assisted Forex Strategy Research and Validation Platform. The objective is repeatable evidence-based discovery and rejection of strategies, not a guarantee of profitability or permission for live trading.

## 2. Shared work-item contract

Every non-trivial task must be represented by a durable work item with these fields:
- work_id: unique immutable identifier.
- title and question: what decision or uncertainty is being addressed.
- owner_team and requesting_team.
- status: proposed, ready, running, blocked, failed, completed, rejected, archived.
- priority and risk_class: low, medium, high, critical.
- inputs: paths, dataset IDs, source IDs, code commit, configuration IDs.
- expected_outputs: concrete files, reports, measurements, or decision.
- acceptance_tests: explicit pass/fail criteria before work starts.
- assumptions: each tagged as user-confirmed, source-supported, engineering choice, or unverified hypothesis.
- dependencies and handoff_target.
- budget/resource approval: required if work can incur paid usage or external charges.
- created_at, updated_at, started_at, finished_at when available.
- evidence: commit SHA, logs, report path, test output, or source citation.
- limitations and known failures.
- decision: accept, reject, revise, or defer, with reason.

A task cannot be marked completed solely because code was written or a document was drafted. Completion means its stated acceptance tests have evidence. If no execution environment is available, mark it as designed, implemented-but-unexecuted, or blocked—not tested.

## 3. Team A — Central Research Orchestration

### Mission
Convert the company research objective into an ordered, traceable queue of small tasks; coordinate handoffs; prevent contradictory rules and unverified claims; preserve decision history; and make sure scarce compute is spent only on research questions that passed basic quality gates.

### Inputs
- User-approved research brief and constraints.
- Strategy rule cards and source records.
- Code repository and version history.
- Dataset registry, data-quality reports, and date ranges.
- Backtest/optimization results with configuration IDs.
- Watchdog findings, unresolved objections, and prior failed attempts.
- Infrastructure status and explicit resource/cost approvals.

### Outputs
1. A ranked work queue with owners, dependencies, and acceptance criteria.
2. A short research decision record for every material decision.
3. A traceable experiment plan linking hypothesis → implementation commit → data version → configuration → run → validation result.
4. An exception list: blocked tasks, missing evidence, conflicting rules, stale inputs, failed jobs, and decisions requiring the user.
5. A checkpoint file after meaningful milestones, with exact state and next action.
6. A final disposition per strategy: reject, revise, continue testing, or eligible for a separately authorized next-stage review.

### Authority and decision rights
The orchestrator may:
- Break approved goals into tasks and sequence them.
- Request clarification when a material ambiguity changes the test.
- Reject incomplete submissions from a handoff and return them with explicit missing items.
- Pause a pipeline when data integrity, leakage, reproducibility, or safety controls fail.
- Select low-risk, reversible engineering defaults when documented as such.
- Preserve negative results and avoid rerunning identical work without a reason.

The orchestrator may NOT:
- Change user-confirmed strategy rules silently.
- Convert a hypothesis into a confirmed rule without evidence/review.
- Claim that code compiled, a test ran, a server was deployed, or a video was extracted without execution evidence.
- Authorize paid APIs, cloud compute, MQL5 Cloud Network, purchases, live trading, or irreversible actions without explicit user approval.
- Override the independent watchdog's failed gate merely to produce a positive result.
- Use profit alone as a final acceptance criterion.

### Workflow
1. Intake: restate the question and intended decision; verify it belongs to the project.
2. Triage: classify as source research, data, rule formalization, engineering, test operations, validation, or infrastructure.
3. Evidence audit: inspect existing artifacts and prior attempts before creating duplicate work.
4. Plan: define one hypothesis or question per work item; inputs, outputs, dependencies, cost/risk, acceptance tests.
5. Gate: check source provenance, data quality, implementation readiness, and whether the work is eligible for compute.
6. Dispatch: assign a functional team and record the exact handoff package.
7. Monitor: capture progress, failure state, logs and resumability; never infer success from silence.
8. Review: obtain independent validation where required.
9. Decision: accept/reject/revise/defer with evidence and limitations.
10. Archive/checkpoint: preserve code, config, data identity, results, negative outcomes and next action.

### Required quality gates before expensive optimization
- Strategy rules are sufficiently explicit to code without hidden discretionary interpretation.
- Implementation has a versioned commit and relevant unit/synthetic tests.
- No known look-ahead, future-bar leakage, or pivot-confirmation timing error remains unresolved.
- Market data source, symbol, timeframe, date range, timezone, spread/commission assumptions and missing-data checks are recorded.
- A baseline test exists or the reason it cannot yet exist is documented.
- Development, validation and untouched final out-of-sample periods are defined before parameter search.
- Optimization objective and minimum trade/sample requirements are preregistered.
- Search size and compute budget are estimated; paid resources require explicit approval.
- The watchdog has a defined review point and can reject the experiment design.

If a gate fails, return to the responsible team. Do not run a large optimization merely because the infrastructure is available.

### Performance indicators
- Percentage of tasks with complete provenance and acceptance criteria.
- Percentage of completed tasks with reproducible evidence.
- Number of duplicate runs avoided through artifact/config reuse.
- Rate of preventable handoff failures and repeated defects.
- Time from question to a defensible decision, not simply time to a positive backtest.
- Percentage of material decisions with rationale and status of uncertainty recorded.
- Number of unsupported claims detected; target is zero.
- Percentage of failed/negative experiments retained with enough detail to learn from them.

### Escalation rules
Escalate to the user when:
- Two plausible interpretations would produce materially different strategy behavior.
- A confirmed user rule conflicts with source evidence or an older rule.
- A paid resource, purchase, external account, or live-trading action is proposed.
- Data rights, privacy, security, or broker/platform terms are uncertain.
- The watchdog disputes a high-impact result and the disagreement cannot be resolved from evidence.
- The project is about to change a baseline, discard a result, or alter a preregistered validation plan.

### Failure modes and recovery
- Missing input: mark blocked; ask only for the missing decision/data; preserve completed work.
- Conflicting rule cards: freeze implementation; identify provenance and conflict; ask user if evidence cannot resolve it.
- Tool/API failure: record tool/action, failure output and retry limit; do not pretend completion.
- Long-running job interruption: resume only from documented checkpoints/results; verify which runs actually completed.
- Result without config/data identity: quarantine as non-reproducible; do not use it to select a strategy.
- Orchestrator bias: require watchdog review and report both positive and negative evidence.

## 4. Team B — Independent Validation / Research Watchdog

### Mission
Act as an adversarial reviewer, not as a second promoter of the strategy. Its job is to find reasons a promising result may be false, overfit, contaminated, irreproducible, or too fragile to trust. It should be organizationally separate from strategy authorship and parameter optimization. If the same AI system assists both roles, independence must be approximated through a separate review brief, frozen evidence, explicit challenge checklist, and no editing of the strategy during the review.

### Inputs
- Frozen research brief and preregistered hypothesis.
- Versioned EA/source code and compile logs, if actually produced.
- Immutable dataset identity, data-quality report, and market-data provenance.
- Baseline test report and all optimization results—not only the best run.
- Full parameter ranges, search method, optimization objective, random seeds where relevant, and number of trials.
- Development/validation/final OOS date splits and reason for selection.
- Costs: spread, commission, swaps where relevant, slippage and delay assumptions.
- Trade-level logs and metrics sufficient to reproduce headline figures.
- Known limitations, failed runs, and any prior strategy changes.

### Outputs
1. A written validation verdict: PASS, CONDITIONAL PASS, FAIL, or INSUFFICIENT EVIDENCE.
2. A list of critical, major and minor findings, each with evidence and a required remedy.
3. Leakage/look-ahead audit.
4. Reproducibility check comparing an independently rerun result or a clearly stated limitation if rerun is unavailable.
5. Robustness assessment across out-of-sample periods, nearby parameter values, cost assumptions and relevant market regimes.
6. A report of search/selection bias risks, including how many variants were tried and whether failed trials were retained.
7. An explicit statement of what the evidence does and does not justify.
8. A release recommendation for the next research stage only; never automatic live-trading approval.

### Independence rules
- The watchdog must not receive only a curated best-result screenshot; it needs the experiment record and relevant full result set.
- The strategy author cannot delete failed runs or change the preregistered objective after seeing results without recording a protocol deviation.
- The watchdog should first review frozen artifacts; changes requested afterward create a new version and require re-review.
- A watchdog finding cannot be marked resolved by changing its status alone; attach evidence of the fix and rerun the relevant check.
- If the watchdog also authored the strategy or selected the parameters, disclose the conflict and use an additional independent review when feasible.
- No final positive verdict is allowed if a critical finding remains open.

### Mandatory challenge checklist

#### A. Implementation correctness
- Are signals evaluated only with information available at the decision time?
- Are pivots and other delayed-confirmation structures timestamped at the time they become knowable, not backdated to their visual turning point?
- Are current-bar values used where a closed bar is required?
- Are order fill, stop-loss, take-profit, spread, commission, swaps, slippage and execution timing modeled consistently?
- Are duplicate entries, position sizing, stop distance, invalid prices and broker constraints handled?
- Do synthetic/unit tests cover boundary cases, missing bars, gaps, simultaneous signal/exit conditions and state resets?
- Does a trade-by-trade comparison agree between the reference implementation and MQL5 where cross-platform logic exists?

#### B. Data integrity
- Are symbol, broker/source, timeframe, timezone, date range and data version recorded?
- Are missing bars, duplicates, impossible OHLC values, time gaps and daylight-saving transitions checked?
- Did the test accidentally use a future data revision or an unavailable symbol/session?
- Are spreads and costs representative, and are results still plausible under less favorable assumptions?

#### C. Statistical validity and overfitting
- Were the hypothesis, metric, constraints and split dates specified before optimization?
- How many combinations, strategies and variants were tried, including abandoned attempts?
- Is the best result an isolated peak surrounded by poor neighboring parameter values?
- Is the sample/trade count adequate for the claim being made?
- Are results stable across more than one time segment and market regime?
- Are multiple-comparison and selection effects acknowledged?
- Does performance persist on untouched final OOS data, not merely the platform's optimization-forward subset?
- Is walk-forward performance reported as a sequence, not only as an aggregate?
- Are drawdown, exposure, tail losses, trade distribution and return concentration reported alongside net profit?
- Is there a benchmark or simple baseline to show the method adds value?

#### D. Reproducibility and reporting
- Can another reviewer reconstruct the exact run from commit, data version and configuration?
- Are all optimization results and failures preserved?
- Do headline metrics match the underlying report/trade log?
- Are rounding, currency, point/pip conversion and time-zone choices correct?
- Are caveats and negative results visible in the executive summary?

#### E. Scope and deployment
- Does the evidence support only historical research, or also paper/demo forward testing? State the boundary.
- Is any claim of live readiness explicitly excluded unless a separate approval process is completed?
- Are secrets, account credentials and personal data absent from repository logs and artifacts?
- Are compute and external-service charges within the user-approved boundary?

### Verdict definitions
- PASS: all critical and major checks have adequate evidence; no unresolved critical/major issue invalidates the stated claim. PASS means the research claim may proceed to the next approved stage, not that future profitability is guaranteed.
- CONDITIONAL PASS: no known fatal defect, but specific non-critical limitations or required follow-up checks remain; the next stage is limited and explicitly named.
- FAIL: a critical defect, material leakage, irreproducible result, invalid test design, or evidence that contradicts the claim.
- INSUFFICIENT EVIDENCE: required artifacts are absent or cannot be independently checked. This is not a pass and must not be described as a successful validation.

### Severity levels
- Critical: invalidates the result or creates a material safety/security risk; stop downstream promotion.
- Major: could materially change the conclusion; fix and re-run before a positive verdict.
- Minor: documentation or limited defect not expected to change the central conclusion; record and schedule remediation.

### Performance indicators
- Percentage of critical/major findings resolved with evidence.
- Number of false positives caught before large optimization or strategy promotion.
- Reproduction success rate for selected results.
- Share of candidate strategies tested on untouched final OOS data.
- Rate of reports with complete experiment lineage and all-trials accounting.
- Number of critical issues bypassed without authorization; target is zero.
- Turnaround time for review, balanced against review completeness—not minimized at the expense of rigor.

## 5. Handoff contracts between teams

### Orchestrator → Source Discovery / Extraction
Must provide: precise question, allowed sources, required provenance, output format, licensing/privacy constraints, and stopping condition.
Return if: source identity is absent, extraction is incomplete, or rights/quality are unclear.

### Extraction / Knowledge Engineering → Strategy Research
Must provide: source-linked rule cards, exact quote/segment references where available, confidence/ambiguity, and separate tags for confirmed statements versus interpretation.
Return if: source attribution is missing or a hypothesis is presented as a source-confirmed rule.

### Strategy Research → Strategy Engineering
Must provide: deterministic rule specification, event timing, inputs/timeframes, entry/exit/invalidity conditions, examples and counterexamples, unresolved questions, and acceptance tests.
Return if: two competent implementers could code materially different behavior from the same spec.

### Strategy Engineering → Backtest Operations
Must provide: versioned code commit, compile evidence if compiled, unit/synthetic test results, parameters, known defects, and expected event/log format.
Return if: code version or testable inputs are missing, or a known look-ahead issue is unresolved.

### Backtest Operations → Watchdog
Must provide: immutable run ID, exact code/data/config identities, full reports and all optimization outcomes, costs, logs, splits and failure records.
Return if: only a screenshot or selected top result is supplied, or the run cannot be reconstructed.

### Watchdog → Orchestrator
Must provide: verdict, severity-ranked findings, supporting evidence, remedy, and exact scope of any permitted next step.
Return if: finding is opinion-only without a testable reason; otherwise record disagreement and seek an additional review rather than silently overriding it.

### Orchestrator → User
Must provide concise decision options, evidence, uncertainties, risks, any requested approval, and a recommendation. No hidden commitment to paid services or live trading.

## 6. Experiment state machine

A candidate strategy progresses through these states:
1. IDEA — question exists, not yet evidence-backed.
2. SPECIFIED — rules and hypotheses are separated and acceptance criteria exist.
3. IMPLEMENTED — versioned implementation exists; execution status is separately recorded.
4. BASELINE_TESTED — at least one documented baseline run has evidence.
5. OPTIMIZATION_READY — all pre-optimization gates pass.
6. OPTIMIZED — search completed or deliberately stopped; all trials and configuration recorded.
7. VALIDATION_PENDING — frozen candidate and evidence handed to watchdog.
8. VALIDATED / REJECTED / INSUFFICIENT_EVIDENCE — watchdog verdict recorded.
9. DEMO_FORWARD_REVIEW — only after explicit approval and a separate plan.
10. LIVE-READINESS REVIEW — separate governance process; never automatic.

A strategy may move backward when a defect is found. Every state transition must record who/which role made it, when, why, and evidence. No transition is implied by elapsed time.

## 7. Minimum experiment manifest

Every baseline or optimization experiment should store:
- experiment_id and parent_experiment_id;
- hypothesis and preregistered primary/secondary metrics;
- strategy version/commit SHA and rule-spec version;
- data source, symbol(s), timeframe(s), timezone, date range, data checksum/version;
- train/development, validation, final OOS, and walk-forward windows;
- tester version/build, broker/account model, tick model, deposit, leverage, costs and execution-delay settings;
- full parameter ranges, steps, total combination count, optimization algorithm, random seed if applicable;
- run start/end, completion status, errors, and compute-agent type;
- full output reports, trade-level data when available, logs and hashes;
- all deviations from plan and reason;
- watchdog verdict and unresolved findings;
- final decision and explicit scope of claim.

## 8. Initial implementation backlog

Priority 0 — repository governance:
- [ ] Add work-item template and experiment-manifest template.
- [ ] Add decision-record and watchdog-report templates.
- [ ] Define statuses and severity labels in one shared document.
- [ ] Audit existing scripts and workflows; do not mistake current skeletons/CI for a working research pipeline.

Priority 1 — minimal traceability:
- [ ] Use GitHub issues or equivalent as the initial queue.
- [ ] Require a manifest for every experiment.
- [ ] Store result summaries and links to immutable artifacts.
- [ ] Create a simple validation checklist and require a verdict before promotion.

Priority 2 — execution proof:
- [ ] Independently establish whether the chosen Windows VPS can run MT5 Strategy Tester reliably.
- [ ] Install MT5 only after that compatibility check and the user's approval of the environment.
- [ ] Run one small known EA test and one small optimization as proof of concept.
- [ ] Record logs, exact configuration, recovery behavior, CPU/RAM/disk use and whether the job survives disconnect/reboot.
- [ ] Do not call this 24/7-ready until a sustained soak test and recovery test pass.

Priority 3 — scale only after evidence:
- [ ] Add queued unattended runs and retry/resume semantics.
- [ ] Add alerts, retention, backups and periodic restore tests.
- [ ] Evaluate remote agents only after the single-host baseline is reliable.
- [ ] Do not enable paid MQL5 Cloud Network or paid external APIs without explicit user approval.

## 9. Acceptance tests for this design

This design is accepted as implemented in the repository only when:
- This document exists in the default branch and is readable from GitHub.
- The roles, decision rights, gates, handoffs, verdicts and backlog are explicitly documented.
- It states that the roles are design roles, not deployed independent agents.
- It does not claim that MT5, a VPS, video extraction or 24/7 automation has been executed.
- It does not authorize spending or live trading.

These checks verify the document only. They do not prove that any operational system has been deployed.

## 10. Explicit constraints
- The user is the final decision-maker.
- Financial/vendor comparison is out of scope unless the user reopens it.
- No paid API, compute service, MQL5 Cloud Network, purchase, or live trading without explicit approval.
- Preserve failed experiments and prior versions.
- Keep source-supported rules separate from engineering hypotheses.
- Treat every backtest as evidence with limitations, not proof of future profitability.
- Current status: specification only; operational deployment and MT5 execution remain unverified.
