# M3 HAC-Studentized MBB v2.0.3 — Pre-Registered Calibration Plan

Status: **pre-registered plan; formal campaign not yet run**.

This plan supersedes the preserved v2.0.2 plan solely to correct the family-level null operating-characteristic sample size. The method algorithm remains `2.0.2`; this is calibration plan `V2-3`.

- Plan ID: `M3-HAC-MBB-CALIBRATION-V2-3`
- Method ID/version: `M3-HOLM-HAC-MBB-V2` / `2.0.2`
- Implementation: `openfx/selection_bias_v2.py`
- Frozen engine revision: `087e66622f27350f1999d2e5b2ec82a9ead78982` (the checked-out engine file must match this commit byte-for-byte).
- Runner revision: automatically bound to the clean Git `HEAD`; it is never caller-supplied.
- Plan hash: SHA-256 of the exact plan file bytes, computed by the runner and aggregator (not caller-supplied).
- Freeze date: 2026-10-30 UTC
- Evidence class: synthetic only.
- This plan is separate from M3 v1. It supersedes the unexecuted v2.0.0, v2.0.1, and v2.0.2 calibration plans. No formal v2 cells were run; all earlier seed ranges are retired and are not reused.

## 1. Frozen method settings

| Setting | Frozen value |
|---|---|
| Null / alternative | E[r] <= 0 / E[r] > 0 |
| Family-wise alpha | 0.05 |
| Bootstrap replicates | 9,999 |
| Minimum observations | 252 |
| Maximum observations per trial | 100,000 |
| Maximum registered trials per family | 10,000 |
| Maximum estimated bootstrap work | 1,000,000,000 units (`B × eligible_trials × n × (HAC_lag+1)`) |
| Campaign sample size | 252 |
| Circular block length | ceil(n^(1/3)) = 7 |
| HAC kernel | Newey-West/Bartlett |
| HAC lag | ceil(n^(1/3)) = 7 |
| HAC covariance denominator | n |
| Marginal p-value | (1 + # {T* >= T_obs}) / 10,000 |
| Multiplicity correction | Holm step-down |
| Failed/ineligible attempts | p=1 and retained in family |

No parameter may be tuned after campaign execution begins. A code or parameter change requires a new method/calibration version and disjoint seeds.

## 2. Null generators

Each return series has 252 observations and unit unconditional variance before any planted mean shift.

| ID | Generator | Definition |
|---|---|---|
| N1 | Gaussian IID | independent N(0,1) |
| N2 | Student-t(5) IID | t(5) scaled by sqrt(3/5) |
| N3 | AR(1)-Gaussian | phi=0.30, stationary unit variance |
| N4 | GARCH(1,1) | omega=0.05, alpha=0.05, beta=0.90, Gaussian innovations |
| N5 | AR(1)-Student-t(5) | phi=0.30, variance-standardized t(5) innovations |

Marginal null campaign: **5,000 independent deterministic replicates per generator**. Report false-positive rate at 0.05 and two-sided 95% Wilson interval.

## 3. Planted-effect campaign

- MDE: +0.35 standard deviations per observation.
- 1,000 independent deterministic replicates per generator.
- Effect is added to the first trial only in family-level power tests.
- Marginal MDE tests use the same five generators and 1,000 replicates per generator.
- No effect size may be substituted after observing results.

## 4. Direct correlated-return family campaign

This replaces the empirical-p-value copula as the primary family-level acceptance test.

- Family size: 20 trials.
- Family size 5 is evaluated as the first five members of the same generated 20-trial family, using the same underlying return family and bootstrap resamples.
- Cross-trial return dependence: common-factor correlation rho = 0.0, 0.5, 0.9.
- Generators: N1 through N5.
- 5,000 independent families per (generator, rho) cell.
- Run both global-null families and one-MDE-candidate families.
- Total: 15 global-null cells + 15 MDE cells; each cell contains 5,000 complete families.
- Each family has synchronized return timestamps, identical data/cost/split bindings, and the frozen v2 method settings.
- Apply the actual HAC-studentized MBB p-value calculation and Holm correction to the complete family, including any failed/ineligible member with p=1.

### Dependence construction

For Gaussian innovation generators, each time step uses a common-factor innovation construction:
`epsilon[j,t] = sqrt(rho)*factor[t] + sqrt(1-rho)*idiosyncratic[j,t]`.

For Student-t generators, use a multivariate-t(5) innovation construction: correlated Gaussian factor innovations divided by a common chi-square scale per time step, scaled to unit marginal variance. Because the common chi-square scale is shared across trials, rho=0 means zero linear correlation, not full statistical independence; the multivariate-t cells intentionally retain common-scale tail dependence. Because the common chi-square scale is shared across trials, rho=0 means zero linear correlation, not full statistical independence; the multivariate-t cells intentionally retain common-scale tail dependence. AR(1) and GARCH recursions are applied after the correlated innovations are generated. The runner records realized average pairwise return correlation for every family; for GARCH it may differ from the innovation-correlation parameter rho.

The independent calibration runner must record the exact generation method, seed, return-series hash, family membership, frozen M3 engine revision, and runner revision for every generated family. These engine/runner revisions identify the calibration implementation; they are not a strategy source revision. Separately, the production evaluator requires each real trial validation payload to match the strategy source_revision frozen in its family manifest. This dependence construction is synthetic and does not claim to reproduce every empirical strategy-correlation structure.

## 5. Deterministic seed map

Generator order: N1, N2, N3, N4, N5. Replicate/family indices start at zero.

- Marginal null data: `3,300,000,000 + generator_index*100,000 + replicate_index`.
- Marginal MDE data: `3,400,000,000 + generator_index*100,000 + replicate_index`.
- Marginal null bootstrap seed: `3,800,000,000 + marginal_null_data_seed`.
- Marginal MDE bootstrap seed: `3,900,000,000 + marginal_mde_data_seed`.
- Global-null family seed: `3,500,000,000 + generator_index*1,000,000 + correlation_index*10,000 + family_index`.
- One-MDE family seed: `3,600,000,000 + generator_index*1,000,000 + correlation_index*10,000 + family_index`.
- Bootstrap resampling seed for a family: `3,700,000,000 + family_seed`.
- Correlation order: 0.0, 0.5, 0.9.
- Trial IDs and ordering are deterministic; the signal candidate is always the first trial in MDE families.

No seed may be skipped, replaced, or removed. Failed replicates remain in the raw output with failure reason and count toward the denominator. A campaign with any failed replicate is not accepted.

### Family-null operating-characteristic justification

For the family-null rule (point estimate <=5.5% and two-sided 95% Wilson upper bound <=6.5%), an exact binomial operating-characteristic calculation gives a 47.97% probability of passing a cell with 1,000 families when true FWER is exactly 5%. At 5,000 families, the pass probability rises to 94.94% (largest passing count 275/5,000). The family sample size is therefore fixed at 5,000 for both null and MDE cells. This calculation concerns the acceptance rule's sampling uncertainty; it is not a simulated M3 calibration result.

## 6. Acceptance criteria

### Marginal null
For each of five generators:
- FPR point estimate <=5.5%.
- Two-sided 95% Wilson upper bound <=6.5%.

### Marginal MDE
For each of five generators:
- Two-sided 95% Wilson lower bound >=80%.

### Direct family-level global null
For each of 15 generator/correlation cells, and separately for family size 5 and 20:
- FWER point estimate <=5.5%.
- Two-sided 95% Wilson upper bound <=6.5%.

### Direct family-level MDE
For each of 15 generator/correlation cells, and separately for family size 5 and 20:
- Power to reject the planted first candidate has two-sided 95% Wilson lower bound >=80%.

### Reproducibility and audit
- 5,000 null and 1,000 alternative marginal replicates per generator complete with no missing records.
- All 30 direct family cells complete 5,000 families each; all 60 family-size/scenario views are retained.
- Same frozen inputs, seeds, code revision, and runtime reproduce canonical results and hashes.
- Preserve raw p-values, return-series hashes, family-level outcomes, seed map, runtime, source revisions, and failure ledger.
- Independent reproduction of HAC statistics, bootstrap p-values, and Holm outputs must match exact/canonical results or predeclared numeric tolerances.

The evaluator blocks before sampling if estimated work `9,999 × eligible_trials × n × (HAC_lag+1)` exceeds 1,000,000,000 units; it also caps each trial at 100,000 observations and each manifest at 10,000 registered trials. A resource-budget block is not a statistical failure; it is an incomplete evaluation and cannot count as a pass.

A failure of any criterion means M3 method v2.0.2 remains **not accepted** under calibration plan V2-3. No threshold, generator, seed, family size, correlation cell, or MDE may be removed after results are seen.

## 7. Computational execution boundary

The revised 40-cell campaign is materially larger than v2.0.2. The frozen workload is approximately:
- Direct family cells: 150,000 families × 9,999 bootstrap replicates × 20 trials × 252 observations × 8 HAC terms = 60,473,952,000,000 estimated work units.
- Marginal cells: 30,000 single-trial series × 9,999 × 252 × 8 = 604,739,520,000 estimated work units.
- Total: 61,078,691,520,000 estimated work units (about 151,500 full-family-equivalent workloads).

Before launching any formal cell, run the performance preflight on the intended research host:

```bash
python research/benchmark_m3_v2_family.py --plan-file docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md --families 3 --output artifacts/m3-v2.0.3/benchmark-preflight.json
```

The preflight warms the JIT kernel separately, times full 9,999-replicate family workloads, records host/runtime/source provenance, and estimates CPU-hours. It is performance evidence only, never calibration evidence. Review the estimate and storage requirements before scheduling the campaign. Run independent cells as separate immutable jobs, initially limiting concurrency to at most four cells or the available CPU count, whichever is lower; adjust only after observing host memory/CPU behavior. Do not start the 40-cell campaign if the benchmark indicates the required wall-clock or storage budget is unavailable.



This is a deliberately substantial calibration campaign. It must be run on a reproducible research host with sufficient time and memory; it is not part of normal unit-test CI. The runner must support resumable, immutable cell artifacts without overwriting prior outputs. A partial campaign is not acceptance evidence.

The independent runner must not import the production M3 v2 evaluator. It must implement the frozen formula independently and compare selected deterministic fixtures against the production module.

## 8. Interpretation limits

- Synthetic calibration does not establish a market edge or profitability.
- HAC/MBB validity depends on time-series regularity; structural breaks, long memory, and non-stationarity remain risks.
- Holm controls FWER under arbitrary dependence only if marginal p-values are valid.
- Direct common-factor return simulations cover only the declared dependence structures.
- This does not implement DSR, PBO, or Sharpe deflation.
- No broad optimization, final-winner selection, MT5, VPS, broker, paid service, or live trading is authorized.

## 9. Stop conditions

Stop and mark the campaign inconclusive if:
- any frozen setting, code revision, seed, or family membership changes;
- any trial is omitted from the registered family;
- any return vector/hash or timestamp alignment fails;
- any cell is incomplete or has a failed replicate;
- independent calculation or deterministic reproduction disagrees;
- a code change is required after the campaign begins.

A fix requires a new method/calibration version, new plan hash, and disjoint seed ranges. Preserve all prior failed outcomes.

## 10. Execution and aggregation

Install optional pinned dependencies with `python -m pip install -r requirements-m3-calibration.txt`.

First run the deterministic primitive-level reference check. It must pass before any cell is accepted:

```bash
python research/validate_m3_v2_reference.py --plan-file docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md --engine-revision 087e66622f27350f1999d2e5b2ec82a9ead78982 --output artifacts/m3-v2.0.3/reference-check.json
```

Run each cell as a separate immutable artifact. Required filenames:

- `marginal-null-<GENERATOR>.json`
- `marginal-mde-<GENERATOR>.json`
- `family-null-<GENERATOR>-rho-0p0.json`, `...-rho-0p5.json`, `...-rho-0p9.json`
- `family-mde-<GENERATOR>-rho-0p0.json`, `...-rho-0p5.json`, `...-rho-0p9.json`

Example command:

```bash
python research/m3_hac_mbb_v2_calibration.py --phase family-null --generator N3_AR1_GAUSSIAN --rho 0.5 --plan-file docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md --engine-revision 087e66622f27350f1999d2e5b2ec82a9ead78982 --output artifacts/m3-v2.0.3/family-null-N3_AR1_GAUSSIAN-rho-0p5.json
```

Run all 40 cells (5 marginal-null + 5 marginal-MDE + 15 family-null + 15 family-MDE). Do not overwrite a cell artifact. A rerun must use a new campaign directory and preserve the original outcome.

After all 40 cell files exist, aggregate and validate them:

```bash
python research/aggregate_m3_hac_mbb_v2.py --input-dir artifacts/m3-v2 --plan-file docs/M3_HAC_MBB_V2_3_CALIBRATION_PLAN.md --reference-check artifacts/m3-v2.0.3/reference-check.json --output artifacts/m3-v2.0.3/campaign-summary.json
```

The runner computes the plan SHA-256 from the actual plan file and verifies that the plan, runner, and engine files match the clean Git checkout. The runner revision is taken from `HEAD`, not caller-supplied metadata; the engine revision must resolve to a commit containing the exact checked-out engine file. The reference check records the same provenance. The aggregator recomputes the plan hash, verifies the clean checkout and exact source bindings, and checks reference/cell provenance, cell hashes, complete seed sequences, return hashes, trial membership, realized family correlations, all cell counts, and frozen acceptance thresholds. A missing, failed, overwritten, or inconsistent cell prevents a valid campaign summary.
