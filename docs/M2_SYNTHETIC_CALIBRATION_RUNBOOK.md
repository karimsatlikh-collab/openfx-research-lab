# Running the M2 synthetic calibration campaign

The pre-registration is `docs/M2_SYNTHETIC_CALIBRATION_PLAN_V1.md`. Do not
edit its thresholds or seed allocation after seeing results.

Run from the repository root after the calibration implementation is frozen:

```bash
python -m unittest discover -s tests -p "test_m2_*.py" -v
python scripts/run_m2_calibration.py --output-dir calibration-artifacts/m2-v1
```

The campaign runs 20,000 deterministic replicates (5 null cells and 15
power cells), each with 100 synthetic observations. It writes raw JSONL
records and an aggregate JSON report. Preserve the entire output directory
as evidence; never overwrite an earlier campaign. The runner should refuse
to overwrite an existing output directory.

The plan's leakage fixture matrix is a separate required acceptance item.
Passing the return-generator campaign alone is not sufficient to close
Issue #24. Results are synthetic only and do not establish market validity.
