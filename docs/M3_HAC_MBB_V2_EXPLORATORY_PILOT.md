# M3 HAC-Studentized MBB v2 Candidate — Exploratory Pilot

Status: **exploratory only; not pre-registered; not accepted**.

This pilot was performed only to inform Issue #36 after M3 v1 failed. These results must not be reused as v2 acceptance evidence. Any formal v2 calibration must use a new frozen plan and disjoint seeds.

## Candidate procedure

- Circular moving-block bootstrap, block length L=7.
- Null-centered return samples.
- Studentized mean statistic uses Newey-West/Bartlett HAC long-run variance, not the ordinary sample variance.
- HAC lag q=7, Bartlett weights w(k)=1-k/(q+1).
- The same HAC statistic is calculated for the observed series and each bootstrap replicate.
- 9,999 bootstrap replicates; one-sided p-value; Holm step-down at alpha 0.05.

The pilot is a method variant, not a patch to M3 v1. The production M3 v1 module remains unchanged.

## Pilot A — 1,000 marginal null and MDE replicates per generator

Exploratory seed ranges:
- Null data: 110,000,000 + generator_index*100,000 + replicate_index.
- MDE data: 120,000,000 + generator_index*100,000 + replicate_index.
- Bootstrap seed: 150,000,000 + data seed.
- MDE: +0.35 standard deviations.

| Generator | Null FPR | 95% Wilson interval | Null diagnostic | MDE power | 95% Wilson lower |
|---|---:|---:|---|---:|---:|
| N1 Gaussian IID | 5.2% (52/1,000) | 3.99%–6.76% | Upper bound slightly above 6.5% | 100.0% | 99.62% |
| N2 Student-t(5) IID | 4.6% (46/1,000) | 3.47%–6.08% | Below 5.5% point threshold | 99.9% | 99.44% |
| N3 AR(1)-Gaussian | 4.5% (45/1,000) | 3.38%–5.97% | Below 5.5% point threshold | 99.3% | 98.56% |
| N4 GARCH(1,1) | 4.3% (43/1,000) | 3.21%–5.74% | Below 5.5% point threshold | 100.0% | 99.62% |
| N5 AR(1)-Student-t(5) | 4.9% (49/1,000) | 3.73%–6.42% | Below 5.5% point threshold | 99.0% | 98.17% |

This is a promising marginal diagnostic, but it is only an exploratory sample. No calibration acceptance is inferred.

## Pilot B — empirical p-value copula stress

- Family sizes: 5 and 20.
- Gaussian-copula correlations: 0.0, 0.5, 0.9.
- 100,000 families per cell.
- Five generators; 30 global-null cells and 30 one-MDE-candidate cells.
- This is dependence stress on empirical p-values, not direct return-level simulation of correlated strategies.

Results:
- Global-null FWER passed 26/30 exploratory cells using point FWER <=5.5% and 95% Wilson upper <=6.5%.
- Four exploratory cells did not pass:
  - N3 AR(1)-Gaussian, m=5, rho=0: 7.201%.
  - N3 AR(1)-Gaussian, m=5, rho=0.5: 5.826%.
  - N3 AR(1)-Gaussian, m=20, rho=0: 5.989%.
  - N4 GARCH(1,1), m=20, rho=0: 5.671%.
- MDE family-power lower 95% bounds passed 30/30 cells; lowest lower bound was 84.41%.
- Observed global-null FWER ranged from 0.489% to 7.201%.

The empirical marginal tail is still based on 1,000 replicates and is too sparse for strong conclusions at Holm's first m=20 threshold (0.0025). The copula results are diagnostics only.

## Pilot C — block-length sensitivity (ordinary sample-variance studentization)

200 null replicates per generator and block length; these are very small exploratory cells.

| Generator | L=7 | L=10 | L=14 | L=21 |
|---|---:|---:|---:|---:|
| N1 Gaussian IID | 5.0% | 7.5% | 7.5% | 7.5% |
| N2 Student-t(5) IID | 5.5% | 5.5% | 7.5% | 9.5% |
| N3 AR(1)-Gaussian | 7.0% | 7.0% | 6.0% | 7.0% |
| N4 GARCH(1,1) | 4.0% | 4.0% | 4.0% | 4.5% |
| N5 AR(1)-Student-t(5) | 6.0% | 5.5% | 6.0% | 4.5% |

Simply increasing the block length did not consistently improve null behavior. This does not justify selecting any alternative block length.

## Execution limits

- Runtime: Python 3.13, NumPy 2.3.5, Numba 0.65.1.
- Calculations were run independently in the ChatGPT Python runtime; not by GitHub Actions.
- No market data, MT5, broker, VPS, or live trading.
- No direct return-level correlated-trial family simulation was performed.
- No method or threshold has been accepted from this pilot.

## Decision

Carry the HAC-studentized statistic forward only as a **candidate** for a new method version. Before implementation or acceptance:
1. Freeze a new method ID and full protocol.
2. Quantitatively justify the number of marginal null replicates needed to estimate alpha/m tails for the declared maximum family size.
3. Run direct correlated-return family simulations.
4. Use disjoint seeds for formal v2 calibration.
5. Independently reproduce results and preserve all raw evidence.

See Issue #36. M3 v1 remains unaccepted and broad optimization remains disabled.
