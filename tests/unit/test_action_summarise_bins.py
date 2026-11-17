"""Unit tests for binned statistics and metrics-cache summarise output."""

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


def _logger() -> MagicMock:
    """Return a workflow logger that prints nothing."""
    logger = MagicMock()
    logger.is_terminal_logging = False
    return logger


def _entry(values: Dict[str, Any]) -> Dict[str, Any]:
    """Return an aggregation entry holding metric values in its result."""
    return {
        "matrix_values": {"seed": 1},
        "metadata": {"provenance": {}, "result": values},
        "cache_path": "test.db",
    }


def _run(
    entries: List[Dict[str, Any]],
    metric: List[str],
    output: Any,
    **extra: Any,
) -> Any:
    """Run summarise with the supplied entries and parameters."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    return AnalysisActionProvider().run(
        action="summarise",
        parameters={
            "_aggregation_entries": entries,
            "metric": metric,
            "output": str(output),
            **extra,
        },
        mode="run",
        context=None,
        logger=_logger(),
    )


def test_bin_and_pct_stats(tmp_path: Any) -> None:
    """A bin counts values in a half-open range and pct reports them."""
    entries = [_entry({"x": value}) for value in (0.2, 0.6, 0.8)]
    result = _run(
        entries,
        ["x.bin(0.5, 0.9) as binned", "x.pct(0.5, 0.9) as percent"],
        tmp_path / "summary.csv",
    )

    assert result[0] == "success"
    assert result[1]["binned"] == 2
    assert result[1]["percent"] == pytest.approx(200.0 / 3.0)


def test_bin_boundaries_are_lower_inclusive(tmp_path: Any) -> None:
    """A value on the lower bound is included; the upper bound is not."""
    entries = [_entry({"x": value}) for value in (0.5, 0.9)]
    result = _run(
        entries,
        ["x.bin(0.5, 0.9) as binned"],
        tmp_path / "summary.csv",
    )

    assert result[1]["binned"] == 1


def test_list_values_are_flattened(tmp_path: Any) -> None:
    """List-valued fields contribute each element to the statistics."""
    entries = [
        _entry({"x": [0.1, 0.5, 0.9]}),
        _entry({"x": [0.55, 0.95]}),
    ]
    result = _run(
        entries,
        ["x.count as n", "x.mean as mean", "x.bin(0.5, 1.0) as high"],
        tmp_path / "summary.csv",
    )

    assert result[1]["n"] == 5
    assert result[1]["mean"] == pytest.approx(0.6)
    assert result[1]["high"] == 4


def test_pct_of_empty_values_is_empty(tmp_path: Any) -> None:
    """A percentage over no values is an empty cell, not a division error."""
    entries = [_entry({"other": 1.0})]
    result = _run(
        entries,
        ["x.pct(0.5, 1.0) as percent"],
        tmp_path / "summary.csv",
    )

    assert result[1]["percent"] == ""


def test_bare_alias_reference_copies_a_column(tmp_path: Any) -> None:
    """A specification that is a bare alias copies the earlier column."""
    entries = [_entry({"x": 0.8})]
    result = _run(
        entries,
        ["x.mean as value", "value as copied"],
        tmp_path / "summary.csv",
    )

    assert result[1]["value"] == pytest.approx(0.8)
    assert result[1]["copied"] == pytest.approx(0.8)


def test_metrics_cache_output(tmp_path: Any) -> None:
    """A .db output returns a metrics object instead of a table."""
    entries = [_entry({"x": 0.8})]
    result = _run(
        entries,
        ["x.mean as value", "value as y"],
        tmp_path / "summary.db",
    )

    assert result[0] == "success"
    assert result[2][0]["type"] == "metrics"
    assert result[2][0]["format"] == "json"
    content = json.loads(result[2][0]["content"])
    assert content == {"value": 0.8, "y": 0.8}
    assert not (tmp_path / "summary.db").exists()


def test_metrics_cache_output_rejects_presentation_options(
    tmp_path: Any,
) -> None:
    """Table presentation options are invalid with a metrics cache."""
    entries = [_entry({"x": 0.8})]
    with pytest.raises(Exception, match="does not support"):
        _run(
            entries,
            ["x.mean as value"],
            tmp_path / "summary.db",
            headers=["mean"],
        )


def test_bin_bounds_accept_infinities() -> None:
    """The top and bottom buckets can use infinite bounds."""
    from causaliq_analysis.workflow_action.actions.summarise.columns import (
        _parse_column_spec,
    )

    top = _parse_column_spec("x.pct(0.95, inf) as high")
    bottom = _parse_column_spec("x.bin(-inf, 0.5) as low")

    assert top.bounds == (0.95, float("inf"))
    assert bottom.bounds == (float("-inf"), 0.5)


def test_bin_spec_accepts_where_clause() -> None:
    """A binned column can restrict the entries it draws on."""
    from causaliq_analysis.workflow_action.actions.summarise.columns import (
        _parse_column_spec,
    )

    spec = _parse_column_spec("x.pct(0.1, 0.2) where seed == 1 as b")

    assert spec.where == "seed == 1"
    assert spec.bounds == (0.1, 0.2)


def test_summarise_cache_rejects_significance() -> None:
    """A significance table cannot be written as a metrics cache."""
    from causaliq_analysis.workflow_action.actions.summarise.execution import (
        _summarise_cache,
    )
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    with pytest.raises(ActionExecutionError, match="significance requires"):
        _summarise_cache(
            {"significance": [object()], "is_aggregation": True},
            None,
            None,
        )


def test_summarise_cache_requires_input_files() -> None:
    """A metrics cache needs scanned input entries."""
    from causaliq_analysis.workflow_action.actions.summarise.execution import (
        _summarise_cache,
    )
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    with pytest.raises(ActionExecutionError, match="requires 'input'"):
        _summarise_cache(
            {"significance": [], "is_aggregation": False},
            None,
            None,
        )


def test_cache_metadata_records_filter_and_output_path() -> None:
    """The cache metadata records the filter and the open cache path."""
    from types import SimpleNamespace

    from causaliq_analysis.workflow_action.actions.summarise.execution import (
        _cache_metadata,
    )

    request = {"metric_specs": ["x.mean"], "filter": "seed == 1"}
    context = SimpleNamespace(cache=SimpleNamespace(db_path="out.db"))

    metadata = _cache_metadata(request, context, 1, ["a.db"])

    assert metadata["filter"] == "seed == 1"
    assert metadata["output_path"] == "out.db"


@pytest.mark.parametrize(
    "spec, message",
    [
        ("x.bin(0.9, 0.5) as b", "lower bound is above"),
        ("x.bin(0.0, 0.5) / x.count as b", "must be its own column"),
        ("x.bin(a, 0.5) as b", "is not a number"),
    ],
)
def test_invalid_binned_specs(
    tmp_path: Any,
    spec: str,
    message: str,
) -> None:
    """Invalid binned specifications are rejected."""
    entries = [_entry({"x": 0.8})]
    with pytest.raises(Exception, match=message):
        _run(entries, [spec], tmp_path / "summary.csv")
