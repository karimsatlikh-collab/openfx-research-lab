"""Conservative parser for English MT5 Strategy Tester HTML summary tables.

This parser accepts explicit label/value rows only. It rejects missing or ambiguous
metrics and is not a substitute for validating a real terminal/build-specific report.
"""
from __future__ import annotations

import math
import re
from html.parser import HTMLParser
from typing import Any

_MAX_REPORT_CHARS = 5 * 1024 * 1024
_LABELS = {
    "total net profit": "net_profit",
    "net profit": "net_profit",
    "gross profit": "gross_profit",
    "gross loss": "gross_loss",
    "profit factor": "profit_factor",
    "expected payoff": "expected_payoff",
    "total trades": "trade_count",
    "maximal drawdown": "max_drawdown_pct",
    "maximum drawdown": "max_drawdown_pct",
    "max drawdown": "max_drawdown_pct",
    "relative drawdown": "relative_drawdown_pct",
}
_NUMBER_RE = re.compile(r"^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$")


class _TableRows(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
            self._cell = None


def _normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().rstrip(":")).casefold()


def _parse_number(value: str, field: str) -> float:
    cleaned = value.strip().replace("\u00a0", " ")
    cleaned = re.sub(r"(?i)\b(?:USD|EUR|GBP|JPY|AUD|CAD|CHF)\b", "", cleaned)
    cleaned = re.sub(r"[$€£¥\s]", "", cleaned)
    cleaned = cleaned.rstrip("%")
    if not _NUMBER_RE.fullmatch(cleaned):
        raise ValueError(f"unsupported numeric format for {field}: {value!r}")
    try:
        number = float(cleaned.replace(",", ""))
    except ValueError:
        raise ValueError(f"invalid number for {field}") from None
    if not math.isfinite(number):
        raise ValueError(f"non-finite number for {field}")
    return number


def _parse_drawdown_percent(value: str, field: str) -> float:
    parenthetical = re.search(r"\(\s*([+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?)\s*%\s*\)", value)
    if parenthetical:
        return _parse_number(parenthetical.group(1), field)
    standalone = re.fullmatch(r"\s*([+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?)\s*%\s*", value)
    if standalone:
        return _parse_number(standalone.group(1), field)
    raise ValueError(f"{field} must include an explicit percentage")


