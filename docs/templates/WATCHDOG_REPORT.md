# Independent Validation / Watchdog Report

- Review ID:
- Date (UTC):
- Reviewer role:
- Candidate / strategy version:
- Experiment ID(s):
- Code commit SHA:
- Data version / checksum:
- Review mode: frozen-artifact review / independent rerun / partial review
- Conflict of interest or shared authorship disclosure:

## Verdict
Choose exactly one:
- [ ] PASS
- [ ] CONDITIONAL PASS
- [ ] FAIL
- [ ] INSUFFICIENT EVIDENCE

A PASS permits only the named next research stage. It does not guarantee future profitability and is not authorization for live trading.

## Scope and evidence received
- Rule specification:
- Code and compile evidence:
- Dataset and quality report:
- Baseline report:
- Full optimization results (including failed/abandoned runs):
- Parameter search space and trial count:
- OOS / walk-forward design:
- Cost assumptions:
- Trade-level logs:
- Missing artifacts:

## Findings
For each finding include severity, evidence, impact, remedy and retest required.

### Critical
- Finding / evidence / remedy:

### Major
- Finding / evidence / remedy:

### Minor
- Finding / evidence / remedy:

## Challenge checklist
### Implementation and timing
- [ ] No future-bar leakage identified, or issue is documented.
- [ ] Pivot/signal confirmation is timestamped when it becomes knowable.
- [ ] Closed-bar assumptions are consistent.
- [ ] Entry, exit, stop, target, costs and execution timing are modeled.
- [ ] Boundary and failure cases are tested.

### Data and reproducibility
- [ ] Symbol, timeframe, timezone, date range and data version are identifiable.
- [ ] Data quality and missing bars are checked.
- [ ] Exact run can be reconstructed from code, data and configuration.
- [ ] Report metrics match the underlying logs.

### Overfitting and robustness
- [ ] All variants/trials are accounted for.
- [ ] Development, validation and untouched final OOS periods are separated.
- [ ] Nearby parameter values and cost sensitivity are examined.
- [ ] Trade count, drawdown, distribution and return concentration are reviewed.
- [ ] Walk-forward windows and negative results are reported.

### Scope and governance
- [ ] No claim exceeds the evidence.
- [ ] No critical finding remains open for a positive verdict.
- [ ] Paid services and live-trading actions remain subject to explicit approval.

## Independent reproduction
- Re-run attempted? yes / no
- Environment and exact configuration:
- Result compared:
- Differences:
- Limitations if no rerun was possible:

## Required remedies and re-review
- Finding:
- Owner team:
- Acceptance test:
- Evidence required:
- Re-review trigger:

## Final scope statement
- What is supported by this review:
- What is not supported:
- Permitted next research stage:
- Prohibited inference or action:
