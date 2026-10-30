import unittest

from openfx.calibration import (
    DECISION_THRESHOLD, EFFECTS, FAMILIES, MDE, N_OBSERVATIONS,
    REPLICATES_PER_CELL, canonical_json, generate_noise, run_cell,
    seed_cells, wilson_interval,
)


class CalibrationProtocolTests(unittest.TestCase):
    def test_frozen_families_and_seed_ranges_are_disjoint(self):
        cells = seed_cells()
        self.assertEqual(len(cells), 20)
        ranges = [(c["seed_start"], c["seed_end"]) for c in cells]
        self.assertEqual(len({seed for lo, hi in ranges for seed in range(lo, hi + 1)}), 20000)
        self.assertEqual(ranges[0], (100000, 100999))
        self.assertEqual(ranges[4], (104000, 104999))
        self.assertEqual(ranges[5], (200000, 200999))
        self.assertEqual(ranges[-1], (214000, 214999))
        self.assertEqual(FAMILIES, ("N-IID", "T5-IID", "HET-IID", "AR1-030", "CONTAM-05"))
        self.assertEqual(EFFECTS, (0.25, 0.40, 0.60))

    def test_generators_are_repeatable_and_have_exact_length(self):
        for family in FAMILIES:
            first = generate_noise(family=family, seed=777, n=N_OBSERVATIONS)
            second = generate_noise(family=family, seed=777, n=N_OBSERVATIONS)
            self.assertEqual(first, second)
            self.assertEqual(len(first), N_OBSERVATIONS)

    def test_generator_rejects_unknown_family_and_invalid_seed(self):
        with self.assertRaises(ValueError):
            generate_noise(family="made-up", seed=1)
        with self.assertRaises(ValueError):
            generate_noise(family="N-IID", seed=True)

    def test_wilson_interval_known_edges(self):
        low, high = wilson_interval(0, 1000)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)
        low, high = wilson_interval(1000, 1000)
        self.assertLess(low, 1.0)
        self.assertEqual(high, 1.0)
        low, high = wilson_interval(50, 100)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)

    def test_wilson_rejects_invalid_denominators_and_boolean_counts(self):
        for args in ((0, 0), (2, 1), (True, 10), (1, False)):
            with self.assertRaises(ValueError):
                wilson_interval(*args)

    def test_calibration_cell_enforces_frozen_size_and_effects(self):
        with self.assertRaises(ValueError):
            run_cell(kind="null", family="N-IID", effect=0.1, seed_start=1)
        with self.assertRaises(ValueError):
            run_cell(kind="power", family="N-IID", effect=0.3, seed_start=1)
        with self.assertRaises(ValueError):
            run_cell(kind="null", family="N-IID", effect=0.0, seed_start=1, count=10)

    def test_cell_has_exact_denominator_and_raw_seed_coverage(self):
        cell = run_cell(kind="null", family="N-IID", effect=0.0, seed_start=100000)
        self.assertEqual(cell["trials"], REPLICATES_PER_CELL)
        self.assertEqual(len(cell["records"]), REPLICATES_PER_CELL)
        self.assertEqual(cell["records"][0]["seed"], 100000)
        self.assertEqual(cell["records"][-1]["seed"], 100999)
        self.assertEqual(cell["records"][0]["evidence_level"], "synthetic")
        self.assertEqual(cell["acceptance"], cell["wilson_95_upper"] <= 0.05)
        repeat = run_cell(kind="null", family="N-IID", effect=0.0, seed_start=100000)
        self.assertEqual(cell, repeat)

    def test_canonical_serialization_rejects_nan(self):
        with self.assertRaises(ValueError):
            canonical_json({"bad": float("nan")})


if __name__ == "__main__":
    unittest.main()
