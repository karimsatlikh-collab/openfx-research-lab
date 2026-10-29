# MT5 Windows VPS Compatibility Review

**Review date:** 2026-10-29  
**Purpose:** Decide the correct execution environment for continuous MT5 Strategy Tester runs and large parameter-grid optimization.  
**Status:** DOCUMENTARY REVIEW COMPLETE — HOSTED PILOT NOT RUN; NO VPS PURCHASE OR INSTALLATION.

## Executive decision

**Use a conventional Windows VPS with interactive/RDP access as the leading proof-of-concept target. Do not use MetaQuotes/MQL5 Virtual Hosting as the optimization server.**

The MetaTrader 5 Strategy Tester is documented as a multi-threaded desktop feature that uses local/remote/cloud testing agents to run tests and parameter passes. MetaQuotes' own hosted virtual platform is documented for migrating and continuously running trading robots/signals, not as a general-purpose desktop where we can manage long-running Strategy Tester optimization jobs. Community forum replies also distinguish these two services; official documentation is the primary basis for the decision.

For a new hosted Windows environment, **do not select Windows 7/8/8.1 or Windows Server 2008**. MetaTrader release notes say Build 5320 (2025-09-25) was the last build to support those operating systems; newer desktop builds no longer receive updates there, except for the noted Wine exception. Prefer a currently supported Windows client/server release, then prove the exact MT5 build and agent behavior with a small pilot.

This is a compatibility decision, not a claim that any particular provider or server is already verified. No Windows VPS has been purchased, installed, or tested by this project.

## What official documentation establishes

### 1. Strategy Tester uses local computing agents and supports optimization

The official MetaTrader 5 Help page says Strategy Tester tests and optimizes EAs, is multi-threaded, and uses computing agents installed as services on the user's computer. Agents work independently and enable parallel optimization passes.

Sources:
- https://www.metatrader5.com/en/terminal/help/algotrading/testing
- https://www.metatrader5.com/en/terminal/help/algotrading/strategy_optimization
- https://www.mql5.com/en/docs/runtime/testing

**Implication:** a suitable dedicated Windows desktop/VPS environment is the natural place to prove local-agent optimization. For large grids, measure actual throughput; the number of advertised vCPUs alone is not enough.

### 2. MetaQuotes Virtual Hosting is a different product

The official Virtual Hosting guide describes a hosted platform for continuous operation of trading robots/signals. The service is designed around migration of a trading environment to a managed virtual platform, with server status, journal, and resource monitoring.

Sources:
- https://www.metatrader5.com/en/terminal/help/virtual_hosting
- https://www.metatrader5.com/en/terminal/help/virtual_hosting/virtual_hosting_terminal

A moderator response in the MQL5 forum explicitly says the built-in MQL5 VPS is not suitable for running the Strategy Tester. This is supporting community evidence, not the primary source.

Source:
- https://www.mql5.com/en/forum/327693

**Implication:** do not confuse “MT5 VPS hosting for a live EA” with a Windows VPS on which we can install MT5, MetaEditor, and run long optimization jobs.

### 3. Avoid unsupported Windows generations

MetaTrader 5 release notes state that Build 5320, dated 2025-09-25, was the last to support Windows 7, Windows 8, Windows 8.1, and Windows Server 2008. The note says desktop platforms on those operating systems will no longer receive updates after that build, except for platforms running under Wine.

Source:
- https://www.metatrader5.com/en/releasenotes

**Implication:** do not build the new runner on the user's older Windows 7 computer or on an obsolete Windows Server image. For a clean pilot, choose a currently supported Windows version and verify MT5's own update/build and agent startup.

### 4. More cores do not automatically mean faster tests

A community report describes poor Strategy Tester performance on one Windows Server 2022 VM, with a separate Windows 10 test-agent machine running much faster on the same host. This is anecdotal and does not prove Windows Server 2022 is generally unsuitable; it demonstrates why we must benchmark the exact provider, OS image, CPU allocation, and agent configuration.

