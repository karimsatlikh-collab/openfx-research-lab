# M3 Method Candidate v2 — HAC-Studentized Moving-Block Bootstrap + Holm

Status: **executable research candidate; not accepted, not calibrated, not market-validated**.

- Method ID: `M3-HOLM-HAC-MBB-V2`
- Version: `2.0.1`
- Candidate implementation: `openfx/selection_bias_v2.py`
- Primary correction: Holm step-down family-wise error control.
- Marginal test: one-sided HAC-studentized mean test using a null-centered circular moving-block bootstrap.
- This version is separate from M3 v1. M3 v1 code and results remain unchanged.

## 1. Why v2 is a separate candidate

M3 v1 used the ordinary sample standard deviation to studentize the observed and bootstrap means. Its pre-registered calibration failed under Student-t(5) and AR(1) null generators. An exploratory, non-pre-registered pilot suggested that HAC/Newey-West studentization may improve marginal null calibration, but did not establish family-wise control. The pilot is recorded in `docs/M3_HAC_MBB_V2_EXPLORATORY_PILOT.md`; it is not acceptance evidence.

The v2 candidate changes the marginal studentization method while retaining the family registry and Holm correction. The 2.0.1 hardening additionally binds every completed trial to the frozen source revision and blocks evaluations that exceed a deterministic bootstrap-work budget. It must pass a new, independently pre-registered calibration before it can replace v1.

## 2. Frozen v2 candidate settings

| Setting | Frozen candidate value |
|---|---|
| Null hypothesis | E[r] <= 0 |
| Alternative | E[r] > 0 |
| Family-wise alpha | 0.05 |
| Bootstrap replicates | 9,999 |
| Minimum aligned observations | 252 |
| Maximum observations per trial | 100,000 |
| Maximum registered trials in a family | 10,000 |
| Maximum estimated bootstrap work | 1,000,000,000 units (`replicates × eligible_trials × n × (HAC_lag+1)`) |
| Circular moving-block length | ceil(n^(1/3)) |
| HAC kernel | Newey-West/Bartlett |
| HAC lag | ceil(n^(1/3)) |
| HAC covariance denominator | n |
| Bootstrap p-value | (1 + exceedances) / 10,000 |
| Multiplicity correction | Holm step-down |
| Failed/ineligible attempts | Retained in family with p=1 |

At n=252, both block length and HAC lag equal 7. The implementation rejects a manifest that changes method ID/version, alpha, bootstrap count, minimum sample, HAC kernel, HAC lag rule, or block-length rule.

## 3. Marginal statistic

For a return vector r[1..n], calculate:

1. Sample mean: r-bar.
2. Centered observations: u[t] = r[t] - r-bar.
3. Newey-West/Bartlett long-run variance:

   LRV = gamma[0] + 2 * sum(k=1..q) [(1 - k/(q+1)) * gamma[k]]

   where gamma[k] = (1/n) * sum(t=k+1..n) u[t]u[t-k], and q=ceil(n^(1/3)).

4. Studentized statistic: T = r-bar / sqrt(LRV/n).

Reject degenerate or non-finite long-run variance inputs as ineligible.

## 4. Bootstrap procedure

For every eligible completed trial:

1. Center the observed return vector by subtracting its sample mean to impose the null boundary.
2. Generate 9,999 circular moving-block-bootstrap samples of length n with block length L=ceil(n^(1/3)).
3. Use the same resampled time indices across all eligible trials in a family for each bootstrap replicate.
4. Recalculate the HAC-studentized statistic for each bootstrap sample using the same Bartlett kernel and lag rule.
5. Count a degenerate bootstrap draw conservatively as an exceedance.
6. Calculate the one-sided Monte Carlo p-value: (1 + count(T* >= T_observed))/10,000.
7. Apply Holm to the complete registered family, with every failed, non-completed, or ineligible attempt assigned p=1.

