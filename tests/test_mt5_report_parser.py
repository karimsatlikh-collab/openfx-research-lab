import unittest

from openfx.mt5_report_parser import compare_report_metrics, parse_mt5_report_html


def report_html(net_profit="250.00", profit_factor="2.00"):
    return f"""
    <html><body><table>
      <tr><td>Total Net Profit:</td><td>{net_profit}</td></tr>
      <tr><td>Gross Profit:</td><td>500.00</td></tr>
      <tr><td>Gross Loss:</td><td>-250.00</td></tr>
      <tr><td>Profit Factor:</td><td>{profit_factor}</td></tr>
      <tr><td>Expected Payoff:</td><td>2.50</td></tr>
      <tr><td>Total Trades:</td><td>100</td></tr>
      <tr><td>Maximal Drawdown:</td><td>1,200.00 (12.00%)</td></tr>
      <tr><td>Relative Drawdown:</td><td>800.00 (8.00%)</td></tr>
    </table></body></html>
    """


class MT5ReportParserTests(unittest.TestCase):
    def test_parses_required_english_summary_metrics(self):
        result = parse_mt5_report_html(report_html())
        self.assertEqual(result["metrics"]["net_profit"], 250.0)
        self.assertEqual(result["metrics"]["gross_loss"], 250.0)
        self.assertEqual(result["metrics"]["trade_count"], 100)
        self.assertEqual(result["metrics"]["max_drawdown_pct"], 12.0)
        self.assertEqual(result["metrics"]["relative_drawdown_pct"], 8.0)
        self.assertEqual(result["warnings"], [])

    def test_missing_metric_is_rejected(self):
        html = report_html().replace("<tr><td>Profit Factor:</td><td>2.00</td></tr>", "")
        with self.assertRaisesRegex(ValueError, "missing required English metrics"):
            parse_mt5_report_html(html)

    def test_ambiguous_duplicate_metric_is_rejected(self):
        html = report_html() + "<table><tr><td>Total Net Profit:</td><td>999.00</td></tr></table>"
        with self.assertRaisesRegex(ValueError, "ambiguous duplicate"):
            parse_mt5_report_html(html)

    def test_ambiguous_decimal_comma_format_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported numeric format"):
            parse_mt5_report_html(report_html(net_profit="1.234,56"))

    def test_parsed_metrics_match_declared_result(self):
        parsed = parse_mt5_report_html(report_html())
        declared = {"metrics": {
            "net_profit": 250.0, "gross_profit": 500.0, "gross_loss": 250.0,
            "profit_factor": 2.0, "expected_payoff": 2.5, "trade_count": 100,
            "max_drawdown_pct": 12.0, "relative_drawdown_pct": 8.0,
        }}
        self.assertEqual(compare_report_metrics(parsed, declared)["status"], "matched")

    def test_report_manifest_metric_mismatch_is_flagged(self):
        parsed = parse_mt5_report_html(report_html())
        declared = {"metrics": {
            "net_profit": 251.0, "gross_profit": 500.0, "gross_loss": 250.0,
            "profit_factor": 2.0, "expected_payoff": 2.5, "trade_count": 100,
            "max_drawdown_pct": 12.0, "relative_drawdown_pct": 8.0,
        }}
        comparison = compare_report_metrics(parsed, declared)
        self.assertEqual(comparison["status"], "mismatch")
        self.assertEqual(comparison["mismatched_metrics"], ["net_profit"])


if __name__ == "__main__":
    unittest.main()
