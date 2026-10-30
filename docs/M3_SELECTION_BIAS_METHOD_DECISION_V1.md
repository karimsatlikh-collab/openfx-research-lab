# M3 Selection-Bias Correction Method Decision v1

Status: **method decision and pre-implementation protocol**. This document is a frozen engineering proposal for review; it is not evidence that the correction is implemented, calibrated, or valid on market data. No broad parameter search is authorized by this document.

- Protocol ID: `M3-HOLM-BLOCK-BOOTSTRAP-V1`
- Version: `1.0.0`
- Primary method: **one-sided moving-block-bootstrap p-values with Holm step-down family-wise error correction**.
- Nominal family-wise alpha: `0.05`.
- Bootstrap replicates: `9999`.
- Minimum aligned observations per eligible trial: `252`.
- Bootstrap block length: `ceil(n^(1/3))`, fixed from the eligible sample length before resampling.
- Return frequency: one common, predeclared calendar frequency per family (daily portfolio returns by default); no mixing frequencies within a family.

## 1. Why this method

OpenFX needs a family-level selection control that does not assume independent strategy variants. Holm's step-down procedure controls family-wise error under arbitrary dependence between valid marginal p-values. A synchronized moving-block bootstrap is selected to estimate each trial's one-sided mean-return p-value while retaining local serial dependence; the same resampled time indices are used for every trial so cross-trial dependence is retained in the resampling experiment.

This is a deliberately narrower v1 than claiming DSR or PBO. **No DSR, PBO, Sharpe-deflation, or other correction is claimed or implemented by this protocol.** The method tests whether at least one registered candidate has positive mean net return at the declared return frequency, after the family-wide correction. It does not estimate the probability of backtest overfitting, prove economic value, or guarantee future profitability.

## 2. Trial and family definitions

### Trial unit
A trial is one uniquely registered, executable research attempt with a frozen tuple of:
- strategy/specification and implementation/build digest;
- parameter/configuration digest;
- symbol/universe and timeframe;
- data profile and split manifest;
- cost profile and execution assumptions;
- return-frequency and metric definition.

A changed parameter, code/build, timeframe, symbol/universe, data snapshot, cost assumption, or other search choice that is actually evaluated is a **new trial**. A trial is registered before execution.

### Family boundary
A family is the complete search lineage for one research hypothesis/strategy idea over the declared instrument universe, timeframe variants, parameter variants, implementation revisions, and cost/data variants. A family must not be split after seeing results to reduce the correction burden. Related child searches inherit the parent family ID unless a documented, outcome-blind protocol change is approved before the child search starts. Renaming a family, changing a symbol/timeframe, or changing a parameter grid does not create an independent family.

The family manifest is frozen before validation results are inspected and binds:
- family ID and parent/lineage IDs;
- hypothesis/specification and search-space digest;
- declared trial budget and registry snapshot/root;
- data, costs, return frequency, development/validation/final-OOS split IDs;
- method/version, alpha, bootstrap count/block-length rule, minimum sample, and source revision.

### Counting and retries
Every unique attempted trial consumes one family slot and remains in the family, regardless of completed, failed, timeout, interrupted, rejected, cancelled, or abandoned outcome. A failed/non-completed trial receives no eligible return-series test and is assigned p=1 for multiplicity accounting. It cannot disappear from the denominator.

An exact idempotent transport retry is not a new trial only when it reuses the same trial ID and identical immutable request/config/build/data digests. Any changed input or genuinely re-executed search attempt receives a new trial ID and consumes another slot. A duplicate ID with changed content is a hard error.

## 3. Statistical procedure

### Inputs and eligibility
For every completed trial, require a finite, non-missing, timestamp-aligned vector of **net** portfolio returns after the frozen spread, commission, slippage, swap/funding, and other applicable costs. All completed candidates in a family must use the same timestamps, frequency, currency/normalization convention, and split boundaries. Costs may not be omitted or selectively changed after results.

