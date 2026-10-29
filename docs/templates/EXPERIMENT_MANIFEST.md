# Experiment Manifest

> Copy this file for every baseline test, optimization, validation run, or material rerun. A blank field must be marked `unknown` or `not applicable`, not silently omitted. Do not store credentials or secrets here.

## Identity and claim
- Experiment ID:
- Parent experiment ID:
- Date created (UTC):
- Owner team:
- Strategy / candidate name:
- Research question:
- Preregistered hypothesis:
- Intended decision:
- Primary metric:
- Secondary metrics:
- Minimum trade/sample requirement:
- Acceptance / rejection thresholds:
- Protocol deviations (if any):

## Rule and implementation provenance
- Rule-spec version/path:
- Rule status: user-confirmed / source-supported / engineering choice / unverified hypothesis
- Source references:
- Repository and branch:
- Code commit SHA:
- EA / script version:
- Compile status: not attempted / passed / failed / unknown
- Compile evidence path:
- Unit/synthetic test status and evidence:
- Known defects or unresolved timing/look-ahead concerns:

## Data identity and quality
- Data source / broker:
- Symbol(s):
- Timeframe(s):
- Date range:
- Timezone:
- Data file or dataset ID:
- Data checksum/version:
- Tick/bar model:
- Missing bars / duplicates / OHLC sanity checks:
- Data-quality report:
- Licensing or usage constraints:

## Test design (freeze before optimization)
- Development / training period:
- Validation period:
- Final untouched out-of-sample period:
- Walk-forward windows:
- Baseline configuration:
- Primary optimization objective:
- Secondary constraints:
- Parameter names, ranges and steps:
- Total expected combinations:
- Search algorithm:
- Random seed, if applicable:
- Number of strategies/variants previously tried:
- Rationale for date splits and metrics:

## Execution environment and costs
- MT5 terminal build:
- Strategy Tester build / settings:
- OS / host identifier (no secrets):
- Compute agent type:
- Deposit and account currency:
- Leverage / margin model:
- Spread assumption:
- Commission:
- Swap:
- Slippage / execution delay:
- Other broker constraints:
- User approval reference for paid compute, if applicable:

## Run record
- Run ID:
- Start time (UTC):
- End time (UTC):
- Status: proposed / running / completed / failed / interrupted / not run
- Error messages:
- Recovery/resume details:
- Raw report path:
- Trade-level report path:
- Logs path:
- Artifact hashes:
- Completed combinations / total combinations:
- Resource usage, if measured:

## Results
- Net profit / return:
- Maximum drawdown:
- Trade count:
- Profit factor:
- Expected payoff:
- Exposure / time in market:
- Long vs short breakdown:
- Cost sensitivity:
- OOS result:
- Walk-forward results by window:
- Neighboring-parameter robustness:
- Baseline comparison:
- Important negative results:
- Limitations and confidence:

## Independent validation
- Watchdog report path:
- Verdict: pending / PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE
- Critical findings:
- Major findings:
- Minor findings:
- Reproduction result:
- Required remediation:
- Review date:

## Final disposition
- Decision: reject / revise / continue research / eligible for next approved stage
- Decision rationale:
- What the evidence supports:
- What the evidence does not support:
- Next work item:
- Reviewer / approver:
- Evidence links:

## Integrity checklist
- [ ] Code, data and configuration are uniquely identified.
- [ ] Hypothesis, objective, thresholds and date splits were recorded before optimization.
- [ ] All tested variants and failed runs are retained or linked.
- [ ] Costs and execution assumptions are recorded.
- [ ] No unresolved look-ahead or future-data leakage is hidden.
- [ ] OOS results are not confused with development results.
- [ ] Any unexecuted work is explicitly marked not run.
- [ ] No live-trading readiness or future profitability is implied by a backtest alone.
