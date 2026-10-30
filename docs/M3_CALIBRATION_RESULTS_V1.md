# M3 Calibration Results v1

Status: **NOT ACCEPTED — calibration criteria failed**.

This is synthetic calibration only. It is not market evidence and does not establish profitability.

## Execution provenance

- Plan: `M3-CALIBRATION-V1`
- Plan SHA-256: `039ce5adaf1c5bd6c3df93c760f6702149fcd61db25c861e2eefbec18fb15cca`
- Production engine revision: `c08035e1de8d3047323b906011b56bb328cd2270`
- Independent runner revision: `e2edcfc9ac35007ca0f55f2381f4543b83e04ead`
- Campaign SHA-256: `26f9a912c04a954672c465ee75bf27d27ed68dd6a21952853e22e6df49399e03`
- Raw JSON file SHA-256: `dfa675b0074b0e169695ff3be290c9ffa3f6946a86f13e1c25a65275a03b5f5b`
- Runtime: Python 3.13, NumPy 2.3.5, Numba 0.65.1.
- Execution: independent NumPy/Numba calculations in the ChatGPT Python runtime, using the runner's predeclared generators, seeds, bootstrap, and Holm procedure. The full campaign was **not** run by GitHub Actions; CI validated project syntax and existing tests only.
- Completed: 5,000 null series + 5,000 planted-effect series; 30 global-null and 30 MDE copula cells, 100,000 families per cell; zero failed replicates.

## Marginal null false-positive rate

Acceptance: point estimate <=5.5% and two-sided 95% Wilson upper bound <=6.5%.

| Generator | False positives | FPR | 95% Wilson interval | Result |
|---|---:|---:|---:|---|
| N1 Gaussian IID | 48/1,000 | 4.8% | 3.64%–6.31% | PASS |
| N2 Student-t(5) IID | 61/1,000 | 6.1% | 4.78%–7.76% | FAIL |
| N3 AR(1)-Gaussian, phi=0.30 | 66/1,000 | 6.6% | 5.22%–8.31% | FAIL |
| N4 GARCH(1,1) | 48/1,000 | 4.8% | 3.64%–6.31% | PASS |
| N5 AR(1)-Student-t(5) | 59/1,000 | 5.9% | 4.60%–7.54% | FAIL |

Only 2/5 marginal null generators passed.

## Marginal MDE power

Predeclared MDE: +0.35 standard deviations per observation. Acceptance: lower 95% Wilson bound >=80%.

| Generator | Detections | Power | 95% Wilson interval | Result |
|---|---:|---:|---:|---|
| N1 Gaussian IID | 1,000/1,000 | 100.0% | 99.62%–100.00% | PASS |
| N2 Student-t(5) IID | 999/1,000 | 99.9% | 99.44%–99.98% | PASS |
| N3 AR(1)-Gaussian, phi=0.30 | 995/1,000 | 99.5% | 98.83%–99.79% | PASS |
| N4 GARCH(1,1) | 1,000/1,000 | 100.0% | 99.62%–100.00% | PASS |
| N5 AR(1)-Student-t(5) | 987/1,000 | 98.7% | 97.79%–99.24% | PASS |

All 5 marginal MDE power cells passed.

## Family-wise copula stress

The copula is applied to empirical marginal p-value distributions; it is a p-value dependence stress, **not** a direct simulation of correlated strategy return series.

### Global-null FWER

Acceptance: point estimate <=5.5% and two-sided 95% Wilson upper bound <=6.5%.

| Generator | m=5, rho=0 | m=5, rho=.5 | m=5, rho=.9 | m=20, rho=0 | m=20, rho=.5 | m=20, rho=.9 |
|---|---:|---:|---:|---:|---:|---:|
| N1 Gaussian IID | 6.29% | 5.06% | 2.75% | 9.49% | 5.92% | 1.95% |
| N2 Student-t(5) IID | 8.21% | 6.48% | 3.56% | 16.73% | 9.63% | 3.33% |
| N3 AR(1)-Gaussian | 7.28% | 5.78% | 3.22% | 7.88% | 5.10% | 1.60% |
| N4 GARCH(1,1) | 6.75% | 5.56% | 2.96% | 9.55% | 5.94% | 1.97% |
| N5 AR(1)-Student-t(5) | 8.13% | 6.49% | 3.60% | 9.64% | 6.01% | 1.93% |

Only 12/30 global-null cells passed. Observed FWER range: 1.60%–16.73%.

### Family-wise MDE power

All 30/30 cells passed the lower 95% Wilson bound >=80% criterion. Family-wise power ranged from 87.77% to 99.92%.

## Calibration diagnosis

The campaign does **not** support accepting M3 v1.

1. Three marginal null generators failed the pre-registered false-positive criteria: Student-t(5), AR(1)-Gaussian, and AR(1)-Student-t(5).
2. Eighteen of 30 empirical-copula global-null cells failed the family-wise criterion.
3. For a 20-trial family, the first Holm threshold is 0.05/20 = 0.0025. Estimating that tail from only 1,000 marginal null replicates is too sparse: only a handful of observations determine the empirical tail. The resulting copula FWER estimates are therefore noisy and should not be interpreted as precise estimates of the true FWER.
4. The marginal FPR failures at nominal 0.05 remain a genuine warning independent of the copula-tail issue.
5. The independent calibration implementation uses NumPy PCG64 bootstrap indices rather than the production module's Python `random.Random` stream. The resampling distribution and statistical procedure match, but exact random streams and exact per-seed p-values are not expected to match.

## Decision and next step

- M3 v1 calibration is **not accepted**.
- Do not enable broad optimization, final-winner selection, MT5, VPS, broker access, or live trading.
- Preserve the v1 method and all outcomes; do not tune v1 against this same campaign.
- Next research step: design M3 v2 with a defensible tail-calibration sample size for the smallest Holm threshold, stronger marginal null calibration under heavy tails and serial dependence, and a direct correlated-return family simulation. Pre-register v2 with disjoint seeds before execution.