The family-level verdict is PASS only if at least one eligible trial is rejected by Holm. A statistical PASS is not a profitability guarantee.

## 5. Registry and evidence requirements

The evaluator consumes the complete verified local registry family snapshot, not a caller-supplied candidate list or count. Every trial must have a pending registration bound to the frozen family-manifest digest before execution. The manifest binds family ID, data profile, cost profile, validation split, return frequency, source revision, trial budget, method ID/version, and all statistical settings.

Completed trial inputs must have:
- finite net portfolio returns;
- matching data, cost, split, return-frequency, and exact source-revision bindings;
- timezone-aware, valid, strictly increasing timestamps;
- exactly aligned timestamps across eligible candidates;
- a canonical SHA-256 return-series hash;
- at least 252 observations.

Final OOS is not read or evaluated by the function. Failed and ineligible attempts remain in the family with p=1.

The manifest source revision must be a 40- or 64-character lowercase Git SHA. The validation payload of every completed trial must carry that exact source_revision; a mismatch is excluded with p=1. The evaluator blocks before bootstrap sampling if its estimated work exceeds the frozen one-billion-unit budget.

The local hash-chain registry remains a prototype, not an independently trusted registrar. A privileged actor can rewrite the entire ledger. The boolean `registered_before_execution` is an application-level assertion, not cryptographic proof of wall-clock ordering.

## 6. Known statistical risks

- The HAC/MBB candidate has only exploratory pilot evidence. Its finite-sample marginal p-values are not yet calibrated.
- HAC lag q=ceil(n^(1/3)) and block length L=ceil(n^(1/3)) are candidate rules; they have not been validated across broad sample lengths, regimes, and dependence structures.
- Newey-West/HAC estimators can be biased or unstable in short samples, under strong dependence, structural breaks, and long memory.
- Circular moving-block bootstrap validity relies on time-series regularity assumptions that may fail for market returns.
- Holm controls FWER under arbitrary dependence only when the marginal p-values are valid. v2 has not yet established this.
- The Gaussian-copula p-value stress from v1 is not direct return-level simulation and is not sufficient for v2 acceptance.
- No DSR, PBO, Sharpe deflation, or profitability claim is made.

## 7. Why Holm remains the baseline correction

Holm is retained because it provides family-wise error control under arbitrary dependence when valid marginal p-values are supplied. Resampling-based stepdown methods such as Romano–Wolf can exploit dependence and may improve power, but their validity depends on the method's assumptions and construction. The v2 task is first to validate the marginal time-series test and the family boundary; changing both the marginal test and multiplicity correction at once would make failures harder to diagnose.

References:
- Romano, J. P. and Wolf, M. (2005), “Exact and Approximate Stepdown Methods for Multiple Hypothesis Testing,” *JASA* 100(469), 94–108. DOI: https://doi.org/10.1198/016214504000000539
- Romano, J. P. and Wolf, M. (2005), “Stepwise Multiple Testing as Formalized Data Snooping,” *Econometrica* 73(4), 1237–1282. DOI: https://doi.org/10.1111/j.1468-0262.2005.00615.x

## 8. Acceptance boundary

This document is a method candidate, not an authorization to use v2 for strategy selection. Before acceptance:
- freeze a new v2 calibration plan and disjoint seeds;
- quantify how many marginal null replicates are needed to resolve the smallest Holm threshold for the declared maximum family size;
- run direct return-level correlated-trial family simulations;
- test Gaussian, heavy-tail, serial-correlation, volatility-clustering, and combined nulls;
- test predeclared weaker, MDE, and stronger effects;
- preserve all p-values, series hashes, seeds, runtime versions, failed replicates, and output hashes;
- independently reproduce the calculations;
- obtain independent statistical review.

Until Issue #24 and Issue #27 are independently accepted, broad parameter-grid optimization and final-winner selection remain disabled. No MT5, VPS, broker, paid service, or live trading is enabled.
