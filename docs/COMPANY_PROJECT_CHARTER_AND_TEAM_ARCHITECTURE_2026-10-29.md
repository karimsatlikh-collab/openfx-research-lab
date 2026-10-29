# Company Project Charter and Team Architecture — 2026-10-29

## 1. Project definition

### Proposed company project
Build an **AI-assisted Forex Strategy Research and Validation Platform**. Its main purpose is to discover, formalize, implement, test, optimize, and independently validate trading strategies for the user. It is not a promise of profitability, a live-trading service, or an unrestricted general-purpose AI lab.

The platform has two connected workstreams:
1. **Primary workstream — strategy research and testing:** maintain a pipeline from research hypothesis to precise rules, EA implementation, systematic backtests/optimization, independent validation, and archived decision.
2. **Supporting workstream — source and knowledge acquisition:** find authorized educational videos, transcripts, articles, documentation, datasets, and code repositories; extract useful information with source traceability; verify it before it becomes a strategy rule.

Video collection is an input capability, not the company's final product. A source is not considered a confirmed trading rule merely because an AI system extracted it.

### Success criteria
- Every strategy idea has a source or is explicitly labelled as a hypothesis.
- Rules can be implemented unambiguously and reviewed before coding.
- Every experiment is reproducible from versioned code, data identifiers, settings, and logs.
- Backtests include appropriate costs and realistic data assumptions.
- Development, validation, and final out-of-sample periods are separated.
- Negative results and failed runs are preserved.
- Strategy decisions are based on robust evidence, not the highest historical profit or the largest number of optimization passes.
- The system recovers jobs after process/host failure and exposes health, errors, and resource use.
- No live trading is enabled without a separate explicit decision and risk approval from the user.

## 2. Research lifecycle

1. **Research brief:** define a question, why it matters, expected evidence, and a stop condition.
2. **Source discovery:** identify authorized videos, transcripts, documents, public data, or repositories; record URL, creator, date, access/license notes, and retrieval time.
3. **Extraction and provenance:** retrieve available transcripts/metadata first; use speech-to-text only where needed; preserve source timestamps and the original extracted artifact when permitted.
4. **Extraction quality review:** sample-check omissions, changed numbers/dates, negation errors, and semantic distortion. Uncertain text remains uncertain.
5. **Rule-card drafting:** convert claims into atomic rules with exact conditions, timing, timeframe, exceptions, examples, source citations, and confidence/status: confirmed source rule, unresolved ambiguity, or team hypothesis.
6. **Independent rule review:** resolve contradictions and identify look-ahead risks before coding.
7. **Implementation:** build a versioned EA or research prototype, with unit/synthetic tests and a traceable mapping from rule to code.
8. **Baseline backtest:** run a fixed, documented baseline before parameter optimization.
9. **Optimization:** define parameter ranges and the optimization method in advance; use bounded queues and record every run. Avoid exhaustive search when the parameter space is not tractable.
10. **Independent validation:** use walk-forward and out-of-sample checks, trading costs, data-quality checks, robustness/sensitivity tests, and a review independent of the proposer.
11. **Decision gate:** accept for further research, revise, reject, or mark inconclusive. No automatic promotion to live trading.
12. **Archive and learn:** preserve code revision, data version, configuration, logs, results, reviewer notes, and reason for the decision.

## 3. Functional teams

These are **functional teams/roles in the design**, not a claim that separate autonomous agents are already deployed. Initially, one coordinator and small scripts may cover multiple roles; independent review must remain logically separate from strategy proposal.

### A. President / Product Owner — user
- Sets the mission, priorities, acceptable risk, and final approvals.
- Resolves material strategic ambiguities.
- Approves any paid services, production/live trading, and changes to risk policy.
- Receives concise status reports with evidence, blockers, and decisions required.

### B. Research Director / Orchestrator — ChatGPT-assisted workflow
- Maintains the roadmap, task queue, checkpoints, decision log, and research backlog.
- Assigns tasks to functional teams and chooses the next evidence-based action.
- Separates verified facts from assumptions and proposed work.
- Does not claim a job ran unless logs/artifacts prove it.

### C. Source Discovery and Collection Team
- Finds permitted public sources, official documentation, educational videos, transcripts, datasets, and relevant open-source tools.
- Maintains a source registry and records access, licensing, attribution, and usage restrictions.
- Prefers existing captions/transcripts and reusable tools before custom development.
- Uses rate limits and preserves source identifiers.

### D. Extraction and Knowledge Engineering Team
- Extracts transcript text, timestamps, tables, figures, metadata, and structured claims.
- Measures extraction quality on a test corpus.
- Builds searchable knowledge records and rule cards linked to exact source locations.
- Labels uncertainty and never silently converts an inference into a source-confirmed rule.

### E. Strategy Research Team
- Formulates research questions and trading hypotheses.
- Converts approved source evidence into explicit market-structure, entry, exit, risk, and trade-management specifications.
- Tracks conflicting definitions and unresolved questions.
- Does not choose rules solely because they produce profitable historical results.

