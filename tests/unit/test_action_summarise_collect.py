"""Unit tests for summarise value collection and filters."""

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


# Test summarise reads metric values from the entry's JSON object.
def test_summarise_reads_values_from_json_object(tmp_path: Any) -> None:
    """Test that values come from the entry's JSON object."""
    import csv

    from causaliq_workflow.cache import CacheEntry

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    entry = CacheEntry()
    entry.add_object("metrics", "json", '{"f1": 0.5}', "evaluate_graph")

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {},
            "entry": entry,
            "cache_path": "metrics.db",
        }
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
    with output_path.open() as handle:
        row = next(csv.DictReader(handle))
    assert float(row["f1.mean"]) == 0.5
    assert int(row["f1.count"]) == 1


# Test summarise ignores object content that is not a JSON mapping.
def test_summarise_ignores_non_mapping_object(tmp_path: Any) -> None:
    """Test that invalid or non-mapping JSON objects contribute no values."""
    import csv

    from causaliq_workflow.cache import CacheEntry

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    invalid = CacheEntry()
    invalid.add_object("metrics", "json", "not json", "evaluate_graph")
    non_mapping = CacheEntry()
    non_mapping.add_object("metrics", "json", "[1, 2]", "evaluate_graph")
    not_json = CacheEntry()
    not_json.add_object("dag", "graphml", "<graphml/>", "learn_graph")

    aggregation_entries: List[Dict[str, Any]] = [
        {"matrix_values": {"seed": 1}, "metadata": {}, "entry": invalid},
        {"matrix_values": {"seed": 2}, "metadata": {}, "entry": non_mapping},
        {"matrix_values": {"seed": 3}, "metadata": {}, "entry": not_json},
    ]
    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.count"],
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    with output_path.open() as handle:
        row = next(csv.DictReader(handle))
    assert int(row["f1.count"]) == 0


# Test summarise applies filter to aggregation entries.
def test_summarise_with_filter(tmp_path: Any) -> None:
    """Test that summarise filters entries by expression."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1, "status": "completed"},
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 2, "status": "failed"},
            "metadata": {"provenance": {}, "result": {"f1": 0.5}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 3, "status": "completed"},
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
            "filter": "status == 'completed'",
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    # Only 2 completed entries (0.8 and 0.9)
    assert result[1]["f1.count"] == 2
    assert abs(result[1]["f1.mean"] - 0.85) < 0.01


# Test summarise applies random() filter in aggregation mode.
def test_summarise_with_random_filter_aggregation(
    tmp_path: Any,
) -> None:
    """Test that summarise resolves random() in aggregation."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": str(i)},
            "metadata": {
                "provenance": {},
                "result": {"f1": 0.5 + i * 0.05},
            },
            "cache_path": "test.db",
        }
        for i in range(10)
    ]

    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.count"],
            "output": str(output_path),
            "filter": "seed in random(3, 0)",
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["f1.count"] == 3


# Test summarise skips non-numeric values.
def test_summarise_skips_non_numeric(tmp_path: Any) -> None:
    """Test that summarise ignores non-numeric field values."""
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
        {
            "matrix_values": {"seed": 2},
            "metadata": {"provenance": {}, "result": {"f1": "not_a_number"}},
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
    assert result[1]["f1.count"] == 1
    assert result[1]["f1.mean"] == 0.8


# Test summarise direct mode requires input or aggregation entries.
def test_summarise_requires_input_or_entries(tmp_path: Any) -> None:
    """Test that summarise requires aggregation entries or input files."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    output_path = tmp_path / "summary.csv"

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "metric": ["f1.mean"],
                "output": str(output_path),
                # No _aggregation_entries and no input
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "requires either aggregation entries" in str(exc_info.value)


# Test summarise direct mode only supports .db files.
def test_summarise_direct_mode_only_db(tmp_path: Any) -> None:
    """Test that direct mode rejects non-.db input files."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    output_path = tmp_path / "summary.csv"

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "metric": ["f1.mean"],
                "input": ["results.json"],
                "output": str(output_path),
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "only supports .db cache files" in str(exc_info.value)


# Test summarise filter exception in aggregation mode.
def test_summarise_filter_exception_aggregation(tmp_path: Any) -> None:
    """Test that filter exception skips entry in aggregation mode."""
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
            "metric": ["f1.count"],
            "output": str(output_path),
            "filter": "undefined_var > 5",  # Will cause exception
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    # Entry skipped due to filter exception
    assert result[1]["f1.count"] == 0


# Test summarise with input as single string.
def test_summarise_input_as_string(tmp_path: Any) -> None:
    """Test that single string input is normalised to list."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create a cache with one entry
    cache_path = tmp_path / "single.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry = CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.8}})
        cache.put({"seed": 1}, entry)

    output_path = tmp_path / "summary.csv"

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    result = provider.run(
        action="summarise",
        parameters={
            "metric": ["f1.mean"],
            "input": str(cache_path),  # String, not list
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["f1.mean"] == 0.8


# Test direct mode filters cache entries by context matrix values.
def test_summarise_direct_mode_filters_by_context_matrix(
    tmp_path: Any,
) -> None:
    """Verify direct mode input filters cache entries by context matrix."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create a cache with entries for different networks
    cache_path = tmp_path / "multi.db"
    with WorkflowCache(str(cache_path)) as cache:
        # Asia entries
        cache.put(
            {"network": "asia", "seed": 0},
            CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.8}}),
        )
        cache.put(
            {"network": "asia", "seed": 1},
            CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.9}}),
        )
        # Alarm entries (should be filtered out)
        cache.put(
            {"network": "alarm", "seed": 0},
            CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.5}}),
        )

    output_path = tmp_path / "summary.csv"

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Context specifies network=asia, so only asia entries should be counted
    mock_context = MagicMock()
    mock_context.matrix_values = {"network": "asia"}
    mock_context.job_index = 0
    mock_context.total_jobs = 1

    result = provider.run(
        action="summarise",
        parameters={
            "metric": ["f1.mean", "f1.count"],
            "input": str(cache_path),
            "output": str(output_path),
        },
        mode="run",
        context=mock_context,
        logger=mock_logger,
    )

    assert result[0] == "success"
    # Only 2 asia entries should be counted (not the alarm entry)
    assert result[1]["f1.count"] == 2
    # Mean of 0.8 and 0.9 = 0.85
    assert abs(result[1]["f1.mean"] - 0.85) < 0.01


