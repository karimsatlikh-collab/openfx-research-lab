# OpenFX roadmap

## Phase 0 — Repository foundation (in progress)

- [x] Align README and startup scaffold with OpenFX identity.
- [x] Add versioned experiment manifest helper and schema.
- [x] Add mock-only worker and lifecycle tests.
- [x] Add basic CI test workflow.
- [x] Document secure execution boundaries.
- [x] Confirm CI test run is green in GitHub Actions.
- [x] Record rights-reserved terms in LICENSE; public visibility does not grant general use rights.
- [x] Document owner prerequisites and secure AI/MT5 worker architecture.
- [x] Document Claude as an optional, separately authorized reviewer.
- [x] Add source-record validation with provenance, license-review status, collection method, and content hash.
- [ ] Build a populated source inventory from approved sources and record per-source rights decisions.

## Phase 1 — Reproducible local research

- [x] Enforce strict manifest dates, timezone-aware timestamps, state invariants, finite JSON values, and safe artifact paths.
- [x] Add SHA-256 artifact records and atomic manifest/registry writes.
- [x] Add a CLI that independently verifies artifact file sizes and SHA-256 hashes under a trusted local root.
- [ ] Add immutable run records and independently parse actual MT5 reports/logs.
- [ ] Add synthetic fixtures for costs, order timing, gaps, and look-ahead edge cases.
- [x] Add a strict result schema with metrics, tester configuration, costs, and artifact references.
- [x] Add explicit development / validation / final out-of-sample metadata and reject overlapping splits.
- [x] Add metadata-level result validation with review blockers for missing artifacts/cost attestations and warnings for inconsistent metrics.
- [ ] Parse actual MT5 reports and independently verify their bytes/logs before treating any result as verified.

## Phase 2 — Research-source ingestion

- [x] Source registry for videos, transcripts, papers, datasets, and code.
- [x] Define source URL, author/date, rights status, collection method, content hash, transcript timestamps, extraction method, confidence, and text hash fields.
- [x] Add local VTT/SRT/plain-text transcript import with timestamps, deterministic segment IDs, and content hashes.
- [x] Add a local CLI for registry initialization, source registration, and transcript import.
- [x] Add official YouTube Data API metadata search with bounded responses, API-key environment configuration, and rights status defaulting to unknown.
- [ ] Add a rights-authorized transcript/caption acquisition connector; the current API connector does not download videos or captions.
- [x] Add heuristic extraction-quality checks for dropped/changed numbers and dates, changed negation, and low token similarity.
- [ ] Expand multilingual/ASR-specific fixtures and add human-reviewed reference transcripts; heuristics cannot prove semantic equivalence.
- [x] Add claim classifications and exact-quote evidence links to separate source-confirmed claims, source claims, interpretations, hypotheses, and unknowns.
- [ ] Add human-reviewed conflict resolution and semantic contradiction analysis; current contradiction groups are manually assigned for review.

## Phase 3 — MT5 integration design (not deployed)

- [x] Draft threat model and private control-plane architecture.
- [ ] Implement and independently review the private control plane.
- [x] Define allow-listed worker job fields, exact-host control-plane allowlist, and idempotency-key collision checks in the prototype.
- [ ] Build the private signed/approved queue and independently test crash recovery.
- [x] Define report/artifact provenance and hash contracts.
- [ ] Independently verify artifact bytes and parse actual MT5 logs/reports.
- [ ] Review a compatible Windows host and least-privilege account model.
- [ ] Only after separate approval: install MT5 on the VPS and conduct a non-trading smoke test.

## Phase 4 — Strategy validation

- [ ] Audit candidate strategy rules and historical research artifacts before optimization.
- [ ] Build baseline tests with realistic trading costs.
- [ ] Compare independent implementations/event timing where feasible.
- [ ] Run sensitivity and walk-forward tests.
- [ ] Preserve negative and inconclusive results.

## Explicitly out of scope until separately approved

- Live trading.
- Broker credentials in GitHub.
- Public pull requests triggering privileged execution.
- A persistent privileged self-hosted GitHub Actions runner on this public repository.
- Any claim of profitability based only on an optimized historical backtest.