def parse_mt5_report_html(content: Any) -> dict[str, Any]:
    """Extract required metrics from English MT5 HTML table label/value pairs."""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("report HTML must be a non-empty string")
    if len(content) > _MAX_REPORT_CHARS:
        raise ValueError("report HTML exceeds the 5 MiB text limit")

    parser = _TableRows()
    parser.feed(content)
    found: dict[str, str] = {}
    for row in parser.rows:
        for index, cell in enumerate(row):
            normalized = _normalize_label(cell)
            # Support both a label cell followed by a value cell and "Label: value".
            inline_label = None
            inline_value = None
            if ":" in cell:
                prefix, remainder = cell.split(":", 1)
                if _normalize_label(prefix) in _LABELS and remainder.strip():
                    inline_label, inline_value = _LABELS[_normalize_label(prefix)], remainder.strip()
            key = inline_label or _LABELS.get(normalized)
            if key is None:
                continue
            value = inline_value
            if value is None and index + 1 < len(row):
                value = row[index + 1]
            if not value:
                continue
            if key in found and found[key] != value:
                raise ValueError(f"ambiguous duplicate report metric: {key}")
            found[key] = value

    required = {
        "net_profit", "gross_profit", "gross_loss", "profit_factor",
        "expected_payoff", "trade_count", "max_drawdown_pct", "relative_drawdown_pct",
    }
    missing = required - set(found)
    if missing:
        raise ValueError("report is missing required English metrics: " + ", ".join(sorted(missing)))

    metrics: dict[str, Any] = {
        "net_profit": _parse_number(found["net_profit"], "net_profit"),
        "gross_profit": _parse_number(found["gross_profit"], "gross_profit"),
        "gross_loss": abs(_parse_number(found["gross_loss"], "gross_loss")),
        "expected_payoff": _parse_number(found["expected_payoff"], "expected_payoff"),
        "max_drawdown_pct": _parse_drawdown_percent(found["max_drawdown_pct"], "max_drawdown_pct"),
        "relative_drawdown_pct": _parse_drawdown_percent(found["relative_drawdown_pct"], "relative_drawdown_pct"),
    }
    pf_value = found["profit_factor"].strip().casefold()
    metrics["profit_factor"] = None if pf_value in {"n/a", "na", "--", "not available"} else _parse_number(pf_value, "profit_factor")
    trades = _parse_number(found["trade_count"], "trade_count")
    if trades < 0 or not trades.is_integer():
        raise ValueError("trade_count must be a non-negative integer")
    metrics["trade_count"] = int(trades)
    if not 0 <= metrics["max_drawdown_pct"] <= 100 or not 0 <= metrics["relative_drawdown_pct"] <= 100:
        raise ValueError("drawdown percentages must be between 0 and 100")

    warnings = []
    if metrics["gross_loss"] > 0 and metrics["profit_factor"] is not None:
        expected_pf = metrics["gross_profit"] / metrics["gross_loss"]
        if not math.isclose(metrics["profit_factor"], expected_pf, rel_tol=0.05, abs_tol=0.05):
            warnings.append("profit_factor_differs_from_gross_profit_over_gross_loss")
    if metrics["trade_count"] > 0 and not math.isclose(
        metrics["expected_payoff"],
        metrics["net_profit"] / metrics["trade_count"],
        rel_tol=0.05,
        abs_tol=0.05,
    ):
        warnings.append("expected_payoff_differs_from_net_profit_per_trade")

    return {
        "parser_version": "openfx-mt5-html/0.1",
        "metrics": metrics,
        "parsed_labels": sorted(found),
        "warnings": warnings,
        "scope": "english_html_summary_parser_not_terminal_or_profitability_verification",
    }


def compare_report_metrics(parsed_report: dict[str, Any], result_manifest: dict[str, Any]) -> dict[str, Any]:
    """Compare parsed report metrics with the declared result metrics."""
    parsed_metrics = parsed_report.get("metrics") if isinstance(parsed_report, dict) else None
    declared_metrics = result_manifest.get("metrics") if isinstance(result_manifest, dict) else None
    if not isinstance(parsed_metrics, dict) or not isinstance(declared_metrics, dict):
        raise ValueError("parsed report and result manifest must contain metrics objects")
    fields = (
        "net_profit", "gross_profit", "gross_loss", "profit_factor",
        "expected_payoff", "trade_count", "max_drawdown_pct", "relative_drawdown_pct",
    )
    mismatches = []
    for field in fields:
        actual, declared = parsed_metrics.get(field), declared_metrics.get(field)
        if actual is not None and (
            not isinstance(actual, (int, float)) or isinstance(actual, bool) or not math.isfinite(actual)
        ):
            raise ValueError(f"parsed report metric {field} must be finite numeric data or null")
        if declared is not None and (
            not isinstance(declared, (int, float)) or isinstance(declared, bool) or not math.isfinite(declared)
        ):
            raise ValueError(f"declared metric {field} must be finite numeric data or null")
        if actual is None and declared is None:
            continue
        if actual is None or declared is None:
            mismatches.append(field)
        elif field == "trade_count":
            if not isinstance(actual, int) or isinstance(actual, bool) or actual != declared:
                mismatches.append(field)
        elif not math.isclose(float(actual), float(declared), rel_tol=0.01, abs_tol=0.05):
            mismatches.append(field)
    return {
        "status": "matched" if not mismatches else "mismatch",
        "mismatched_metrics": mismatches,
        "scope": "declared_metrics_vs_parsed_report_not_profitability_verification",
    }
