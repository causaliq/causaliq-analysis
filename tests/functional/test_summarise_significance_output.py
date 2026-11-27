"""Functional tests for summarise significance output."""

import csv
import json
from types import SimpleNamespace
from typing import Any

import pytest
from scipy.stats import wilcoxon

_NETWORKS = ["alarm", "asia", "barley", "child", "sports", "water"]

_BNSL = [0.5, 0.55, 0.4, 0.45, 0.3, 0.35]

_LLM = [0.4, 0.45, 0.3, 0.35, 0.2, 0.25]

_FUSION = [0.9, 0.85, 0.8, 0.75, 0.7, 0.65]

_METRIC = [
    "f1.mean[1] as bnsl",
    "f1.mean[2] as llm",
    "f1.mean[3] as fusion",
    "max(bnsl, llm) as best_solo",
]

_SIGNIFICANCE = [
    "wilcoxon-signed-rank-2-sided(fusion, bnsl) as Fusion vs BNSL",
    "wilcoxon-signed-rank-2-sided(fusion, llm) as Fusion vs LLM",
    "wilcoxon-signed-rank-2-sided(fusion, best_solo) as Fusion vs best solo",
]


def _write_cache(path: Any, values: list[float]) -> str:
    """Write a cache holding one F1 value per network.

    Args:
        path: Destination cache path.
        values: F1 values in network order.

    Returns:
        The cache path as a string.
    """
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    with WorkflowCache(str(path)) as cache:
        for network, value in zip(_NETWORKS, values):
            entry = CacheEntry(
                metadata={
                    "provenance": {},
                    "result": {"status": "ok"},
                }
            )
            entry.add_object(
                "metrics",
                "json",
                json.dumps({"f1": value}),
                "evaluate_graph",
            )
            cache.put({"network": network}, entry)
    return str(path)


def _inputs(tmp_path: Any) -> list[str]:
    """Build the three input caches of the worked example."""
    return [
        _write_cache(tmp_path / "bnsl.db", _BNSL),
        _write_cache(tmp_path / "llm.db", _LLM),
        _write_cache(tmp_path / "fusion.db", _FUSION),
    ]


def _context() -> Any:
    """Build a workflow context grouping by network."""
    return SimpleNamespace(
        matrix={"network": _NETWORKS},
        matrix_values={"network": _NETWORKS[0]},
        cache=None,
    )


def _run(
    tmp_path: Any,
    significance: list[str],
    output_name: str = "significance.md",
    **extra: Any,
) -> Any:
    """Run the summarise action with significance tests."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    parameters: dict[str, Any] = {
        "metric": _METRIC,
        "significance": significance,
        "input": _inputs(tmp_path),
        "output": str(tmp_path / output_name),
    }
    parameters.update(extra)
    return AnalysisActionProvider().run(
        action="summarise",
        parameters=parameters,
        mode="run",
        context=_context(),
        logger=SimpleNamespace(is_terminal_logging=False),
    )


def _expected_p() -> str:
    """Return the formatted paired p-value of the worked example."""
    return format(wilcoxon(_FUSION, _BNSL).pvalue, ".4f")


# Test the significance workflow writes the comparison table.
def test_significance_markdown_output(tmp_path: Any) -> None:
    """The Markdown output holds the three comparisons and stars."""
    result = _run(tmp_path, _SIGNIFICANCE)
    text = (tmp_path / "significance.md").read_text(encoding="utf-8")
    assert result[0] == "success"
    assert "## STATISTICAL TESTS (Wilcoxon signed-rank, two-sided)" in text
    assert "| Comparison | W | p | Significance |" in text
    assert f"| Fusion vs BNSL | 0.0 | {_expected_p()} | * |" in text
    assert "| Fusion vs LLM | 0.0 |" in text
    assert "| Fusion vs best solo | 0.0 |" in text


# Test omitting the label derives it from the operand aliases.
def test_significance_default_labels(tmp_path: Any) -> None:
    """A test without an as clause uses its aliases as the label."""
    significance = [
        "wilcoxon-signed-rank-2-sided(fusion, bnsl)",
        "wilcoxon-signed-rank-2-sided(fusion, llm)",
    ]
    _run(tmp_path, significance)
    text = (tmp_path / "significance.md").read_text(encoding="utf-8")
    assert "| fusion vs bnsl | 0.0 |" in text
    assert "| fusion vs llm | 0.0 |" in text


# Test a CSV output holds the raw test results.
def test_significance_csv_output(tmp_path: Any) -> None:
    """The CSV output holds comparison, W, p and stars columns."""
    _run(tmp_path, _SIGNIFICANCE, output_name="significance.csv")
    path = tmp_path / "significance.csv"
    with open(path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == ["Comparison", "W", "p", "Significance"]
    assert rows[0]["Comparison"] == "Fusion vs BNSL"
    assert float(rows[0]["W"]) == pytest.approx(0.0)
    assert float(rows[0]["p"]) == pytest.approx(
        wilcoxon(_FUSION, _BNSL).pvalue
    )
    assert rows[0]["Significance"] == "*"


# Test the result metadata records the test results.
def test_significance_metadata(tmp_path: Any) -> None:
    """The action metadata holds the computed significance rows."""
    result = _run(tmp_path, _SIGNIFICANCE)
    assert result[1]["significance"][0]["comparison"] == "Fusion vs BNSL"
    assert result[1]["significance"][0]["statistic"] == pytest.approx(0.0)
    assert result[1]["table_output"].endswith("significance.md")


# Test significance requires input caches.
def test_significance_requires_input(tmp_path: Any) -> None:
    """A significance table cannot be built from a single entry set."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    with pytest.raises(ActionValidationError, match="requires 'input'"):
        AnalysisActionProvider().run(
            action="summarise",
            parameters={
                "_aggregation_entries": [],
                "metric": _METRIC,
                "significance": _SIGNIFICANCE,
                "output": str(tmp_path / "significance.md"),
            },
            mode="run",
            context=None,
            logger=SimpleNamespace(is_terminal_logging=False),
        )


