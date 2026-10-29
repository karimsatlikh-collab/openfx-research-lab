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
- [ ] Add artifact hashing and immutable run records.
- [ ] Add synthetic fixtures for costs, order timing, gaps, and look-ahead edge cases.
- [ ] Add a results schema with metrics, tester configuration, and artifact references.
- [ ] Add explicit development / validation / final out-of-sample metadata.
- [ ] Build independent report validation before optimizing strategies.

## Phase 2 — Research-source ingestion

- [ ] Source registry for videos, transcripts, papers, datasets, and code.
- [x] Define source URL, author/date, rights status, collection method, content hash, transcript timestamps, extraction method, confidence, and text hash fields.
- [x] Add local VTT/SRT/plain-text transcript import with timestamps, deterministic segment IDs, and content hashes.
- [ ] Add an authorized source connector for source discovery and transcript acquisition; current registry does not crawl or download.
- [x] Add heuristic extraction-quality checks for dropped/changed numbers and dates, changed negation, and low token similarity.
- [ ] Expand multilingual/ASR-specific fixtures and add human-reviewed reference transcripts; heuristics cannot prove semantic equivalence.
- [x] Add claim classifications and exact-quote evidence links to separate source-confirmed claims, source claims, interpretations, hypotheses, and unknowns.
- [ ] Add human-reviewed conflict resolution and semantic contradiction analysis; current contradiction groups are manually assigned for review.

## Phase 3 — MT5 integration design (not deployed)

- [x] Draft threat model and private control-plane architecture.
- [ ] Implement and independently review the private control plane.
- [ ] Define allow-listed job specifications and idempotent queue behavior.
- [ ] Validate log/report/artifact provenance and hashes.
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