### F. Strategy Engineering Team
- Implements rule specifications in MQL5 EAs and/or Python research prototypes.
- Maintains versioned code, unit tests, event-level diagnostics, and reproducible builds.
- Verifies that implementation timing matches the specification and avoids look-ahead.
- Preserves stable baselines and does not overwrite prior versions.

### G. Backtest and Optimization Operations Team
- Maintains the test queue, schedules jobs, controls concurrency, retries recoverable failures, and records completed/failed runs.
- Runs MT5 Strategy Tester jobs and parameter optimization on a compatible Windows test host once provisioned and validated.
- Captures test settings, data range, modeling mode, spread/commission/slippage assumptions, code version, parameter set, run logs, and report artifacts.
- Benchmarks throughput before requesting more compute.
- Does not interpret optimization winners as validated strategies.

### H. Independent Validation / Watchdog Team
- Reviews source fidelity, rule provenance, code-to-rule alignment, data leakage, look-ahead, survivorship/selection bias, overfitting, and test reproducibility.
- Reproduces selected runs independently and challenges optimistic claims.
- Requires out-of-sample, walk-forward, sensitivity, and cost-aware evidence appropriate to the strategy.
- Can veto a research claim or return it for correction.
- Must not be the same logical process that proposed and optimized the strategy without a separate review gate.

### I. Data and Experiment Governance Team
- Maintains source registry, data catalogue, schema/versioning, experiment registry, result database, and artifact retention policy.
- Defines unique run IDs and links code commit, dataset version/hash, configuration, logs, and report.
- Prevents duplicate work where cached results are trustworthy, while ensuring cache keys include all material settings.
- Preserves failed, negative, and superseded results.

### J. Platform / DevOps / Reliability Team
- Maintains GitHub workflows for code review and CI, runtime environment, scheduling, queues, logs, monitoring, alerts, backup, and restart recovery.
- Keeps the coordinator separate from the Windows MT5 test runner where practical.
- Manages access control, secrets, patching, firewall, and recovery procedures.
- Establishes measurable acceptance tests before calling any service persistent or 24/7-ready.

### K. Risk and Research Governance
- Defines pre-registered experiment plans and stop conditions.
- Limits repeated optimization against the same validation set.
- Requires a separate decision for any live trading.
- Records known limitations, rejected approaches, and the evidence behind promotion/rejection decisions.

## 4. Required infrastructure beyond a VPS

### Core components
1. **Source control and change review:** GitHub repository, pull requests or reviewed commits, CI tests, tags/releases, and immutable references to tested code.
2. **Research orchestrator and job queue:** a durable queue/state machine with job IDs, statuses, retry limits, timeouts, idempotency, and restart recovery. Start simply (SQLite-backed ledger and one worker); introduce a separate queue service only if measured concurrency needs it.
3. **Source registry and knowledge store:** URLs, source metadata, timestamps, rights/usage notes, transcript/rule records, and provenance links.
4. **Raw and processed artifact storage:** keep large audio/video, market data, and full reports out of Git history; use a structured data directory or separate storage with hashes, retention rules, and backups.
5. **Market-data layer:** broker/source inventory, symbol specifications, timezone/session handling, missing/duplicate/outlier checks, and clear distinctions between bar, tick, and real-tick data.
6. **Windows MT5 test runner:** supported Windows environment with MT5 terminal, Strategy Tester, historical data, EA versions, local agents, report export, and reboot/recovery checks. Do not assume Linux/Wine is production-compatible without testing.
7. **Experiment registry/results database:** track strategy version, parameter grid, run ID, instrument, timeframe, dates, modeling mode, costs, status, metrics, and artifact locations.
8. **Monitoring and alerting:** scheduler heartbeat, missed/failed jobs, CPU/RAM/disk, storage growth, MT5/terminal state, queue age, and last successful test.
9. **Security and access controls:** least privilege, secrets outside Git, SSH/RDP hardening, firewall, updates, audit trail, and controlled access to proprietary strategies/data.
10. **Backup and disaster recovery:** backup the database, configs, source manifests, EA versions, and important reports; test restoration rather than merely enabling backup.
11. **Research quality harness:** small gold-standard transcript corpus, rule-extraction checks, synthetic price/event tests, Python-versus-MQL5 comparison where applicable, and regression tests.
12. **Human approval interface:** concise reports showing what ran, what failed, what changed, evidence quality, and which decisions require the user's approval.

### Optional components to defer until evidence requires them
- PostgreSQL instead of SQLite for genuinely concurrent writers or larger workloads.
- Object storage or a dedicated data volume for growing video/tick archives.
- External speech-to-text or AI APIs after quality and cost are measured.
- Separate Linux coordinator and Windows backtest host if combining them causes reliability or security issues.
- MQL5 Cloud Network or remote agents for bounded, explicitly approved bursts of optimization.
- Local LLM/GPU infrastructure only if measured workloads justify it.
- Dashboard or message queue service only after logs and basic reports are adequate.