# Test a footer is rejected on a significance table.
def test_significance_rejects_footer(tmp_path: Any) -> None:
    """A significance table has no footer row."""
    from causaliq_core import ActionValidationError

    with pytest.raises(ActionValidationError, match="not supported"):
        _run(tmp_path, _SIGNIFICANCE, footer=["note"])


# Test the format parameter must have four entries.
def test_significance_format_count(tmp_path: Any) -> None:
    """The format list covers the four significance columns."""
    from causaliq_core import ActionValidationError

    with pytest.raises(ActionValidationError, match="4 entries"):
        _run(tmp_path, _SIGNIFICANCE, format=["", ".1f", ".4f"])


# Test the headers parameter follows the visible column count.
def test_significance_headers_count(tmp_path: Any) -> None:
    """A hidden column reduces the number of declared headers."""
    from causaliq_core import ActionValidationError

    with pytest.raises(ActionValidationError, match="3 entries"):
        _run(
            tmp_path,
            _SIGNIFICANCE,
            format=["", ".1f", ".4f", None],
            headers=["Comparison", "W", "p", "Significance"],
        )


# Test a significance test must name a declared metric alias.
def test_significance_unknown_alias(tmp_path: Any) -> None:
    """An operand that is not a metric alias is rejected."""
    from causaliq_core import ActionValidationError

    with pytest.raises(ActionValidationError, match="Unknown column"):
        _run(
            tmp_path,
            ["wilcoxon-signed-rank-2-sided(fusion, missing)"],
        )


# Test the caption must be text.
def test_significance_invalid_caption(tmp_path: Any) -> None:
    """A non-string caption is rejected."""
    from causaliq_core import ActionValidationError

    with pytest.raises(ActionValidationError, match="must be a string"):
        _run(tmp_path, _SIGNIFICANCE, caption=123)


# Test an invalid format specification is rejected.
def test_significance_invalid_format(tmp_path: Any) -> None:
    """A format specification Python cannot apply is rejected."""
    from causaliq_core import ActionValidationError

    with pytest.raises(ActionValidationError, match="Invalid format spec"):
        _run(tmp_path, _SIGNIFICANCE, format=["", "i3", ".4f", ""])


# Test every significance column may not be hidden.
def test_significance_all_hidden(tmp_path: Any) -> None:
    """At least one significance column must remain visible."""
    from causaliq_core import ActionValidationError

    with pytest.raises(ActionValidationError, match="at least one visible"):
        _run(
            tmp_path,
            _SIGNIFICANCE,
            format=[None, None, None, None],
        )


# Test the filter is recorded in significance metadata.
def test_significance_filter_metadata(tmp_path: Any) -> None:
    """A filtered significance run records the filter expression."""
    result = _run(
        tmp_path,
        _SIGNIFICANCE,
        filter="network == 'alarm'",
    )
    assert result[0] == "success"
    assert result[1]["filter"] == "network == 'alarm'"


# Test headers without a format list cover all four columns.
def test_significance_headers_without_format(tmp_path: Any) -> None:
    """Four headers are valid when no column is hidden."""
    result = _run(
        tmp_path,
        _SIGNIFICANCE,
        headers=["Comparison", "W", "p", "Significance"],
    )
    assert result[0] == "success"


# Test headers follow a hidden significance column.
def test_significance_hidden_headers(tmp_path: Any) -> None:
    """A hidden stars column leaves three visible column headers."""
    result = _run(
        tmp_path,
        _SIGNIFICANCE,
        format=["", ".1f", ".4f", None],
        headers=["Comparison", "W", "p"],
    )
    text = (tmp_path / "significance.md").read_text(encoding="utf-8")
    assert result[0] == "success"
    assert "| Comparison | W | p |" in text
    assert "***" not in text
