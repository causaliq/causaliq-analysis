"""Unit tests for rendering significance tables."""

import csv
from typing import Any

import pytest

from causaliq_analysis.workflow_action.actions.summarise import (
    render_significance,
    significance_specs,
)
from causaliq_analysis.workflow_action.types import ActionExecutionError

_csv_labels = render_significance._csv_labels
_significance_lines = render_significance._significance_lines
_write_significance = render_significance._write_significance
_parse_significance_specs = significance_specs._parse_significance_specs

_Row = tuple[dict[str, Any], dict[str, Any]]
_ALIASES = {"bnsl", "fusion", "llm"}


def _request(**overrides: Any) -> dict[str, Any]:
    """Build a significance request over three comparisons."""
    specs = _parse_significance_specs(
        [
            "wilcoxon-signed-rank-2-sided(fusion, bnsl) as Fusion vs BNSL",
            "wilcoxon-signed-rank-2-sided(fusion, llm) as Fusion vs LLM",
            "wilcoxon-signed-rank-2-sided(fusion, llm) as Fusion vs best solo",
        ],
        _ALIASES,
    )
    request: dict[str, Any] = {
        "significance": specs,
        "headers": [],
        "format": [],
        "caption": None,
        "output": None,
    }
    request.update(overrides)
    return request


def _rows() -> list[_Row]:
    """Build three significance result rows."""
    return [
        (
            {},
            {
                "comparison": "Fusion vs BNSL",
                "statistic": 17.0,
                "p_value": 6.169e-06,
                "significance": "***",
            },
        ),
        (
            {},
            {
                "comparison": "Fusion vs LLM",
                "statistic": 3.0,
                "p_value": 1.773e-05,
                "significance": "***",
            },
        ),
        (
            {},
            {
                "comparison": "Fusion vs best solo",
                "statistic": 36.0,
                "p_value": 0.0001448,
                "significance": "***",
            },
        ),
    ]


# Test the Markdown table holds a caption, headers, alignment and rows.
def test_markdown_significance_table() -> None:
    """The Markdown table renders the default columns and formats."""
    lines = _significance_lines(".md", _request(), _rows())
    assert lines[0] == (
        "## STATISTICAL TESTS (Wilcoxon signed-rank, two-sided)"
    )
    assert lines[1] == ""
    assert lines[2] == "| Comparison | W | p | Significance |"
    assert lines[3] == "| :--- | ---: | ---: | :--- |"
    assert lines[4] == "| Fusion vs BNSL | 17.0 | 0.0000 | *** |"


# Test the LaTeX table is a tabular fragment with a caption comment.
def test_latex_significance_table() -> None:
    """The LaTeX table holds a tabular, a rule and the result rows."""
    lines = _significance_lines(".tex", _request(), _rows())
    assert lines[0] == "% STATISTICAL TESTS (Wilcoxon signed-rank, two-sided)"
    assert lines[1] == r"\begin{tabular}{lrrl}"
    assert lines[2] == r"Comparison & W & p & Significance \\"
    assert lines[3] == r"\hline"
    assert lines[4] == r"Fusion vs BNSL & 17.0 & 0.0000 & *** \\"
    assert lines[-1] == r"\end{tabular}"


# Test declared headers and formats override the defaults.
def test_custom_headers_and_formats() -> None:
    """Headers and formats apply to the four significance columns."""
    request = _request(
        headers=["Comparison", "W", "p", ""],
        format=["", ">7.1f", ".4f", ""],
    )
    lines = _significance_lines(".md", request, _rows())
    assert lines[2] == "| Comparison | W | p |  |"
    assert "17.0" in lines[4]


# Test a null format hides its column from the presentation table.
def test_hidden_significance_column() -> None:
    """A hidden column disappears from Markdown but not from CSV."""
    request = _request(
        headers=["Comparison", "W", "p"],
        format=["", ".1f", ".4f", None],
    )
    lines = _significance_lines(".md", request, _rows())
    assert lines[2] == "| Comparison | W | p |"
    assert "***" not in "\n".join(lines)
    assert _csv_labels(request) == [
        "Comparison",
        "W",
        "p",
        "Significance",
    ]


# Test a declared caption replaces the default heading.
def test_caption_override() -> None:
    """A declared caption is used verbatim."""
    lines = _significance_lines(".md", _request(caption="Custom"), _rows())
    assert lines[0] == "## Custom"


# Test an empty caption suppresses the heading.
def test_empty_caption() -> None:
    """An empty caption leaves the table without a heading."""
    lines = _significance_lines(".md", _request(caption=""), _rows())
    assert lines[0] == "| Comparison | W | p | Significance |"


# Test a CSV output writes raw values and default labels.
def test_csv_significance_table(tmp_path: Any) -> None:
    """A .csv output holds the comparison, W, p and stars columns."""
    output = tmp_path / "significance.csv"
    _write_significance(_request(output=str(output)), _rows(), None)
    with open(output, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == ["Comparison", "W", "p", "Significance"]
    assert rows[0]["Comparison"] == "Fusion vs BNSL"
    assert float(rows[0]["W"]) == pytest.approx(17.0)
    assert float(rows[0]["p"]) == pytest.approx(6.169e-06)
    assert rows[0]["Significance"] == "***"


# Test a hidden column remains in CSV output.
def test_csv_keeps_hidden_column(tmp_path: Any) -> None:
    """CSV output names every column, including a hidden one."""
    output = tmp_path / "significance.csv"
    request = _request(
        output=str(output),
        headers=["Comparison", "W", "p"],
        format=["", ".1f", ".4f", None],
    )
    _write_significance(request, _rows(), None)
    with open(output, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == ["Comparison", "W", "p", "Significance"]


# Test the writer reports the file it wrote.
def test_write_significance_logs(tmp_path: Any) -> None:
    """A successful write reports the output path."""
    messages: list[str] = []
    output = tmp_path / "significance.md"
    _write_significance(
        _request(output=str(output)),
        _rows(),
        messages.append,
    )
    assert messages == [f"Significance table written to {output}"]


# Test a write failure is reported as an action error.
def test_write_significance_failure(tmp_path: Any) -> None:
    """An unwritable destination raises ActionExecutionError."""
    with pytest.raises(
        ActionExecutionError,
        match="Failed to write significance table",
    ):
        _write_significance(_request(output=str(tmp_path)), _rows(), None)


# Test detailed significance tables use the six-column default format.
def test_detail_default_formats() -> None:
    """Detailed comparisons default to six presentation columns."""
    request = _request(significance_detail=True)
    formats = render_significance._declared_formats(
        request, request["significance"]
    )
    assert formats == ["", "d", "d", "+.3f", ".1f", ".4f"]
