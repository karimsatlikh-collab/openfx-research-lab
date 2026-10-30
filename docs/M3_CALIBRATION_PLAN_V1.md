# M3 Selection-Bias Gate Calibration Plan v1

Status: **pre-registered plan; campaign not yet run**.

- Plan ID: `M3-CALIBRATION-V1`
- Target implementation: `M3-HOLM-BLOCK-BOOTSTRAP-V1`, version `1.0.0`
- Target source branch/head at freeze: `research/m3-selection-bias-engine-v1` / `c08035e1de8d3047323b906011b56bb328cd2270`
- Freeze date: 2026-10-30 UTC
- Primary purpose: evaluate the finite-sample behavior of the marginal circular moving-block-bootstrap test and the Holm family-wise correction under predeclared synthetic distributions.
- Evidence class: synthetic only. This campaign cannot establish market profitability or validate any trading strategy.

## 1. Frozen M3 v1 method settings

The production gate must enforce these exact values; callers may not lower them or select alternatives within method version 1:

| Setting | Frozen value |
|---|---:|
| One-sided null | mean net return <= 0 |
| Family-wise alpha | 0.05 |
| Bootstrap replicates | 9,999 |
| Minimum aligned observations | 252 |
| Sample length for this campaign | 252 |
| Circular moving-block length | ceil(n^(1/3)) = 7 |
| Monte Carlo p-value | (1 + exceedances) / 10,000 |
| Multiple-testing correction | Holm step-down |
| Trial accounting | all unique registered attempts; ineligible/non-completed p=1 |

Any change to one of these settings requires a new method or calibration version and a new pre-registration. The campaign will not tune block length, alpha, bootstrap count, sample length, or MDE after observing results.

## 2. Return generators

Every generated series has 252 observations and unit unconditional standard deviation before any planted mean shift. All random seeds are deterministic and disjoint between null and alternative campaigns.

| ID | Null generator | Definition |
|---|---|---|
| N1 | Gaussian IID | independent N(0,1) observations |
| N2 | Student-t IID | t(5) innovations scaled by sqrt(3/5), giving unit variance |
| N3 | AR(1)-Gaussian | x[t] = 0.30*x[t-1] + sqrt(1-0.30^2)*epsilon[t], epsilon ~ N(0,1) |
| N4 | GARCH(1,1) | omega=0.05, alpha=0.05, beta=0.90, Gaussian innovations; unconditional variance 1 |
| N5 | AR(1)-Student-t | AR(1) coefficient 0.30 with variance-standardized t(5) innovations |

For each null generator, the campaign runs 1,000 independent deterministic replicates. The one-sided null false-positive rate is measured at nominal alpha=0.05. The complete p-value sample is retained.

## 3. Planted-effect campaign

For each of the same five generators, create 1,000 independent deterministic replicates with a constant positive mean shift of **+0.35 pre-shift standard deviations per observation**. This is the predeclared minimum detectable effect (MDE) for this synthetic calibration. The shift is added after the null process is generated; no other parameters change.

The campaign reports power and a two-sided 95% Wilson interval for every generator. The MDE is fixed before the run; no effect size may be substituted after results are observed.

## 4. Family-size and dependence stress

The marginal null and MDE p-value samples above are used to form predeclared empirical marginal distributions. A separate Gaussian-copula stress campaign then constructs complete families using those empirical p-value marginals:

- Family sizes: 5 and 20 trials.
- Cross-trial Gaussian-copula correlations: 0.0, 0.5, and 0.9.
- 100,000 deterministic families per (generator, family-size, correlation) cell.
- Global-null cells contain only null p-values.
- Power cells contain one MDE alternative at the first deterministic trial ID and (m-1) null trials.
- Each family is evaluated with the exact Holm step-down rule and deterministic trial-ID tie breaking.

This copula stress is a **p-value dependence model**, not a substitute for direct return-level simulations of correlated strategies. Results must be labelled accordingly. Holm's theoretical FWER guarantee is conditional on valid marginal p-values and applies under arbitrary dependence; the copula campaign is a finite-sample implementation stress, not a proof of that theorem.

## 5. Deterministic seed map

- Null data seeds: `10,000,000 + generator_index*100,000 + replicate_index`.
- Alternative data seeds: `20,000,000 + generator_index*100,000 + replicate_index`.
- Bootstrap resampling seeds are deterministically derived from the corresponding replicate seed plus the fixed bootstrap-seed offset in the runner.
- Copula seeds: `30,000,000 + generator_index*1,000,000 + family_size_index*100,000 + correlation_index*10,000 + replicate_index`.
- Generator order is N1, N2, N3, N4, N5; replicate indices are 0 through 999; correlation order is 0.0, 0.5, 0.9; family-size order is 5, 20.

No seed is dropped or replaced. Failed replicates remain in the raw ledger with a failure reason and count toward the denominator; a campaign with any failed replicate is not accepted until rerun under a new campaign ID with all original outcomes preserved.

## 6. Metrics and acceptance

For each null generator:
- Report false-positive count / 1,000, point estimate, and two-sided 95% Wilson interval.
- Acceptance: observed FPR <= 5.5% and Wilson upper bound <= 6.5%.

For each MDE generator:
- Report power count / 1,000, point estimate, and two-sided 95% Wilson interval.
- Acceptance: Wilson lower bound >= 80%.

For every family-size/correlation copula cell:
- Report global-null family-wise error rate (FWER) and two-sided 95% Wilson interval.
- Acceptance: observed FWER <= 5.5% and Wilson upper bound <= 6.5%.
- Report MDE family-wise detection power and two-sided 95% Wilson interval.
- Acceptance: Wilson lower bound >= 80%.

Additional required checks:
- All Holm results must match an independent reference implementation on deterministic edge cases.
- Re-running the same campaign under the same code/runtime versions and seed map must reproduce canonical summaries and hashes exactly.
- All 5 null generators and all 5 alternative generators must complete all 1,000 replicates.
- All 30 global-null and 30 MDE copula cells (5 generators x 2 family sizes x 3 correlations) must complete all 100,000 families.
- Preserve raw p-values, per-replicate return-series hashes, seed map, cell-level counts, Wilson intervals, runtime versions, source revision, and campaign output hash.

A failure of any criterion means M3 v1 calibration is **not accepted**. No threshold, generator, seed, MDE, or family-size/correlation cell may be removed or redefined after seeing results.

## 7. Interpretation limits

- These are synthetic calibration results only, not real-market evidence.
- The bootstrap's stationarity/mixing assumptions can fail under structural breaks, regime changes, long memory, or other non-stationary market behavior.
- The Gaussian-copula stress does not model every possible dependence structure among strategy return series.
- A successful M3 calibration does not replace Issue #24 acceptance, independent statistical review, data/cost provenance, or untouched final-OOS validation.
- A statistical family pass is not a profitability guarantee and does not authorize broad optimization, deployment, MT5/VPS use, broker access, or live trading.

## 8. Stop conditions

Stop and mark the campaign inconclusive if:
- any frozen input, method setting, source revision, seed, or raw result changes unexpectedly;
- any return series is non-finite, malformed, or has a mismatched deterministic hash;
- any cell has a missing/failed replicate;
- the independent Holm implementation disagrees;
- output reproducibility fails;
- a code change is needed after the campaign starts.

A code fix requires a new source revision, a new calibration plan version, and a new campaign ID. The original campaign and its failures must remain preserved.
