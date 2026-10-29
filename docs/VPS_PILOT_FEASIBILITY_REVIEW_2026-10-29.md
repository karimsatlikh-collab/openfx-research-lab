# VPS Pilot Feasibility Review — 2026-10-29

Status: researched and documented; no purchase or deployment has occurred.

## Decision to be implemented
The president asked to proceed with feasibility work, using an Iranian Linux VPS and excluding the personal Windows 7 computer as the execution host. The working ceiling discussed is approximately 600,000 toman/month for the server. Whether this is the server-only ceiling or the entire company operating budget has not yet been explicitly confirmed, so no other paid service should be activated.

## Current public price snapshots
Prices below were visible on provider pages at the time of review. They are not checkout quotes; taxes, setup fees, renewal price, traffic overage, availability, and exact OS images must be confirmed before payment.

| Provider / offer | Published resources | Published monthly price | Fit against 600,000 toman ceiling | Assessment |
|---|---|---:|---|---|
| [Userver — Linux Iran, Plan 1](https://userver.ir/vps-hosting-linux-iran/) | 2 vCPU, 2 GB RAM, 20 GB NVMe, 100 GB traffic | 559,000 toman | Within ceiling by 41,000 | Best initial candidate on published specs; confirm renewal/fees and Ubuntu LTS image. |
| [IRVM — entry VPS](https://irvm.org/) | 1 CPU, 1 GB RAM, 10 GB storage, 15 GB initial traffic | 545,000 toman | Within ceiling by 55,000 | Not recommended for the pilot: too constrained for logs, packages, and reliable scheduled jobs; listed as a generic VPS and OS/storage details require confirmation. |
| [Milad Server — Iran Linux Economic 2](https://miladserver.com/) | 2 vCPU, 2 GB RAM, 45 GB HDD, 300 GB traffic | 610,000 toman | 10,000 above ceiling | Near alternative but exceeds the ceiling and lists HDD rather than NVMe. |
| [eFixHost — Linux Cloud Server IR-2](https://efixhost.com/%D8%B3%D8%B1%D9%88%D8%B1-%D9%85%D8%AC%D8%A7%D8%B2%DB%8C-%D9%84%DB%8C%D9%86%D9%88%DA%A9%D8%B3-%D8%A7%DB%8C%D8%B1%D8%A7%D9%86/) | 2 vCPU, 2 GB RAM, 35 GB NVMe, unlimited traffic (as advertised) | 790,000 toman | 190,000 above ceiling | Better disk capacity on paper, but outside current budget. |

Sources:
- Userver: https://userver.ir/vps-hosting-linux-iran/
- IRVM: https://irvm.org/
- Milad Server: https://miladserver.com/
- eFixHost: https://efixhost.com/سرور-مجازی-لینوکس-ایران/

## Technical feasibility verdict
A 2-vCPU / 2-GB-RAM / 20-GB-NVMe VPS is sufficient only for a deliberately small first pilot:
- a minimal Linux OS, Python runtime, and pinned lightweight dependencies;
- one scheduled collector/check at a time;
- metadata and source registry in SQLite;
- structured logs, small JSON/CSV outputs, and health reports;
- bounded retries, disk-space checks, and restart recovery.

It is not a responsible assumption that this size can handle all workloads. Exclude for phase 1:
- local large-language-model inference or model training;
- bulk video downloads, video transcoding, and large-scale speech-to-text;
- large tick-data archives or large datasets stored on the VPS;
- running MT5/Strategy Tester under Wine;
- paid AI/API calls until a separate limit is approved;
- multiple concurrent research workers.

For transcript extraction, prefer a staged approach: first index sources and collect authorized captions/transcripts when available; only later evaluate a bounded external transcription service or a separate compute host. Do not download or process large media by default.

## Initial resource budget
- Keep at least 25% of disk available; 20 GB is a hard constraint, not a media archive.
- Keep concurrency at one worker until memory usage is measured.
- Set logs to rotate and cap their total size.
- Store source URLs, timestamps, license/access notes, hashes, extraction status, and compact results on the VPS.
- Keep source code in GitHub and make separate backups of small state/database files. Never commit secrets or large media to Git.
- Configure monitoring for memory, disk, failed jobs, missed schedules, and network errors.

## Required purchase checks
Before placing an order, verify in the provider's checkout/support response:
1. Final monthly recurring price and renewal price; taxes and setup fees.
2. Ubuntu LTS version available, KVM or equivalent virtualization, and SSH/root recovery console.
3. CPU/RAM/storage allocation and whether NVMe is actually included in the selected plan.
4. Monthly traffic cap and exact overage price; the page notes that excess download traffic can incur additional charges.
5. Backup/snapshot price and whether a snapshot survives account cancellation.
6. Provider terms permit the planned authorized research workload.
7. Cancellation and refund terms, service region, and network access to required repositories/sources.

## Next actions after approval/purchase
1. Provision with Ubuntu LTS and document provider/plan/price.
2. Secure SSH, create a non-root service account, enable firewall, update packages, and protect credentials.
3. Clone repository and run the existing tests; record outputs rather than infer success.
4. Implement one harmless scheduled heartbeat job with structured logs and a SQLite run ledger.
5. Test restart recovery and simulated job failure.
6. Run a monitored 72-hour soak test before using the phrase “24/7-ready.”
7. Only after this gate, add one authorized source-discovery/extraction workflow and measure its resource use.

## Final recommendation
Keep Userver's 559,000-toman plan as the first candidate, not a final purchase instruction. It fits the working monthly ceiling and has the minimum 2-vCPU / 2-GB / NVMe shape needed for the lightweight pilot. Do not buy until renewal/fees, Ubuntu LTS, traffic overage, backups, and recovery access are confirmed. If any condition fails, pause and return with the exact quote rather than silently exceeding the budget.