Development results may support implementation/debugging but are not eligible for the final family verdict. The primary family correction is evaluated on the predeclared validation segment. Final OOS remains sealed and is not an input to candidate selection or this gate. Any use of final OOS is a separate, single, human-authorized evaluation and cannot feed back into search.

A completed trial is statistically ineligible if it has fewer than 252 aligned observations, missing timestamps, non-finite values, incompatible data/cost/split bindings, or an unverifiable artifact. Ineligible trials fail closed and remain counted with p=1; if the family has no eligible completed trial, the family verdict is BLOCKED.

### Marginal test
For each eligible trial (j), test the one-sided null (H_{0j}: E[r_j] \le 0) against (H_{1j}: E[r_j] > 0), where (r_j) is the aligned validation-period net portfolio return at the family frequency.

1. Calculate the observed studentized mean statistic (T_j = \bar r_j/(s_j/\sqrt n)). Reject degenerate/non-finite variance inputs as ineligible.
2. Center the observed return vector by subtracting its sample mean to impose the null boundary.
3. Generate 9,999 circular moving-block-bootstrap samples of length (n), with block length (L=\lceil n^{1/3}\rceil). Blocks wrap at the series boundary. The same bootstrap start indices are shared across all eligible trials in a family to preserve their cross-trial dependence.
4. Recalculate the studentized mean for every replicate. The one-sided Monte Carlo p-value is ((1 + \#\{T^* \ge T_{obs}\})/(9999+1)). The random seed is derived deterministically from the frozen family-manifest digest and method version; it is recorded in the verdict.
5. Ineligible and non-completed trials are assigned p=1 and remain in family size (m).

This bootstrap is an approximate time-series inference procedure. Its validity depends on the stationarity/mixing and sample-size assumptions being sufficiently reasonable; the gate must report this limitation and fail closed for unsupported data shapes rather than imply universal validity.

### Family-wise correction
Apply Holm step-down to all (m) registered trial p-values, including p=1 placeholders:
- Sort p-values (p_{(1)} \le \dots \le p_{(m)}), with deterministic trial-ID tie-breaking.
- At rank (i), compare (p_{(i)}) with (\alpha/(m-i+1)), alpha=0.05.
- Stop at the first non-rejection; no later hypothesis is rejected.
- Report raw p-values, Holm-adjusted p-values, rank, threshold, reject/not-reject decision, and the full registered family membership.

The family-level statistical result is PASS only if at least one eligible completed trial is rejected by Holm. This is evidence against the family-wide no-positive-mean null at the declared alpha under the method assumptions. It is not a profitability guarantee and does not authorize final-OOS access, deployment, or live trading.

## 4. Fail-closed rules

Return BLOCKED/INCONCLUSIVE, never PASS, when any of the following applies:
- registry integrity, family completeness, manifest freeze, or trial lineage cannot be verified;
- any attempted trial is absent from the registry snapshot or a family has been split/renamed without an outcome-blind approved lineage record;
- validation series are missing, non-finite, not aligned, too short, mixed-frequency, or bound to different data/cost/split digests;
- costs are absent or not applied consistently;
- final-OOS observations or metrics entered candidate selection or validation;
- bootstrap output is non-finite/degenerate or deterministic reproduction fails;
- required trial artifacts or source/build/config digests are missing;
- family budget is exceeded or method/configuration changed after freeze.

A local hash-chain ledger is not a trusted registrar: until a trusted, access-controlled registrar exists, the verdict must explicitly say that family completeness is not independently authenticated. A local ledger rewrite by a privileged actor remains a known threat.

## 5. Auditable verdict

The GateVerdict must bind at minimum:
- protocol/method ID and version; alpha; bootstrap count; block-length rule; deterministic seed;
- family ID, lineage IDs, frozen manifest digest, registry snapshot/root and every trial ID in deterministic order;
- each trial outcome, eligibility reason, return-series artifact hash, data/cost/split IDs, sample size, raw p-value, Holm-adjusted p-value, rank, threshold, and decision;
- selected/rejected candidate IDs (if any), but no final-OOS metrics;
- source commit/build digest, execution environment, calculation version, output artifact hashes, timestamp, and limitations.

Preserve raw aligned series or immutable references to them, all intermediate bootstrap statistics (or a reproducible seed+algorithm record plus output digest), the complete registry snapshot, and the canonical verdict. Reproduction must recompute from frozen inputs and compare canonical outputs within predeclared floating-point tolerances.

## 6. Calibration and adversarial acceptance

This method is not accepted until a separate pre-registered calibration campaign passes. The calibration plan must be committed before execution and must use seed ranges disjoint from tuning/debug fixtures.

### Required synthetic designs
- Multiple null families: IID Gaussian, heavy-tailed, heteroskedastic, AR/serially correlated, regime-switching, and volatility-clustered returns.
- Correlated trial families: near-duplicate candidates, shared signal/noise components, mixed positive/negative correlations, and large families with many variants.
- Planted effects at a declared minimum detectable effect (MDE), plus weaker and stronger references, with the MDE frozen before the campaign.
- Include both short-memory and difficult/non-stationary fixtures. Unsupported regimes must be explicitly classified; they must not be silently counted as passes.
- All replicates retain exact denominators and raw outcomes. Report family-wise false-positive rates and 95% binomial confidence intervals, plus power and intervals at the MDE.

### Numerical acceptance
- For every declared in-scope null/correlation family, the upper 95% confidence bound for family-wise false positives must be <=5%.
- At the predeclared MDE, the lower 95% confidence bound for family-wise detection power must be >=80%.
- Repeatability: same frozen inputs, source/runtime, and seed produce identical canonical p-values/verdicts.
- Independent reproduction recomputes bootstrap indices, marginal p-values, Holm adjustment, and verdict from the raw frozen series.

### Adversarial tests
Reject omitted/hidden trials, family splitting/renaming, changed config after results, altered registry snapshots, duplicate IDs with changed content, missing/changed costs, missing timestamps, misaligned series, NaN/Inf, insufficient observations, non-finite/zero variance, final-OOS leakage, and proposer feedback from final OOS. Verify failed/rejected/interrupted/abandoned attempts remain in (m), and exact idempotent retries do not inflate (m).

## 7. Scope boundaries and open risks

- This is a proposal for a first correction gate, not a market validation result.
- Holm controls family-wise error only if marginal p-values are valid; the block bootstrap's finite-sample validity under structural breaks, long memory, and non-stationarity is not guaranteed.
- The chosen statistic tests positive mean net return at a fixed frequency; it does not directly test risk-adjusted Sharpe, drawdown acceptability, tail risk, capacity, or economic utility. Those remain separate gates.
- The method is conservative and may have low power for large correlated families. The calibration campaign must quantify this; thresholds must not be tuned on the same seeds used for acceptance.
- Final-OOS remains sealed. A validation PASS does not grant access to it.
- No DSR/PBO implementation, market data, MT5, VPS, broker, paid API/compute, or live trading is included or authorized.

## 8. Implementation sequence

1. Review/approve this method decision and resolve the statistical assumptions before code.
2. Add immutable family-manifest and full-family snapshot APIs; do not accept a caller-supplied trial count or hand-picked trial list.
3. Add aligned return-series artifact validation and deterministic circular moving-block bootstrap.
4. Add Holm step-down, canonical GateVerdict, provenance bindings, and fail-closed behavior.
5. Add unit, property, and adversarial tests.
6. Freeze a separate calibration protocol, run the synthetic campaign, retain all raw artifacts, and independently reproduce.
7. Only after independent review and acceptance may Issue #27 close. Broad optimization remains disabled until Issue #24 and Issue #27 are both accepted.
