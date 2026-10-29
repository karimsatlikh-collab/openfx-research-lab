# GitHub Project Review Template

Use one copy per external repository. The goal is to preserve reproducible evidence and avoid turning marketing claims into research facts.

## 1. Review identity

- Review ID:
- Reviewer/team:
- Review date (UTC):
- Repository name:
- Canonical URL:
- Owner/maintainers:
- Default branch:
- Exact commit SHA or release tag reviewed:
- Review scope: README / source / tests / CI / issues / PRs / releases / reports / security
- Review status: NOT STARTED / PARTIAL / COMPLETE / BLOCKED

## 2. Provenance and license

- README URL + blob SHA:
- License file URL + blob SHA:
- License name/version as written in the repository:
- License uncertainty / files with different licenses:
- Attribution, copyleft, patent, trademark, or commercial-use conditions:
- Security policy / SECURITY.md:
- Contribution guide:
- Third-party actions/dependencies and pinning:
- Legal review required? Why?
- **Reuse decision:** LEARN / TEST IN ISOLATION / DEPENDENCY CANDIDATE / FORK CANDIDATE / CONTRIBUTE DRAFT / CONTACT / REJECT / LEGAL REVIEW REQUIRED

Do not assume that “public” means “permissively licensed.” Do not copy code before reviewing license compatibility.

## 3. What is actually implemented?

List concrete files, modules, workflows, and tests inspected. Distinguish observed implementation from README promises.

| Item | Source path / URL | Observed behavior | Evidence strength | Gaps |
|---|---|---|---|---|
| | | | | |

## 4. Claims versus evidence

| Claim | Who makes it? | Evidence found | Independently reproduced by us? | Status |
|---|---|---|---|---|
| | | | NO / YES (link run artifact) | AUTHOR CLAIM / PARTIALLY SUPPORTED / REPRODUCED / CONTRADICTED / UNKNOWN |

A screenshot, README statement, star count, compile success, or single profitable backtest is not proof of a durable trading edge.

## 5. Backtesting and optimization audit

- Engine/platform/version:
- Instrument(s) and broker/data source:
- Data resolution / tick model:
- Date range:
- Development / validation / final OOS split:
- Parameter search space and number of trials:
- Multiple-testing / selection-bias controls:
- Spread:
- Commission:
- Slippage:
- Swap / financing:
- Execution timing: same bar / next bar / tick / other:
- Intrabar stop/target collision policy:
- Look-ahead / repaint / future-data safeguards:
- Survivorship / selection bias risks:
- Metrics and definitions:
- Trade-level / fill-level artifacts:
- Reproducibility instructions:
- Independent replication status:
- Known negative results or limitations:

If an item is not explicitly verified, write UNKNOWN / NOT INSPECTED rather than guessing.

## 6. Tests and software quality

- Unit tests and edge cases inspected:
- Integration tests:
- CI workflow and trigger:
- Build/compile coverage:
- Deterministic fixtures:
- Expected-value assertions:
- Coverage gaps:
- Latest CI result observed (include URL and timestamp) or NOT CHECKED:
- Did we run anything? If yes, exact environment/command/run ID/artifact. If not, state NOT RUN.

## 7. Security and operational risks

- Install/build scripts reviewed:
- External actions pinned to immutable SHAs?
- Secrets/credentials requested?
- Network access or downloads:
- Binary-only dependencies:
- Unsafe eval/deserialization/shell execution:
- Dependency and supply-chain concerns:
- Isolation required before running:
- Findings and severity:

Do not run untrusted repository code simply because documentation recommends it. Do not expose secrets or private strategy rules.

## 8. Reuse and collaboration decision

- What can we learn without copying code?
- Potential dependency / fork / upstream contribution:
- Exact files or issue to target:
- Contribution license implications:
- Could public activity disclose company IP or commit the company to support?
- Approval required before publication? YES unless clearly pre-approved
- Draft issue/PR URL (if any); otherwise NONE
- Maintainer contact made? YES/NO
- Final recommendation and rationale:

## 9. Reusable research outputs

- New hypothesis or research question:
- Possible negative finding:
- Test fixture to reproduce:
- Rule/implementation pattern:
- New company work item:
- Links to internal decision record / experiment manifest:
- Confidence: LOW / MEDIUM / HIGH and why.

## 10. Review sign-off

- Source Discovery and Collection:
- Strategy Research:
- Strategy Engineering:
- Independent Validation / Watchdog:
- Central Research Orchestration:
- Final status: ACCEPTED FOR LEARNING / ACCEPTED FOR ISOLATED TEST / DEPENDENCY APPROVED / REJECTED / NEEDS MORE EVIDENCE

No review status alone implies a profitable strategy or a successful independent reproduction.
