"""Unit tests for summarise statistics."""

from typing import Any, Dict, List
from unittest.mock import MagicMock


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