# Test direct mode with filter expression.
def test_summarise_direct_mode_with_filter_expression(tmp_path: Any) -> None:
    """Verify direct mode applies filter expression to cache entries."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create a cache with entries having different seed values
    cache_path = tmp_path / "filtered.db"
    with WorkflowCache(str(cache_path)) as cache:
        cache.put(
            {"seed": 0},
            CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.8}}),
        )
        cache.put(
            {"seed": 1},
            CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.9}}),
        )
        cache.put(
            {"seed": 2},
            CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.5}}),
        )

    output_path = tmp_path / "summary.csv"

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Filter to only include seed < 2
    result = provider.run(
        action="summarise",
        parameters={
            "metric": ["f1.mean", "f1.count"],
            "input": str(cache_path),
            "output": str(output_path),
            "filter": "seed < 2",
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    # Only 2 entries with seed < 2 should be counted
    assert result[1]["f1.count"] == 2
    # Mean of 0.8 and 0.9 = 0.85
    assert abs(result[1]["f1.mean"] - 0.85) < 0.01


# Test direct mode with random() filter expression.
def test_summarise_direct_mode_with_random_filter(
    tmp_path: Any,
) -> None:
    """Verify direct mode resolves random() in filter."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    cache_path = tmp_path / "random_filter.db"
    with WorkflowCache(str(cache_path)) as cache:
        for i in range(10):
            cache.put(
                {"seed": str(i)},
                CacheEntry(
                    metadata={
                        "provenance": {},
                        "result": {
                            "f1": 0.5 + i * 0.05,
                            "seed": i,
                        },
                    }
                ),
            )

    output_path = tmp_path / "summary.csv"

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    result = provider.run(
        action="summarise",
        parameters={
            "metric": ["f1.count"],
            "input": str(cache_path),
            "output": str(output_path),
            "filter": "seed in random(3, 0)",
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["f1.count"] == 3


# Test direct mode skips entries when filter raises exception.
def test_summarise_direct_mode_filter_exception_skips_entry(
    tmp_path: Any,
) -> None:
    """Verify entries are skipped when filter evaluation raises exception."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create a cache with entries
    cache_path = tmp_path / "filter_error.db"
    with WorkflowCache(str(cache_path)) as cache:
        # Entry with value that exists
        cache.put(
            {"seed": 0},
            CacheEntry(
                metadata={"provenance": {}, "result": {"f1": 0.8, "x": 5}}
            ),
        )
        # Entry without x (filter will fail)
        cache.put(
            {"seed": 1},
            CacheEntry(metadata={"provenance": {}, "result": {"f1": 0.9}}),
        )

    output_path = tmp_path / "summary.csv"

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Filter uses undefined_var which will raise exception for all entries
    # Since exception is caught, entries are skipped
    result = provider.run(
        action="summarise",
        parameters={
            "metric": ["f1.mean", "f1.count"],
            "input": str(cache_path),
            "output": str(output_path),
            "filter": "undefined_var > 0",
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    # All entries should be skipped due to filter exception
    assert result[1]["f1.count"] == 0
    assert result[1]["f1.mean"] == ""  # Empty string for non-computable stats