Source:
- https://www.mql5.com/en/forum/446901

**Implication:** include a fixed workload and measure passes/hour, CPU utilization, agent failures, memory, disk, and completion after a restart. Do not choose a machine based on vCPU count alone.

## Recommended architecture for the first pilot

- **Execution host:** conventional Windows VPS with RDP/console access.
- **Platform:** current 64-bit MetaTrader 5 terminal and MetaEditor, installed from the official broker/MetaQuotes source.
- **Testing:** Strategy Tester with local agents first; do not depend on MQL5 Cloud Network for the initial proof.
- **Control/orchestration:** repository manifests and run IDs define experiments; Windows runner stores logs/reports and uploads or syncs artifacts to the research repository through a controlled path.
- **Safety:** use demo/test-only account context; keep live trading disabled; do not store broker passwords or API secrets in GitHub.
- **Recovery:** configure auto-start only after manual baseline succeeds; maintain a run manifest, logs, and restart/recovery procedure.
- **Isolation:** test one instance first. Multiple terminals should be installed in separate directories if required; official platform help notes two copies cannot run from the same directory.
- **Linux:** retain Linux as a possible later coordinator for collection, scheduling, metadata, and reporting. Do not make Wine-on-Linux the first MT5 optimization host unless a measured comparison later justifies it.

## Acceptance test plan (no test has been run yet)

### Gate A — Before any purchase or install
- [ ] Choose a supported Windows image and confirm RDP/console access.
- [ ] Confirm the VM is not the restricted MetaQuotes Virtual Hosting product.
- [ ] Confirm that MT5 terminal and MetaEditor can be installed from official sources.
- [ ] Confirm enough persistent disk for history, tester agents, logs, and artifacts.
- [ ] Confirm the service allows long-running workloads and that Windows updates/reboots can be scheduled.
- [ ] Do not pay or create a subscription until the user explicitly authorizes the provider and amount.

### Gate B — Manual compatibility smoke test
- [ ] Record provider, VM image, Windows build, CPU model/allocation, RAM, disk, MT5 build, broker server, and date.
- [ ] Launch MT5 and MetaEditor; compile a minimal known-good test EA.
- [ ] Open Strategy Tester and run one short EURUSD test on a fixed date range.
- [ ] Confirm local agent(s) start and finish; preserve tester and agent logs.
- [ ] Repeat with a tiny two-parameter optimization; confirm pass count equals the expected grid.
- [ ] Export HTML/XML/CSV report artifacts and verify they persist after closing/reopening MT5.

### Gate C — Continuous-run / recovery test
- [ ] Run a fixed workload for at least 12–24 hours before calling the host reliable.
- [ ] Record passes/hour, wall-clock duration, CPU, memory, disk, failures, and missing result count.
- [ ] Test a controlled terminal restart and a Windows reboot; verify that the run can resume or be safely marked interrupted without duplicating/mislabeling results.
- [ ] Verify watchdog alert/log behavior and artifact checksums.
- [ ] Repeat a small deterministic test and compare results to ensure repeatability.
- [ ] Only then evaluate scaling to a large parameter grid or parallel terminals.

## Stop conditions

Stop the pilot and record a failure if:
- MT5 or MetaEditor cannot be installed or updated;
- local agents fail to start or repeatedly stop;
- the same deterministic test produces unexplained result differences;
- reports/logs are lost or a restart causes silent duplicate/missing passes;
- the host throttles or terminates long-running work contrary to its stated terms;
- any secret or live-trading capability is exposed unintentionally.

## Final conclusion

The best-supported next step is a **small, approval-gated conventional Windows VPS pilot**. It is not yet appropriate to choose a provider or promise 24/7 performance. Prove install, compile, local-agent execution, optimization pass integrity, artifacts, and recovery before scaling. This remains the company's highest-priority infrastructure proof because the primary goal is continuous MT5 backtesting and large parameter optimization, not merely running a live EA.
