"""Unit tests for summarise source-qualified columns and joins."""

import csv
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

_ENTRY = Tuple[Dict[str, Any], Dict[str, Any]]


def _write_cache(path: Any, entries: List[_ENTRY]) -> str:
    """Write a workflow cache holding one entry per matrix and result.

    Args:
        path: Destination cache path.
        entries: Matrix values and result metrics per entry.

    Returns:
        The cache path as a string.
    """
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    with WorkflowCache(str(path)) as cache:
        for matrix_values, results in entries:
            cache.put(
                matrix_values,
                CacheEntry(metadata={"provenance": {}, "result": results}),
            )
    return str(path)


def _context(networks: List[str]) -> Any:
    """Build a workflow context grouping by network."""
    return SimpleNamespace(
        matrix={"network": networks},
        matrix_values={"network": networks[0]},
        cache=None,
    )


def _logger() -> Any:
    """Build a logger that keeps terminal logging off."""
    return SimpleNamespace(is_terminal_logging=False)


def _run(
    tmp_path: Any,
    inputs: List[str],
    metric: List[str],
) -> Any:
    """Run the summarise action over two networks and return its result."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    parameters: Dict[str, Any] = {
        "metric": metric,
        "input": inputs,
        "output": str(tmp_path / "summary.csv"),
    }
    return AnalysisActionProvider().run(
        action="summarise",
        parameters=parameters,
        mode="run",
        context=_context(["alarm", "asia"]),
        logger=_logger(),
    )


def _rows(path: Any) -> List[Dict[str, str]]:
    """Read the summary rows of a CSV file."""
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# Test each source column takes its value from its own cache.
def test_columns_join_by_source(tmp_path: Any) -> None:
    """BNSL and LLM columns come from their own caches."""
    bnsl = _write_cache(
        tmp_path / "bnsl.db",
        [({"network": "alarm"}, {"node_count": 37, "f1": 0.8})],
    )
    llm = _write_cache(
        tmp_path / "llm.db",
        [({"network": "alarm"}, {"f1": 0.6})],
    )
    metric = ["node_count[1]", "f1.mean[1]", "f1.mean[2]"]
    result = _run(tmp_path, [bnsl, llm], metric)

    assert result[0] == "success"
    row = _rows(tmp_path / "summary.csv")[0]
    assert row["node_count[1]"] == "37"
    assert float(row["f1.mean[1]"]) == pytest.approx(0.8)
    assert float(row["f1.mean[2]"]) == pytest.approx(0.6)


# Test a derived column combines the source columns of a row.
def test_derived_column_over_sources(tmp_path: Any) -> None:
    """Fusion minus the best baseline is computed per row."""
    bnsl = _write_cache(
        tmp_path / "bnsl.db",
        [({"network": "asia"}, {"f1": 0.75})],
    )
    llm = _write_cache(
        tmp_path / "llm.db",
        [({"network": "asia"}, {"f1": 0.84})],
    )
    fusion = _write_cache(
        tmp_path / "fusion.db",
        [({"network": "asia"}, {"f1": 1.0})],
    )
    metric = [
        "f1.mean[1] as bnsl",
        "f1.mean[2] as llm",
        "f1.mean[3] as fusion",
        "fusion - max(bnsl, llm) as gain",
    ]
    _run(tmp_path, [bnsl, llm, fusion], metric)

    row = _rows(tmp_path / "summary.csv")[1]
    assert float(row["gain"]) == pytest.approx(0.16)


# Test a column without a source draws on every input cache.
def test_unqualified_column_unions_sources(tmp_path: Any) -> None:
    """A plain field-and-statistic column spans every input cache."""
    bnsl = _write_cache(
        tmp_path / "bnsl.db",
        [({"network": "alarm"}, {"f1": 0.8})],
    )
    llm = _write_cache(
        tmp_path / "llm.db",
        [({"network": "alarm"}, {"f1": 0.6})],
    )
    _run(tmp_path, [bnsl, llm], ["f1.mean", "f1.count"])

    row = _rows(tmp_path / "summary.csv")[0]
    assert int(row["f1.count"]) == 2
    assert float(row["f1.mean"]) == pytest.approx(0.7)


# Test a source index beyond the input list is rejected.
def test_source_index_out_of_range(tmp_path: Any) -> None:
    """A metric naming a missing input file fails validation."""
    from causaliq_core import ActionValidationError

    cache = _write_cache(
        tmp_path / "bnsl.db",
        [({"network": "alarm"}, {"f1": 0.8})],
    )
    with pytest.raises(ActionValidationError, match="names input file 2"):
        _run(tmp_path, [cache], ["f1.mean[2]"])


# Test a source-qualified cache must carry the grouping dimension.
def test_source_qualified_cache_requires_dimension(tmp_path: Any) -> None:
    """An entry without the grouping dimension is rejected, not joined."""
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    bnsl = _write_cache(
        tmp_path / "bnsl.db",
        [({"network": "alarm"}, {"f1": 0.8})],
    )
    llm = _write_cache(
        tmp_path / "llm.db",
        [({"seed": 0}, {"f1": 0.6})],
    )
    with pytest.raises(ActionExecutionError, match="grouping dimension"):
        _run(tmp_path, [bnsl, llm], ["f1.mean[1]", "f1.mean[2]"])


# Test a bare source field rejects conflicting values.
def test_bare_source_field_rejects_conflict(tmp_path: Any) -> None:
    """A field holding two distinct values cannot report one value."""
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    cache = _write_cache(
        tmp_path / "bnsl.db",
        [
            ({"network": "alarm", "seed": 0}, {"node_count": 37}),
            ({"network": "alarm", "seed": 1}, {"node_count": 38}),
        ],
    )
    with pytest.raises(ActionExecutionError, match="distinct values"):
        _run(tmp_path, [cache], ["node_count[1]"])


# Test a bare source field reports a value repeated across seeds.
def test_bare_source_field_repeats(tmp_path: Any) -> None:
    """A field holding one repeated value reports that value."""
    cache = _write_cache(
        tmp_path / "bnsl.db",
        [
            ({"network": "alarm", "seed": 0}, {"node_count": 37}),
            ({"network": "alarm", "seed": 1}, {"node_count": 37}),
        ],
    )
    _run(tmp_path, [cache], ["node_count[1]"])

    row = _rows(tmp_path / "summary.csv")[0]
    assert row["node_count[1]"] == "37"


# Test a missing field leaves the source column empty.
def test_missing_field_is_empty(tmp_path: Any) -> None:
    """A field absent from a cache reports an empty cell."""
    cache = _write_cache(
        tmp_path / "bnsl.db",
        [({"network": "alarm"}, {"other": 1.0})],
    )
    _run(tmp_path, [cache], ["f1.mean[1]"])

    row = _rows(tmp_path / "summary.csv")[0]
    assert row["f1.mean[1]"] == ""


# Test the one-based position of a cache in the input list.
def test_source_index_maps_cache_path() -> None:
    """A declared cache maps to its one-based position, others to zero."""
    from causaliq_analysis.workflow_action.actions.summarise.collect import (
        _source_index,
    )

    inputs = ["bnsl.db", "llm.db"]
    assert _source_index("llm.db", inputs) == 2
    assert _source_index("unknown.db", inputs) == 0
    assert _source_index("llm.db", []) == 0


# Test argmax reports the dimension of the winning entry per source.
def test_argmax_per_source(tmp_path: Any) -> None:
    """argmax reports the dimension value of the source's best entry."""
    cache = _write_cache(
        tmp_path / "bnsl.db",
        [
            ({"network": "alarm", "seed": 0}, {"f1": 0.4}),
            ({"network": "alarm", "seed": 1}, {"f1": 0.9}),
        ],
    )
    _run(tmp_path, [cache], ["f1.argmax.seed[1]"])

    row = _rows(tmp_path / "summary.csv")[0]
    assert row["f1.argmax.seed[1]"] == "1"


