# Remote Control Architecture: ChatGPT ↔ GitHub ↔ Windows MT5 Worker

**Created:** 2026-10-29  
**Status:** DESIGN ONLY — no VPS, remote agent, SSH connection, or MT5 worker has been installed.  
**User direction:** Defer VPS purchase and MT5 installation to a later day. In the meantime, design and validate the least-interactive safe way for the research system to communicate with a future VPS.

## 1. Goal and realistic boundary

The goal is for the user to make only high-level decisions while the research system queues approved experiments, the Windows worker executes them, and results return automatically for review.

ChatGPT does **not** currently have a direct authenticated shell session to an unprovisioned VPS. A future connection must be created deliberately. Once a worker and controlled communication channel exist, the workflow can be largely unattended; provider account creation, payment approval, initial credential/bootstrap, and any high-impact permission changes may still require the user.

## 2. Recommended architecture

### Control plane
- GitHub repository holds versioned experiment manifests, strategy source references, run state, and artifact indexes.
- Each experiment has a unique immutable `experiment_id`, source commit, data identity, symbol/timeframe, date boundaries, parameter grid, costs, and expected output list.
- Jobs move through explicit states: `DRAFT → REVIEWED → APPROVED → QUEUED → RUNNING → COMPLETED | FAILED | INTERRUPTED`.
- The independent Watchdog reviews completeness and validation; the proposing worker must not self-approve its own result.

### Windows execution worker
- A conventional Windows VPS runs MT5/MetaEditor/Strategy Tester after the future purchase and setup are approved.
- A small Windows worker polls for approved manifests over outbound HTTPS, or receives a queued task through a hardened automation channel. No inbound RDP/SSH endpoint is required for routine job dispatch.
- The worker accepts only a constrained schema and an allowlist of operations, such as: check environment, compile a pinned EA source, run a named preset, collect reports/logs, compute checksums, and upload artifacts.
- Do **not** allow a job manifest to contain arbitrary PowerShell, shell commands, download-and-execute instructions, or arbitrary URLs.
- The worker runs with a dedicated low-privilege Windows account, restricted filesystem paths, outbound network policy, and no live-trading credentials.
- It writes append-only run logs and stores results under unique run IDs. Partial/incomplete runs are marked interrupted, never silently completed.

### Result return
- The worker uploads only explicit result artifacts (tester report, journal, compile log, manifest snapshot, environment record, checksums) through a scoped write path.
- The control plane validates the artifact manifest and checks expected outputs and pass counts.
- The Watchdog then checks missing results, duplicate runs, unexpected parameters, date/symbol mismatch, and consistency with the experiment manifest.
- Results become available for ChatGPT analysis through the repository's connected GitHub tools; no claim of a completed test is made until artifacts are fetched and checked.

## 3. Important security decision: do not attach a runner to the current public repository

GitHub's official security guidance warns that self-hosted runners can be persistently compromised by untrusted workflow code and says they should almost never be used for public repositories, because outside contributors can submit pull requests that may execute dangerous code.

Sources:
- https://docs.github.com/en/actions/reference/security/secure-use
- https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners

Therefore:
- Do **not** register a persistent self-hosted GitHub Actions runner against this public repository.
- If GitHub Actions becomes the chosen job channel, first use a separate private repository or a tightly controlled private organization/repository, restrict who can dispatch workflows, require review before privileged execution, and use narrowly scoped credentials.
- Even on a private repository, do not execute unreviewed code on a persistent MT5 machine. Keep job payloads declarative and the runner operations allowlisted.
- A custom polling worker may be safer and simpler than a general-purpose self-hosted Actions runner for the long-lived MT5 host, provided its update, authentication, and audit design is reviewed.

## 4. Communication options to evaluate before VPS purchase

### Option A — Private GitHub control repository + restricted Windows polling worker (preferred candidate)
Pros:
- Outbound HTTPS only; no public inbound admin port required for routine control.
- Declarative manifests and artifacts remain versioned and auditable.
- Does not grant GitHub workflows arbitrary access to the MT5 host.
- Can support queued jobs, retries, checksums, and resumable state.

Cons:
- Requires engineering and security review of worker authentication, polling, state transitions, and artifact upload.
- Requires a private repository or equivalent restricted control channel before secrets or proprietary strategy files are stored.

### Option B — Private GitHub Actions + dedicated Windows self-hosted runner
Pros:
- Native workflow queue and job status; fewer orchestration components.
- GitHub can dispatch a job when the runner is online.

