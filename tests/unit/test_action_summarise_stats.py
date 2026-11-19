"""Unit tests for summarise statistics."""

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


# Test summarise computes mean from aggregation entries.
def test_summarise_computes_mean(tmp_path: Any) -> None:
    """Test that summarise computes mean from aggregation entries."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Entries with f1 values in metadata
    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 2},
            "metadata": {"provenance": {}, "result": {"f1": 0.9}},
            "cache_path": "test.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean", "f1.count"],
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["source_count"] == 2
    assert abs(result[1]["f1.mean"] - 0.85) < 0.01
    assert result[1]["f1.count"] == 2
    assert output_path.exists()


# Test summarise computes standard deviation.
def test_summarise_computes_sd(tmp_path: Any) -> None:
    """Test that summarise computes SD with enough values."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provenance": {}, "result": {"score": 10.0}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 2},
            "metadata": {"provenance": {}, "result": {"score": 20.0}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 3},
            "metadata": {"provenance": {}, "result": {"score": 30.0}},
            "cache_path": "test.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["score.sd"],
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    # SD of [10, 20, 30] is 10.0
    assert abs(result[1]["score.sd"] - 10.0) < 0.01


# Test summarise returns None for SD with insufficient values.
def test_summarise_sd_insufficient_values(tmp_path: Any) -> None:
    """Test that SD returns None with fewer than 2 values."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
            "cache_path": "test.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.sd"],
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["f1.sd"] == ""  # Empty string for non-computable stats


# Test summarise mean returns None with no values.
def test_summarise_mean_no_values(tmp_path: Any) -> None:
    """Test that mean returns None when no values collected."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provenance": {}, "result": {"other": 0.8}},
            "cache_path": "test.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean"],  # f1 field doesn't exist
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["f1.mean"] == ""  # Empty string for non-computable stats


# Test summarise computes min, max and median statistics.
@pytest.mark.parametrize(
    "spec, expected",
    [("f1.min", 0.2), ("f1.max", 0.8), ("f1.median", 0.5)],
)
def test_summarise_extreme_and_median_stats(
    tmp_path: Any, spec: str, expected: float
) -> None:
    """min, max and median report the expected value."""
    import csv

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    entries = [
        {
            "matrix_values": {"seed": seed},
            "metadata": {"provenance": {}, "result": {"f1": value}},
            "cache_path": "test.db",
        }
        for seed, value in enumerate([0.2, 0.5, 0.8])
    ]
    output_path = tmp_path / "stats.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": entries,
            "metric": [spec],
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1][spec] == expected
    with open(output_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert float(rows[0][spec]) == expected


# Test the sum statistic and text unique values.
def test_sum_and_text_unique_stats(tmp_path: Any) -> None:
    """sum adds numeric values and unique reports text metadata."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    entries = [
        {
            "matrix_values": {"network": "alarm"},
            "metadata": {
                "provenance": {},
                "result": {"count": 3, "domain": "patient_monitoring"},
            },
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"network": "asia"},
            "metadata": {
                "provenance": {},
                "result": {"count": 4, "domain": "patient_monitoring"},
            },
            "cache_path": "test.db",
        },
    ]
    output_path = tmp_path / "stats.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": entries,
            "metric": ["count.sum", "domain.unique"],
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["count.sum"] == 7
    assert result[1]["domain.unique"] == "patient_monitoring"


# Test unique rejects conflicting text values.
def test_text_unique_rejects_conflict(tmp_path: Any) -> None:
    """A text unique column rejects two distinct values."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False
    entries = [
        {
            "matrix_values": {"network": "alarm"},
            "metadata": {
                "provenance": {},
                "result": {"domain": "patient_monitoring"},
            },
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"network": "asia"},
            "metadata": {
                "provenance": {},
                "result": {"domain": "respiratory_diagnosis"},
            },
            "cache_path": "test.db",
        },
    ]

    with pytest.raises(ActionExecutionError, match="reports a single value"):
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": entries,
                "metric": ["domain.unique"],
                "output": str(tmp_path / "stats.csv"),
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test numeric filtering and text-unique edge cases.
def test_numeric_values_skip_non_numeric() -> None:
    """Booleans, missing values and text do not enter numeric stats."""
    from causaliq_analysis.workflow_action.actions.summarise.stats import (
        _numeric_values,
        _stat_value,
    )

    values = [True, None, "", "n/a", 2, 3.0]
    assert _numeric_values(values) == [2.0, 3.0]
    assert _stat_value("count", values) == 2
    assert _stat_value("sum", values) == 5.0


# Test integral floats are reported as integers by unique.
def test_unique_integral_float() -> None:
    """A unique integral float is returned as an int."""
    from causaliq_analysis.workflow_action.actions.summarise.stats import (
        _unique_value,
    )

    assert _unique_value([2.0], "value") == 2


# Test empty unique values are ignored.
def test_distinct_values_ignore_empty() -> None:
    """None and empty strings do not create distinct values."""
    from causaliq_analysis.workflow_action.actions.summarise.stats import (
        _distinct_values,
    )

    assert _distinct_values([None, "", "a", "a"]) == ["a"]


@pytest.mark.parametrize(
    "value, element, expected",
    [
        ([0.6, 0.4], 1, 0.6),
        ([0.6, 0.4], 2, 0.4),
        ([0.6, 0.4], 3, ""),
        ("[0.6, 0.4]", 1, 0.6),
        (0.6, 1, 0.6),
        (0.6, 2, ""),
        ("", 1, ""),
        (None, 1, ""),
    ],
)
def test_element_value(value: Any, element: int, expected: Any) -> None:
    """An element is selected from a list, JSON list or scalar."""
    from causaliq_analysis.workflow_action.actions.summarise.stats import (
        _element_value,
    )

    assert _element_value(value, element) == expected


# Test invalid JSON list text falls back to a scalar value.
def test_element_value_invalid_json() -> None:
    """Text that starts a list but is not JSON is treated as a scalar."""
    from causaliq_analysis.workflow_action.actions.summarise.stats import (
        _element_value,
    )

    assert _element_value("[0.6,", 1) == "[0.6,"
    assert _element_value("[0.6,", 2) == ""