## 5. MT5 optimization design notes
The official MT5 Strategy Tester supports multithreaded optimization with local agents, remote agents, and the MQL5 Cloud Network. Optimization may use complete search or a genetic algorithm. These options have different completeness, speed, and cost properties; they are not interchangeable. Every run must preserve its settings and be reproducible. Cloud compute is an optional paid dependency and must not be activated without separate approval.

## 6. Decision rights and hand-offs
- Source team hands off source-indexed artifacts, not untraceable summaries.
- Extraction team hands off quality-checked transcript/claim records, not assumed trading rules.
- Strategy research hands off approved rule cards with ambiguity status.
- Engineering hands off code revision, tests, and known implementation limits.
- Backtest operations hands off raw run artifacts and metadata, not a profitability verdict.
- Independent validation hands off a review with reproduced evidence, failure cases, and a clear accept/reject/inconclusive recommendation.
- Research Director consolidates the evidence and presents decisions to the user.
- Only the user approves paid add-ons, live trading, and material changes in risk tolerance.

## 7. Implementation order
### Phase 0 — scope and audit
- Treat the current repository as a specification/skeleton, not an operational company.
- Audit code, workflows, dependency declarations, existing documents, and available tests.
- Freeze a minimal project charter and define terms and artifact schemas.

### Phase 1 — reliable research control plane
- Add source registry, experiment/run schema, durable queue ledger, structured logs, failure records, and health report.
- Implement one harmless scheduled job and restart/recovery tests.
- Add CI checks and preserve artifacts.

### Phase 2 — source and extraction pilot
- Use a small authorized source set.
- Prefer existing captions/transcripts; evaluate extraction tools on a labelled sample.
- Measure transcript and claim-extraction errors before scaling.

### Phase 3 — MT5 test-runner proof of concept
- Verify supported Windows/MT5 compatibility and unattended execution.
- Run a fixed baseline EA test, export report, restart the host/process, and reproduce the same run.
- Add job queue integration only after the manual smoke test succeeds.

### Phase 4 — optimization and validation
- Define bounded parameter grids and benchmark passes per hour.
- Add development/validation/final out-of-sample splits, costs, robustness tests, and independent review.
- Use external agents/cloud only after measuring the bottleneck and obtaining approval.

### Phase 5 — scale based on evidence
- Increase concurrency, storage, models, and source coverage only when measured throughput or quality requires it.
- Run a continuous reliability soak test before any 24/7 claim.

## 8. Current status
This document defines the proposed project and roles; it does not mean that these teams are staffed as separate agents or that the infrastructure/pipelines are implemented. The repository currently contains an initial Python entry point and project documentation. No server is confirmed purchased or deployed, and no MT5 server installation/backtest is confirmed.

## 9. Immediate next action
Audit the existing repository and turn this charter into a prioritized implementation backlog. The first implementation target should be the research control plane (source registry + experiment/run records + durable queue + logs/recovery), while the Windows MT5 compatibility review proceeds as a separate validation track. Do not conduct a financial/vendor selection exercise unless the user reopens it.


## 11. GitHub ecosystem research and collaboration mandate — user instruction (2026-10-29)

The Source Discovery and Collection Team is explicitly tasked with treating relevant GitHub users, repositories, and open-source projects that develop Forex/trading strategies, indicators, EAs, backtesting frameworks, market-data tools, or research workflows as target research sources and potential collaboration partners—not merely as software dependencies.

Required activities:
- Discover and catalogue relevant public GitHub repositories, authors/maintainers, issues, pull requests, releases, tests, documentation, strategy specifications, backtest methodology, and published results.
- Extract reusable research knowledge: explicit rules, implementation patterns, bug reports, failed approaches, limitations, test fixtures, performance claims, and reproducibility evidence. Record repository URL, commit/release SHA, retrieval date, license, provenance, and confidence.
- Separate source facts, author claims, measured/reproduced findings, and our own hypotheses. A repository's star count, README claim, screenshot, or single backtest is not evidence of profitability by itself.
- Where appropriate, participate constructively: report reproducible bugs, ask focused technical questions, propose tests, improve documentation, or submit code/documentation contributions.
- Before contributing, inspect the repository's license, contribution guide, code of conduct, security policy, and maintainer expectations. Respect attribution and license obligations; do not copy code into proprietary components unless the license and intended use permit it. Do not publish the user's private strategy rules, credentials, private data, or company-internal results.
- Do not create noisy issues/PRs or claim affiliation. Contributions must be relevant, evidence-backed, and reviewed before submission. Public issue/PR submission on behalf of the user requires user approval when it discloses proprietary methods, makes a commitment, or materially represents the company.
- Preserve useful negative findings and abandoned/failed approaches when their evidence can be checked. Track upstream project status and avoid relying on abandoned or unsafe dependencies without review.

This is a standing project instruction from the user. It does not authorize paid services, private-repository access, live trading, or disclosure of confidential information.
