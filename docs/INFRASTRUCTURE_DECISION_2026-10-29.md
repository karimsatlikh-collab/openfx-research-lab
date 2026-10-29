# Infrastructure Decision Log — 2026-10-29

## Decision approved by the president
- The personal Windows 7 computer is no longer the proposed execution host for this project.
- The president accepts a planning budget of approximately **600,000 Iranian toman per month** for an Iranian Linux VPS.
- This is authorization to continue feasibility work and prepare a low-cost VPS plan, **not** confirmation that a server has been purchased, provisioned, secured, or tested.
- Do not exceed the monthly ceiling or enable paid add-ons without explicit approval.

## Intended first use
Use the VPS as a small, persistent Linux/Python research orchestrator:
1. Run scheduled, lightweight collection jobs from permitted/public sources.
2. Store source manifests, metadata, hashes, structured logs, and small outputs.
3. Run lightweight parsing and automated checks.
4. Generate health/status reports and recover scheduled jobs after process restarts.
5. Keep code in GitHub; keep large media and market-data files out of Git history.

## Explicit exclusions for phase 1
- No claim of autonomous 24/7 operation until a continuous soak test has passed.
- No claim that videos are being found, transcribed, or semantically researched until those functions are implemented and measured.
- No MT5 Strategy Tester or live trading requirement on the first Linux VPS. MT5-on-Linux/Wine compatibility must be tested separately before adoption.
- No paid AI/API usage unless a separate budget and hard usage limit are approved.
- No company registration or legal fees at this infrastructure stage.

## Procurement requirements
Before purchase, compare at least two current Iranian VPS offers and verify:
- Total monthly price, VAT/fees, renewal price, and whether the quoted amount is promotional.
- 2 vCPU, at least 2 GB RAM, and at least 20 GB SSD/NVMe as a minimum pilot configuration.
- A currently supported Ubuntu LTS image, SSH access, firewall controls, and console/recovery access.
- Outbound network access required by permitted sources and package repositories.
- Backup/snapshot cost, traffic quota, bandwidth policy, uptime terms, and cancellation/refund terms.
- Provider support, account security, and ability to recover access.
- Whether the provider permits the intended research workload and automated collection.

If 2 GB RAM proves insufficient, measure actual memory pressure before increasing resources; do not silently exceed the budget. Video transcription, large models, and MT5 may not fit this minimum server.

## Security and cost controls
- Use SSH keys where supported; disable password-based root login after confirming key access.
- Create a non-root service account, configure a firewall, apply security updates, and keep secrets out of Git.
- Configure log rotation, disk-space monitoring, and a hard stop/alert for resource or cost limits.
- Keep at least one recoverable copy of configuration and small metadata outputs outside the VPS.
- Use only lawful/authorized collection methods and respect source terms, rate limits, and licenses.

## Acceptance gates after provisioning
1. Record provider, plan, region, price, operating-system image, and resource limits.
2. Confirm SSH access and baseline CPU/RAM/disk/network status.
3. Install the minimum Python runtime and pinned dependencies; run repository tests.
4. Run one harmless scheduled test job and confirm logs/results survive a service restart.
5. Simulate a failed job and verify bounded retry plus an explicit failure record.
6. Complete a 72-hour pilot with monitoring before describing the system as 24/7-ready.
7. Review actual resource usage and cost before adding transcription, AI APIs, or MT5.

## Current status
**Approved plan; not yet purchased or deployed.** Next action is to compare current offers against the checklist and confirm the exact plan, renewal price, and terms before any purchase.
