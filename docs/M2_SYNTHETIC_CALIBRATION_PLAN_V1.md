# M2 Synthetic Calibration Plan v1.0 (Pre-registered)

**Status: FROZEN BEFORE CALIBRATION EXECUTION.**  
**Plan ID:** `m2-synthetic-calibration-v1`  
**Protocol revision:** `1.0.0`  
**Evidence class:** synthetic only; never market evidence.  
**Dependency:** implementation files currently live on `openfx-foundation-m1-contracts`; this plan branch is based on that exact PR #23 head commit. It is not a claim that PR #23 is merged.

This document fixes the generators, sample sizes, seed ranges, decision rule, confidence intervals, leakage fixtures, repeatability contract, and acceptance criteria before the calibration campaign. Do not change this plan after inspecting calibration outcomes. A changed plan requires a new version, a documented reason, and entirely new calibration seed ranges. Preserve all prior outcomes.

## 1. Question and scope

The campaign tests whether the current simple synthetic decision rule can (a) control false positives on several predeclared no-edge return-generating processes and (b) detect a predeclared minimum synthetic mean shift with adequate power.

It does **not** validate a market strategy, model realistic market microstructure, prove profitability, validate DSR/PBO, or implement a multiple-testing correction. Issue #27 remains a separate prerequisite for actual selection-bias correction.

## 2. Frozen decision rule

Use the existing descriptive gate rule, without tuning it on calibration seeds:

- Return observations per replicate: `n = 100`.
- Null threshold: pass only when the arithmetic sample mean is `>= 0.25` synthetic return units.
- Planted-edge minimum detectable effect (MDE): additive mean shift `delta = +0.40` units per observation.
- Reference weaker effect: `delta = +0.25`.
- Reference stronger effect: `delta = +0.60`.
- Noise scale is normalized to marginal variance 1.0 in every generator family.
- One-sided decision is intentional because the gate is testing a positive-edge hypothesis. No threshold may be adjusted after seeing campaign results.

The MDE is a predeclared engineering target, not a claim that 0.40 is economically meaningful.

## 3. Null-generator families

For each family, execute 1,000 independent deterministic replicate seeds with zero location shift. Each replicate contains 100 observations. Use a documented deterministic PRNG and fixed transform order. All families have zero theoretical mean and marginal variance 1.

1. **N-IID:** independent standard normal observations.
2. **T5-IID:** independent Student-t with 5 degrees of freedom, multiplied by `sqrt(3/5)` to normalize variance to 1.
3. **HET-IID:** independent alternating scales `0.5` and `sqrt(1.75)` applied to standard normal draws; the two-position average variance is 1. The first observation uses scale 0.5.
4. **AR1-030:** stationary Gaussian AR(1), coefficient `phi=0.30`, innovation standard deviation `sqrt(1-phi^2)`, initialized from a standard normal draw. The stationary marginal variance is 1.
5. **CONTAM-05:** independent mixture; with probability 0.95 draw `N(0, 0.5^2)`, otherwise draw `N(0, 15.25)`. The unconditional variance is 1. The mixture selector and normal draws use the same seeded PRNG stream in the documented order.

The generator implementation must expose its family identifier and parameters in every raw replicate record. Any implementation deviation invalidates this plan version; do not silently substitute another distribution.

## 4. Power families and effects

For every generator family in section 3, run 1,000 deterministic seeds at each of these additive location shifts: `delta=0.25`, `delta=0.40` (MDE), and `delta=0.60`. Add the shift to every observation after generating the zero-mean noise sequence. Keep the same n=100 and decision threshold 0.25.

Report power separately for every family/effect pair. The acceptance criterion applies to the MDE in every family, not merely to pooled results. The weaker and stronger effects are reference curves and must still be reported, including any unexpected non-monotonicity.

## 5. Seed allocation (disjoint)

Use exactly these contiguous integer seed ranges, with one seed per replicate:

- Null family runs: `100000–104999`; allocate 1,000 seeds to each family in the order listed in section 3.
- Power runs: `200000–214999`; allocate 1,000 seeds to each family/effect pair in family-major, then effect-ascending order.
- Regression/repeatability fixtures: `900000–900099`; never use these seeds to estimate false-positive rate or power.
- Any development/debug seed must be outside all ranges above and must be recorded separately. It must never be included in reported calibration denominators.

Do not reuse a seed across calibration cells. Seed-to-cell mapping must be deterministic and recorded in the report.

## 6. Confidence intervals and denominators

For each cell, report integer successes, integer trials, observed rate, and a two-sided 95% Wilson score interval for the binomial proportion. Report the exact denominator (normally 1,000); never report rounded percentages without counts.

- Null acceptance: the **upper** 95% Wilson bound for false-positive rate must be `<= 0.05` for every null family.
- MDE power acceptance: the **lower** 95% Wilson bound for power at `delta=0.40` must be `>= 0.80` for every generator family.
- No pooling across families to conceal a failing family.
- Report weaker/stronger power cells even though they have no separate numerical acceptance threshold.
- If a cell has missing, duplicate, non-finite, or invalid records, fail that cell closed; do not reduce the denominator silently.

## 7. Leakage fixture matrix

Inject one or more deterministic fixtures for each category below. The fixture manifest must name the injected leak, the expected detector, and the expected result. The finite in-scope set is:

1. Future-bar feature timestamp later than decision timestamp.
2. Timestamp timezone omission or incomparable naive/aware timestamps.
3. Target/label value made available before its declared availability time.
4. Revised historical data whose revision timestamp is later than the simulated decision time.
5. Train/validation split boundary overlap or a feature window crossing the boundary.
6. Final-OOS observation/metric exposed to the development/optimizer interface.

Acceptance: 100% of the finite predeclared fixtures are rejected or explicitly detected by their named control. A fixture not covered by an implemented detector must be marked **out of scope / failed**, not counted as detected. Timestamp comparison alone must not be described as detecting target, revision, split, or OOS leakage.

## 8. Repeatability and provenance

For each run, retain canonical inputs and outputs, family/effect/seed mapping, Python version, OS/platform, source commit SHA, protocol ID, generator version, and decision-rule version. For identical frozen inputs and environment, canonical result records and return-stream hashes must match exactly. Timestamps and other intentionally nondeterministic metadata must be excluded from the canonical equality projection before execution and listed here; no fields may be excluded after observing differences.

Retain all raw replicate summaries, return hashes, failed seeds, false positives, false negatives, fixture artifacts, and aggregate report. Do not overwrite or delete failed or inconvenient outcomes. Calibration seeds and regression seeds remain disjoint.

## 9. Execution and review order

1. Review this frozen plan and its exact seed mapping.
2. Implement the generators, Wilson interval calculation, deterministic runner, canonical serialization, raw-result persistence, and finite leakage fixture harness.
3. Add unit tests for generator moments/parameters, seed uniqueness, confidence interval edge cases, malformed records, and fail-closed behavior.
4. Execute the campaign only after the implementation commit is frozen; record its commit SHA before running.
5. Produce machine-readable raw records and aggregate report.
6. Independently reproduce interval calculations and audit seed allocation and denominators.
7. Mark Issue #24 accepted only after all criteria pass and an independent review is recorded.

## 10. Stop conditions and non-claims

Stop and report failure if any null family exceeds its false-positive bound, any MDE family misses its power lower bound, any required leakage fixture is undetected, repeatability fails, or raw records cannot be reproduced. Do not tune and rerun on the same seeds. A revised design needs a new plan version and fresh seed ranges.

No market data, MT5, VPS, broker, paid API, live trading, DSR/PBO implementation, or profitability claim is part of this calibration.