# Test an unqualified argmax picks the best entry across sources.
def test_argmax_across_sources(tmp_path: Any) -> None:
    """Without a source index argmax spans every input cache."""
    first = _write_cache(
        tmp_path / "first.db",
        [({"network": "alarm", "seed": 0}, {"f1": 0.4})],
    )
    second = _write_cache(
        tmp_path / "second.db",
        [({"network": "alarm", "seed": 7}, {"f1": 0.9})],
    )
    _run(tmp_path, [first, second], ["f1.argmax.seed"])

    row = _rows(tmp_path / "summary.csv")[0]
    assert row["f1.argmax.seed"] == "7"


# Test an element selector reports one element of a list-valued dimension.
def test_argmax_element_selection(tmp_path: Any) -> None:
    """'{n}' selects the n-th element of the best entry's dimension."""
    cache = _write_cache(
        tmp_path / "weights.db",
        [
            ({"network": "alarm", "fusion_weights": [0.6, 0.4]}, {"f1": 0.9}),
            (
                {"network": "alarm", "fusion_weights": [0.25, 0.75]},
                {"f1": 0.5},
            ),
        ],
    )
    _run(
        tmp_path,
        [cache],
        [
            "f1.argmax.fusion_weights{1}",
            "f1.argmax.fusion_weights{2}",
            "f1.argmax.fusion_weights{3}",
        ],
    )

    row = _rows(tmp_path / "summary.csv")[0]
    assert float(row["f1.argmax.fusion_weights{1}"]) == pytest.approx(0.6)
    assert float(row["f1.argmax.fusion_weights{2}"]) == pytest.approx(0.4)
    assert row["f1.argmax.fusion_weights{3}"] == ""
