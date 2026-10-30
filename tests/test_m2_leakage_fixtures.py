import unittest

from openfx.leakage_controls import (
    LeakageDetected, assert_available_by, assert_feature_window_within_split,
    assert_final_oos_access, assert_ordered_splits,
)


class LeakageFixtureTests(unittest.TestCase):
    def test_future_bar_timestamp_is_detected(self):
        with self.assertRaises(LeakageDetected):
            assert_available_by(
                value_name="future_bar_close",
                available_at="2025-01-01T10:15:00+00:00",
                decision_at="2025-01-01T10:00:00+00:00",
            )

    def test_timezone_omission_fails_closed(self):
        with self.assertRaises(LeakageDetected):
            assert_available_by(
                value_name="bar",
                available_at="2025-01-01T09:55:00",
                decision_at="2025-01-01T10:00:00+00:00",
            )

    def test_target_label_availability_is_checked(self):
        with self.assertRaises(LeakageDetected):
            assert_available_by(
                value_name="target_label",
                available_at="2025-01-02T00:00:00+00:00",
                decision_at="2025-01-01T23:59:00+00:00",
            )

    def test_revised_historical_data_is_checked_by_revision_time(self):
        with self.assertRaises(LeakageDetected):
            assert_available_by(
                value_name="revised_bar",
                available_at="2025-01-03T12:00:00+00:00",
                decision_at="2025-01-02T12:00:00+00:00",
            )

    def test_split_overlap_and_cross_boundary_feature_window_are_detected(self):
        with self.assertRaises(LeakageDetected):
            assert_ordered_splits(
                development_end="2025-01-10T00:00:00+00:00",
                validation_start="2025-01-09T00:00:00+00:00",
                validation_end="2025-01-20T00:00:00+00:00",
                final_oos_start="2025-01-21T00:00:00+00:00",
            )
        with self.assertRaises(LeakageDetected):
            assert_feature_window_within_split(
                window_start="2025-01-09T23:00:00+00:00",
                window_end="2025-01-10T01:00:00+00:00",
                split_start="2025-01-10T00:00:00+00:00",
                split_end="2025-01-20T00:00:00+00:00",
            )

    def test_final_oos_cannot_be_exposed_to_search_roles(self):
        for audience in ("proposer", "optimizer"):
            with self.assertRaises(LeakageDetected):
                assert_final_oos_access(split_name="final_oos", audience=audience)
        assert_final_oos_access(split_name="final_oos", audience="authorized_human")
        assert_final_oos_access(split_name="validation", audience="optimizer")

    def test_unknown_audience_fails_closed(self):
        with self.assertRaises(LeakageDetected):
            assert_final_oos_access(split_name="validation", audience="unknown")


if __name__ == "__main__":
    unittest.main()
