# Process Smoke Test — Operational Templates
Date: 2026-10-29
Status: PARTIAL PASS — repository/API checks passed; GitHub UI rendering not yet verified
Related work item: https://github.com/karimsatlikh-collab/video-research-team/issues/1

## 1. Scope
This is a process-only smoke test of repository artifacts and issue tracking. It is not a market experiment and does not involve MT5, EA compilation, strategy backtesting, server deployment, video extraction, or 24/7 execution.

## 2. Actions actually completed
- Read back the work-item issue form from the default branch.
- Checked that the form contains required top-level fields (name, description, body), input fields, acceptance criteria, and safeguards.
- Removed a default label dependency from the form so an unconfigured label cannot block form creation.
- Read back the experiment manifest, decision record, watchdog report, templates README, and pull request template.
- Checked that the manifest includes experiment identity, data checksum/version, untouched OOS period, parameter-combination count, and validation section.
- Checked that the decision record includes options, evidence, approval boundaries, and audit information.
- Checked that the watchdog report includes verdicts, OOS/robustness checks, and critical/major/minor findings.
- Created GitHub issue #1 as the durable tracking item through the GitHub connector API.

## 3. Evidence table

| Check | Result | Evidence / limitation |
|---|---|---|
| Issue form file exists and is readable | PASS | .github/ISSUE_TEMPLATE/01-research-work-item.yml was fetched back from GitHub |
| Required issue-form top-level keys present | PASS (content check only) | name, description, body were present; this is not a GitHub-renderer validation |
| Form does not require a default label | PASS | No labels field is configured in the issue form |
| Experiment manifest has key reproducibility fields | PASS (content check) | docs/templates/EXPERIMENT_MANIFEST.md |
| Decision record includes alternatives and approvals | PASS (content check) | docs/templates/DECISION_RECORD.md |
| Watchdog report includes verdict and robustness sections | PASS (content check) | docs/templates/WATCHDOG_REPORT.md |
| GitHub issue tracking API works for this task | PASS | Issue #1 created and returned by GitHub |
| Issue form renders in the browser's New Issue chooser | NOT VERIFIED | Must be checked in the GitHub web UI |
| Issue can be submitted via the rendered form | NOT VERIFIED | No issue was submitted through the actual UI form in this test |
| YAML schema accepted by GitHub renderer | NOT VERIFIED | File readback/content inspection is not the same as rendering |
| MT5, compile, backtest, VPS or continuous automation | NOT RUN | Explicitly outside the scope of this process test |

## 4. Process-only experiment manifest

- Experiment ID: EXP-PROCESS-001
- Parent experiment ID: none
- Research question: Are the core operational template files present and do they contain the expected sections?
- Hypothesis: The files are available in the default branch and have the required documented fields.
- Primary metric: Presence of required template sections.
- Strategy / EA: not applicable
- Code commit / EA version: not applicable
- Market data / symbol / timeframe: not applicable
- Test period: 2026-10-29 repository state
- Test status: completed for repository readback/content checks; partial overall
- Run identity: GitHub connector readback and content checks
- Result: the expected files were readable and key sections were found
- Failure/limitation: actual GitHub UI rendering/submission remains unverified
- Watchdog verdict: INSUFFICIENT EVIDENCE for rendered-form validity; PARTIAL PASS for repository artifact/content checks
- Final disposition: continue to UI verification; do not yet claim the form is fully operational

## 5. Decision record

### Decision
Do not yet declare the operational issue workflow fully validated.

### Options considered
1. Treat file readback as full validation.
   - Rejected because it does not prove GitHub accepts and renders the form.
2. Record a partial pass and leave UI verification open.
   - Selected because it matches the evidence and avoids overclaiming.

### Rationale
GitHub's official documentation specifies that issue forms use a YAML schema in the .github/ISSUE_TEMPLATE directory and are rendered through the issue-creation UI. Repository file presence alone does not demonstrate that the UI rendered the form or accepted a submission.

### Required next action
Open the repository's Issues → New issue flow in GitHub and confirm:
- The Research Work Item form appears.
- Required fields and dropdowns display correctly.
- No label error appears.
- A test issue can be submitted using the form.

If the form does not appear or fails validation, capture the exact error and amend the YAML; preserve this report as the original failed/partial result.

## 6. Governance
- No paid services or external compute were activated.
- No purchases or live trading were authorized or performed.
- No claim is made that an EA compiled or that any backtest ran.
- The user remains the final decision-maker.
