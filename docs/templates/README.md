# Operational templates

These templates provide the minimum paper trail for the AI-assisted Forex Strategy Research and Validation Platform. They are templates only; creating them does not mean an experiment or service has run.

## Templates
- [Research Work Item issue form](../../.github/ISSUE_TEMPLATE/01-research-work-item.yml): creates structured, actionable work requests in GitHub Issues.
- [Experiment Manifest](EXPERIMENT_MANIFEST.md): one per baseline, optimization, validation run, or material rerun.
- [Decision Record](DECISION_RECORD.md): records material choices, alternatives, evidence, uncertainty, and approval boundaries.
- [Watchdog Report](WATCHDOG_REPORT.md): independent challenge checklist and verdict.
- [Pull Request Template](../../.github/pull_request_template.md): evidence, research-integrity, and approval checks for repository changes.

## Operating rules
1. Every task must have an owner, inputs, outputs, acceptance criteria, dependencies, and evidence.
2. Every experiment must identify the exact code version, data version, configuration, costs, and test periods.
3. Record failures and negative results; do not retain only the best optimization result.
4. Distinguish proposed, implemented, executed, tested, and independently validated states.
5. A missing artifact means INSUFFICIENT EVIDENCE, not success.
6. Do not authorize paid APIs, cloud compute, MQL5 Cloud Network, purchases, or live trading without explicit user approval.
7. The user remains the final decision-maker. Financial/vendor comparison remains out of scope unless reopened.

## Current implementation status
- The files in this directory and the GitHub issue/PR templates have been committed and read back for basic content verification.
- The templates have not yet been exercised through a submitted GitHub issue or pull request.
- No orchestration service, queue, MT5 runner, continuous backtest, or independent deployed agent is claimed to be operational.
