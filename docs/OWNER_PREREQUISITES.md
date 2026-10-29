# Owner-provided prerequisites for OpenFX

This checklist separates decisions and accounts that must be controlled by the project owner from implementation work that can be performed by the engineering assistant. Never paste passwords, API keys, broker logins, recovery codes, or private keys into ChatGPT, GitHub issues, or this public repository.

## Required from the owner

### A. VPS and access
- [ ] Choose and purchase a Windows VPS suitable for MT5 Strategy Tester workloads.
- [ ] Provide the provider, Windows Server version, region, CPU/RAM/storage specifications, and monthly budget.
- [ ] Configure administrator access personally. Do not send the password in chat.
- [ ] Restrict RDP to a VPN or known administrator IP; enable MFA at the provider/identity layer where available.
- [ ] Confirm the VPS is permitted for the intended use under provider terms.

### B. MT5 and market data
- [ ] Confirm the broker and demo-server name to use for research.
- [ ] Install or authorize installation of MT5 on the VPS after the host is ready.
- [ ] Sign in to a demo account on the VPS yourself; do not send account passwords here.
- [ ] Confirm the intended symbols, timeframes, test period, account currency, deposit, and leverage assumptions.
- [ ] Approve the historical-data source and any applicable terms/licensing.
- [ ] Provide the EA source/build to test only after strategy rules and the test plan have been reviewed.

### C. API and model orchestration
- [ ] Decide whether to fund a separate OpenAI API project. ChatGPT subscription access is not the same as API access; API usage is separately billed.
- [ ] Create a dedicated API project/key with minimum required permissions and spend limits. Store the key directly in a secret manager or the orchestrator host's protected environment; never send it in chat or commit it.
- [ ] Decide whether to enable Claude as a separate reviewer. Authenticate its connector directly in Claude; permissions are not transferable to ChatGPT.
- [ ] Approve a maximum monthly budget for model/API use, data services, VPS, and backtest compute.

### D. Security and governance
- [ ] Approve a private control repository/service separate from the public research repository.
- [ ] Approve the policy that automated jobs cannot issue live trades, change broker account settings, or execute arbitrary shell commands.
- [ ] Choose who may approve strategy changes, deployment changes, and any future expansion of permissions.
- [ ] Choose the rights/terms for any external contributor or third-party code; the public repository currently reserves all rights in original project materials.

## Engineering work that can be performed by the assistant

- [x] Maintain repository documentation, schemas, mock lifecycle, tests, and safe research tooling.
- [ ] Implement stricter manifest validation, source provenance, immutable run records, artifact hashing, and report validation.
- [ ] Design the private job API, authentication/authorization, queue semantics, audit logs, and worker protocol.
- [ ] Implement the worker code and deployment scripts in a reviewable form, without needing secrets embedded in source.
- [ ] Implement automated smoke tests, fixed-run reproducibility checks, cost-aware reports, and CI.
- [ ] Add optional Claude-review workflow documentation and standardized review prompts.
- [ ] Create operational checklists and step-by-step instructions for the owner to execute locally or on the VPS.
- [ ] Inspect logs and artifacts that the owner makes available through an approved repository or upload.

## Work that cannot be completed without owner action/access

- Buy or authorize payment for VPS/API services.
- Accept provider terms, configure payment, complete identity verification, or grant external account permissions.
- Log in using owner passwords or recover credentials.
- Install MT5 on a machine that has not been provisioned and authorized.
- Enable a Claude connector in the owner's Claude account.
- Verify a real VPS/MT5 run without access to that host's actual logs/artifacts.
- Decide legal licensing, contributor terms, budget ceilings, or authorization boundaries on behalf of the owner.

## First owner handoff

When ready, send only these non-secret details in chat:
1. VPS provider and Windows Server version (or say "not purchased yet").
2. Monthly total budget range for VPS + API.
3. Broker and intended MT5 demo server.
4. Whether a separate OpenAI API project can be used.
5. Whether Claude should start with read-only GitHub access.

Do not include any credentials.
