# OpenFX G0–G5 Enforcement Matrix

Status: engineering design and acceptance contract. This document does not claim that the gates are currently enforced. A gate may advance only when its required evidence is present and its negative tests pass. A green CI workflow is evidence about tested code paths, not evidence of strategy profitability.

## Decision semantics

- `BLOCKED`: required evidence or control is absent; no downstream stage may treat the gate as passed.
- `PASS`: all required evidence is present, validated by the named control, and recorded with immutable identifiers/hashes.
- `WAIVED`: permitted only for a non-safety, non-integrity requirement with a named human owner, reason, scope, expiry, and audit event. Authorization, provenance, trial accounting, OOS protection, and independent verification are not waivable.
- Every gate verdict binds the gate version, input hashes, code/build hash, timestamp, actor/control identity, and prior gate verdict hash.

## Gate matrix

| Gate | Purpose and required inputs | Enforcing component (target) | Required negative/adversarial tests | Immutable evidence output | Human boundary | Current reality |
|---|---|---|---|---|---|---|
| G0 — Source admissibility | Source identity, URL/media ID, rights/permission basis, retrieval time, exact locator, capture/extraction method, content hash, known limitations | Source Registry + Rights Policy Validator + provenance store | Reject missing/expired rights; reject locator mismatch; reject changed source hash; prompt-injection text treated as data; reject transcript with missing provenance | SourceRecord, rights decision, captured artifact hash, locator map, extraction log | Human approval where rights/permission is ambiguous or owner authorization is required | Partial prototypes and policy/docs; not a complete autonomous discovery/extraction or semantic-fidelity system |
| G1 — Claim and hypothesis | Atomic source claims, exact evidence spans, provenance labels, unresolved ambiguities, StrategySpec, falsifiable HypothesisCard, predicted mechanism and invalidation criteria | Claim/Spec Validator + Hypothesis Registry; role identity service | Reject claim without source locator; reject unsupported rule promoted to verified; reject contradictory spec; reject proposer self-approval; preserve dissent/unknowns | Claim graph, versioned StrategySpec, HypothesisCard, reviewer decision and hashes | Human resolves material source ambiguity and approves research question/risk scope | Documentation and schemas exist; full role separation, claim graph, and auditable reviewer identity are not established |
| G2 — Implementation and pre-market qualification | Approved spec, code/build hash, frozen parameters, synthetic fixture, data/cost profile schemas, gate config, trial-family ID and budget | Build/Spec Conformance Validator + trusted Registrar + Synthetic Engine + Calibration Gate | Reject code/spec drift; look-ahead and timestamp leakage fixtures; noise false-positive calibration; planted-edge power checks; trial-budget race; duplicate/replayed trial; altered artifact; config changed after freeze | Frozen JobSpec, build hash, synthetic RunRecord, raw artifact hashes, registry event chain, calibration report, GateVerdict | Human approves transition from synthetic qualification to any market-data experiment | Local registry, synthetic harness, descriptive gate and tests exist; registry is not central/trusted, no multiple-testing correction, and no production role enforcement |
| G3 — Market-data evaluation | Authorized immutable market data, symbol specs, timezone/session rules, split manifest (development/validation/final OOS), realistic costs, frozen strategy/build/config, full trial-family history | Data/Cost Validator + Market Executor + OOS Access Broker + Statistical Validator | Reject missing bars/gaps or altered data hash; reject cost omissions; reject overlapping/leaking splits; reject repeated final-OOS access; reject unregistered trials; test spread/slippage/swap sensitivity; compare independent event calculations | DataProfile, CostProfile, split manifest, complete trial ledger, raw trades/equity/logs, metrics, selection-bias analysis and verdict | Human authorizes data use and any MT5 demo/local execution; final-OOS access requires separate approval | Not established as a trustworthy end-to-end market test; synthetic results are not market evidence |
| G4 — Independent reproduction and demo acceptance | Frozen source/data/spec/build/cost/gate inputs, selected candidate, reproduction protocol, independent operator identity; demo request only after prior gates | Independent Reproducer + Artifact Verifier + MT5 Demo Adapter (future) | Reproduce from clean environment; verify every input/output hash; compare event/trade sequence and metrics; detect operator identity collision; identical frozen-run repeatability; reject missing terminal logs | Independent reproduction record, discrepancy report, environment fingerprint, verified artifact manifest; if authorized, demo logs and measured runtime | Explicit human approval required before MT5 demo, broker connection, or any external execution | Independent replication and MT5 executor are not implemented; no MT5 run is evidenced |
| G5 — Release/deployment decision | G0–G4 verdicts, unresolved-risk register, operational monitoring/rollback plan, security review, cost/risk approval, owner authorization | Release Policy Engine + signed human authorization + deployment controls (future) | Reject missing/expired approvals; reject unresolved critical finding; test rollback, credential revocation, kill switch, monitoring alert and audit trail | Signed release decision, exact deployed build/config hashes, approval event, rollback and monitoring evidence | Human owner alone authorizes deployment, paid infrastructure, broker/live scope; live trading requires separate explicit approval | No deployment/live-trading capability or authorization established; this gate is design-only |

