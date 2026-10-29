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
- [ ] Add source inventory with provenance, license, and review status.

## Phase 1 — Reproducible local research

- [ ] Freeze experiment-manifest contract and validate date/time fields strictly.
- [ ] Add artifact hashing and immutable run records.
- [ ] Add synthetic fixtures for costs, order timing, gaps, and look-ahead edge cases.
- [ ] Add a results schema with metrics, tester configuration, and artifact references.
- [ ] Add explicit development / validation / final out-of-sample metadata.
- [ ] Build independent report validation before optimizing strategies.

## Phase 2 — Research-source ingestion

- [ ] Source registry for videos, transcripts, papers, datasets, and code.
- [ ] Track source URL, author, date, timestamp/page, license, extraction method, and uncertainty.
- [ ] Add extraction-quality tests that catch dropped negation, altered numbers/dates, and semantic drift.
- [ ] Separate source-confirmed rules from interpretations and hypotheses.

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