Cons:
- A persistent runner executes workflow code on the VPS; dangerous with untrusted or changeable workflows.
- Must never be registered against the current public repository.
- Needs private repo access restrictions, required reviews, least-privilege token, pinned actions, and a recovery/logging plan.

### Option C — SSH/PowerShell remoting
Pros:
- Standard remote administration and automation mechanisms exist for Windows.
- Suitable for controlled maintenance when secured with keys and firewall restrictions.

Cons:
- Requires a reachable management endpoint or private network/tunnel and careful credential handling.
- Adds an administrative access path; not necessary for routine experiment dispatch if Option A works.
- Must not expose RDP or SSH broadly to the public internet.

Microsoft reference:
- https://learn.microsoft.com/en-us/powershell/scripting/security/remoting/ssh-remoting-in-powershell

**Provisional choice:** design Option A first. Evaluate Option B only after securing the repository/control plane. Keep SSH/RDP for tightly controlled setup and recovery, not as the default task queue.

## 5. Credential and approval rules

- Never paste passwords, private SSH keys, access tokens, broker credentials, or VPS credentials into chat messages, public issues, commits, logs, or experiment manifests.
- Use secret storage and short-lived/scoped credentials where supported; rotate/revoke bootstrap credentials after setup.
- No paid provider, VPS, subscription, or cloud service may be created without explicit user approval of the provider and amount.
- No live account access or live trading. Tester jobs must run with trading disabled and no live credentials.
- Public contributions, forks, or external maintainer contact that could disclose proprietary strategy details require separate approval.
- Keep control-plane read/write permissions separated where practical; a worker that only needs to upload reports must not have broad repository administration rights.

## 6. Minimum API/worker contract

Each queued job should include:
- `job_id`, `experiment_id`, schema version, creation timestamp, approval record, expiry time;
- pinned source commit/hash and preset ID;
- expected terminal build and test environment;
- symbol, timeframe, date range, modelling mode, spread/commission/slippage assumptions;
- parameter grid or immutable parameter file and expected pass count;
- permitted action ID from an allowlist (not an arbitrary command);
- artifact list and checksum requirements;
- timeout, retry policy, and stop conditions.

The worker must return:
- `job_id`, `run_id`, worker/OS/MT5 versions, start/end timestamps;
- status and failure reason;
- actual pass count and output file list;
- SHA-256 checksums, tester/agent logs, compile log and report;
- restart/recovery event history;
- explicit `NOT_RUN`, `FAILED`, `INTERRUPTED`, or `COMPLETED_WITH_ARTIFACTS` status.

A result is not accepted solely because the worker says it succeeded; the control plane and Watchdog verify the artifacts.

## 7. Staged implementation plan

### Stage 0 — Now, before purchase
- [x] Document user requirement and communication design.
- [ ] Decide whether to create a separate private control repository.
- [ ] Define job manifest schema and artifact contract.
- [ ] Threat-model the public repository and credential paths.
- [ ] Prototype the queue/state transitions with mock jobs only (no MT5/VPS).
- [ ] Keep the current public repository free of secrets and proprietary strategy details.

### Stage 1 — After user authorizes a VPS
- [ ] Choose a supported Windows VPS and confirm terms before payment.
- [ ] Install Windows updates and secure remote administration.
- [ ] Install current MT5/MetaEditor from official sources.
- [ ] Run manual compile and tiny tester smoke test.
- [ ] Install the restricted worker only after the manual test passes.
- [ ] Verify outbound-only job polling and scoped artifact upload.

### Stage 2 — Reliability and automation
- [ ] Run a mock job end-to-end before a real strategy test.
- [ ] Run a short fixed MT5 test and tiny parameter grid.
- [ ] Verify logs, checksums, expected pass count, and duplicate protection.
- [ ] Run 12–24 hour soak and controlled reboot/recovery.
- [ ] Only then permit larger parameter grids and unattended queue processing.

## 8. Acceptance criteria

The connection is considered operational only when a test job can be created from the control plane, approved, received by the worker without manual intervention, executed in the permitted sandbox, and returned with verifiable logs/reports/checksums and correct state transitions. A mock job proves only communication; it does not prove MT5 compatibility or continuous backtesting.

## 9. Current state

- VPS purchase: NOT DONE.
- MT5 install on VPS: NOT DONE.
- Remote worker/agent: NOT INSTALLED.
- SSH/RDP connection from ChatGPT: NOT CONFIGURED.
- Mock queue prototype: NOT IMPLEMENTED.
- This document is architecture/design only; no connection or execution is claimed.
