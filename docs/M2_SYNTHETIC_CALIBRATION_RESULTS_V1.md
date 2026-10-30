# M2 Synthetic Calibration v1 — Results

**Plan:** `m2-synthetic-calibration-v1` / `1.0.0`  
**Evidence class:** synthetic only.  
**PR:** #32 — Pre-register and implement M2 synthetic calibration v1  
**PR head tested:** `020a9ff83e40d0df8621522eade52b638d01e9ec`  
**GitHub Actions merge-ref SHA recorded in the report:** `3821c75d3ca5e0376db6cbb56902cc52831998c5`  
**Campaign workflow run:** `41015384903` (run #6, completed successfully)  
**Artifact:** `m2-synthetic-calibration-v1-41015384903` (1,042,534 bytes; retained 90 days)  
**Artifact ZIP SHA-256:** `b3433c0d3e6e377db39d9056ca52c8736e054f4890a6594933f0d368e62f8f99`

## 1. Outcome

The frozen v1 numerical acceptance criteria passed in all declared cells:

- **Null false positives:** all 5 generator families had upper two-sided 95% Wilson bounds below 5%.
- **Power at the predeclared MDE (+0.40):** all 5 generator families had lower two-sided 95% Wilson bounds above 80%.
- **Leakage fixtures:** all 6 finite, predeclared fixture classes were detected.
- **Replicates:** 20,000 raw records; 20 cells; exactly 1,000 replicates per cell.
- **Repeatability:** calibration unit tests passed, including deterministic same-cell replay.

This is a pass for the specific frozen synthetic protocol only. It is not evidence of a real market edge, strategy profitability, realistic market simulation, or valid multiple-testing correction.

## 2. Per-family results

Each null cell has 1,000 trials. Each MDE cell has 1,000 trials. The reported bounds are the relevant Wilson bound for the acceptance test.

| Generator family | Null false positives | Null upper 95% bound | Power at +0.25 | Power at MDE +0.40 | MDE lower 95% bound | Power at +0.60 |
|---|---:|---:|---:|---:|---:|---:|
| N-IID | 7/1000 (0.7%) | 1.4378% | 493/1000 (49.3%) | 929/1000 (92.9%) | 91.1386% | 1000/1000 (100%) |
| T5-IID | 6/1000 (0.6%) | 1.3028% | 497/1000 (49.7%) | 939/1000 (93.9%) | 92.2420% | 999/1000 (99.9%) |
| HET-IID | 4/1000 (0.4%) | 1.0240% | 490/1000 (49.0%) | 925/1000 (92.5%) | 90.6999% | 1000/1000 (100%) |
| AR1-030 | 30/1000 (3.0%) | 4.2503% | 519/1000 (51.9%) | 883/1000 (88.3%) | 86.1597% | 997/1000 (99.7%) |
| CONTAM-05 | 5/1000 (0.5%) | 1.1651% | 514/1000 (51.4%) | 942/1000 (94.2%) | 92.5750% | 1000/1000 (100%) |

The closest null family to the 5% upper-bound limit was AR1-030 at 4.2503%. The lowest MDE power lower bound was AR1-030 at 86.1597%. Both satisfy the frozen criteria.

The +0.25 and +0.60 cells are reference effect levels. They are reported for context; the formal power acceptance threshold was applied only at +0.40.

## 3. Leakage fixture results

All six declared fixture classes returned `detected`:

1. Future-bar feature timestamp.
2. Missing timezone / incomparable timestamp.
3. Target-label availability later than decision time.
4. Revised historical data with a later revision timestamp.
5. Split overlap / feature window crossing a split boundary.
6. Final-OOS data or metrics exposed to the optimizer.

These are explicit fixture-level controls, not a general proof that arbitrary datasets or feature values are leakage-free.

## 4. Independent artifact reproduction checks

The downloaded artifact was checked separately from the workflow's aggregate summary:

- Parsed exactly 20,000 JSONL records.
- Confirmed 20 unique calibration cells, each with exactly 1,000 records, and no duplicated seed across the 20,000 records.
- Recomputed every cell's pass count and Wilson interval from the raw records; all 20 matched the aggregate report.
- Regenerated all 20,000 synthetic return streams from the declared family, seed, and effect; **all 20,000 return-stream SHA-256 hashes matched** the stored records (zero mismatches).
- Confirmed all raw records are labelled `synthetic` and carry the plan, generator, decision-rule, source revision, Python, and platform identifiers.

File hashes after extraction:

- `raw-records.jsonl` SHA-256: `2a3934336280a84df577bd67b1a7ee4da5279de7cfd76d49ce005bc93a3f1b16`
- `aggregate-report.json` SHA-256: `8bf65433a7e06db8b70407eff307b1a62a02ce54c685c8414ce202ea5a6c7b35`

This is a reproducibility check of the artifact and calculations. It is not a substitute for the independent human review required by Issue #24.

## 5. CI history

The first CI attempt exposed a floating-point boundary issue in the Wilson interval test for zero successes (the computed lower bound was a tiny positive value rather than exactly zero). The implementation was corrected to handle the mathematical boundary cases explicitly.

On the corrected PR head, the following workflows completed successfully:

- M2 Synthetic Calibration — run `41015384903`.
- Project Tests — run `41015384920`.
- OpenFX Unit Tests — run `41015384884`.

The calibration run executed the complete 20,000-replicate campaign and uploaded the raw and aggregate artifacts. No tests were represented as passing before the corrected run.

## 6. Remaining work before Issue #24 can close

1. Obtain independent human review of generator assumptions, interval calculations, fixture scope, and the raw artifact.
2. Confirm the PR #23 base dependency and review/merge order; PR #32 is based on `openfx-foundation-m1-contracts`, not `main`.
3. Preserve the artifact and this report as immutable evidence.

Issue #27 remains a separate, mandatory selection-bias correction task. Passing this synthetic calibration does not authorize broad strategy parameter-grid optimization or final-winner selection until Issue #27 is implemented and accepted.

No market data, MT5, VPS, broker connection, paid API, or live trading was used.