## Gate invariants

1. No gate may manufacture evidence for an earlier gate. A G2 synthetic pass cannot imply G3 market validity; G3 performance cannot imply G4 independent reproduction.
2. Every attempted trial is registered before execution and remains in the family ledger if it fails, times out, is abandoned, or is retried.
3. Final-OOS data and metrics are access-controlled, not merely hidden by convention. Each access is an auditable event; the proposer receives no final-OOS feedback during search.
4. Frozen inputs are content-addressed. A changed input creates a new version/new trial; it never overwrites historical evidence.
5. A result is not trusted because a manifest says `COMPLETED`. Executor identity, engine, build, artifacts, and attestation must be independently checked.
6. A role collision is recorded and disqualifies the activity from counting as independent review/replication.
7. A gate verdict is scoped to the exact gate version and exact input hashes. Changes invalidate downstream verdicts as configured.
8. No automated gate can authorize rights exceptions, paid services, VPS, broker connection, MT5 demo, deployment, or live trading.

## Minimum end-to-end acceptance path

The first honest vertical slice should stop at a **reproducible synthetic result**, not market profitability:

1. Admit one explicitly authorized, locally supplied source fixture (G0) and capture its hash and locator.
2. Create one atomic claim and one hypothesis card with labels separating source-backed rule from hypothesis (G1).
3. Implement a tiny deterministic synthetic strategy fixture tied to the approved spec/build hash; freeze all inputs and register the trial before running (G2).
4. Execute twice in clean temporary workspaces using the same frozen inputs. Verify identical raw outputs, artifact hashes, registry history, and gate verdict. Intentionally mutate one input and prove the verifier rejects the mismatched result.
5. Record role collisions and mark the outcome `synthetic`; stop. Do not describe it as a market backtest, strategy edge, G3 pass, or profitability result.

## Implementation backlog (ordered)

1. **G0:** source/rights record schema and fail-closed ingestion API; exact locator and raw artifact hash required.
2. **G1:** HypothesisCard schema, atomic claim-to-source links, explicit provenance labels, and reviewer event with stable actor identity.
3. **G2:** trusted trial registration boundary, immutable frozen-job snapshot, mandatory artifact re-verification, spec/build conformance, and synthetic calibration suite.
4. **G3:** market data/cost/split validators, final-OOS access broker, complete trial-family accounting, and pre-registered selection-bias method actually calculated.
5. **G4:** independent identity separation, clean-room replay, exact artifact comparison, and only then a human-approved MT5 demo adapter.
6. **G5:** signed human release authorization, deployment controls, monitoring, rollback, and credential revocation; keep disabled until G4 evidence exists.

## Exit criteria for calling the system research-ready

Do not use “research-ready” until the G0–G4 controls above are implemented and pass adversarial tests, an independent reviewer reproduces the end-to-end path, all trial history is retained, and limitations are explicit. “Production-ready” additionally requires G5 operational/security controls and explicit owner approval. A synthetic vertical slice alone is only prototype evidence.
