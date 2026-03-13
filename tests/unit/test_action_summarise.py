"""Unit tests for summarise action with mocked dependencies."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


def test_summarise_requires_metric() -> None:
    """Test that summarise raises error without metric parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionValidationError, match="At least one metric"):
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": [{"matrix_values": {}}],
                "output": "out.csv",
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test summarise validates metric specification format.
def test_summarise_invalid_metric_spec() -> None:
    """Test that summarise rejects metric specs without dots."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": [{"matrix_values": {}}],
                "metric": ["f1_without_stat"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "must be <field>.<stat>" in str(exc_info.value)


# Test summarise rejects unknown statistics.
def test_summarise_unknown_stat() -> None:
    """Test that summarise rejects unknown statistic names."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": [{"matrix_values": {}}],
                "metric": ["f1.median"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "Unknown statistic 'median'" in str(exc_info.value)


# Test summarise rejects .db output (only CSV supported).
def test_summarise_rejects_db_output() -> None:
    """Test that summarise rejects .db output files."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionValidationError) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": [{"matrix_values": {}}],
                "metric": ["f1.mean"],
                "output": "results.db",
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "only supports CSV output" in str(exc_info.value)


# Test summarise writes to terminal when no output file specified.
def test_summarise_writes_to_terminal(capsys: Any) -> None:
    """Test that summarise writes CSV to terminal when no output specified."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}},
        },
        {
            "matrix_values": {"seed": 2},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.9}}},
        },
    ]

    status, metadata, objects = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean"],
            # No output parameter - should print to terminal
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert status == "success"
    assert metadata["source_count"] == 2
    assert abs(metadata["f1.mean"] - 0.85) < 1e-9

    # Check terminal output
    captured = capsys.readouterr()
    assert "f1.mean" in captured.out


# Test summarise with output="-" writes to terminal.
def test_summarise_dash_output_writes_to_terminal(capsys: Any) -> None:
    """Test that output='-' writes CSV to terminal (workflow syntax)."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}},
        },
    ]

    status, metadata, objects = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean"],
            "output": "-",  # Explicit terminal output
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert status == "success"
    assert metadata["source_count"] == 1

    # Check terminal output
    captured = capsys.readouterr()
    assert "f1.mean" in captured.out


# Test summarise dry-run mode returns skipped.
def test_summarise_dry_run_skips(capsys: Any) -> None:
    """Test that dry-run mode returns skipped without processing."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    aggregation_entries: List[Dict[str, Any]] = [
        {"matrix_values": {"seed": 1}, "metadata": {}},
        {"matrix_values": {"seed": 2}, "metadata": {}},
    ]

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean", "f1.sd"],
            "output": "summary.csv",
        },
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"
    assert result[1]["aggregation_mode"] is True
    assert result[1]["metrics"] == ["f1.mean", "f1.sd"]

    captured = capsys.readouterr()
    assert "Would summarise metrics from 2 entries" in captured.out


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
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 2},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.9}}},
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
            "metadata": {"provider": {"action": {"score": 10.0}}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 2},
            "metadata": {"provider": {"action": {"score": 20.0}}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 3},
            "metadata": {"provider": {"action": {"score": 30.0}}},
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
            "metadata": {"provider": {"action": {"f1": 0.8}}},
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
    assert result[1]["f1.sd"] is None


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
            "metadata": {"provider": {"action": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 2, "status": "failed"},
            "metadata": {"provider": {"action": {"f1": 0.5}}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 3, "status": "completed"},
            "metadata": {"provider": {"action": {"f1": 0.9}}},
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
            "metadata": {"provider": {"action": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"seed": 2},
            "metadata": {"provider": {"action": {"f1": "not_a_number"}}},
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
def test_summarise_requires_input_or_entries() -> None:
    """Test that summarise requires aggregation entries or input files."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "metric": ["f1.mean"],
                # No _aggregation_entries and no input
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "requires either aggregation entries" in str(exc_info.value)


# Test summarise direct mode only supports .db files.
def test_summarise_direct_mode_only_db() -> None:
    """Test that direct mode rejects non-.db input files."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "metric": ["f1.mean"],
                "input": ["results.json"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "only supports .db cache files" in str(exc_info.value)


# Test summarise logs progress with terminal logging enabled.
def test_summarise_logs_progress(tmp_path: Any, capsys: Any) -> None:
    """Test that summarise logs progress when terminal logging enabled."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provider": {"action": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean"],
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    captured = capsys.readouterr()
    assert "Processed entry" in captured.out
    assert "Summary written to" in captured.out


# Test summarise metadata includes all expected fields.
def test_summarise_metadata_complete(tmp_path: Any) -> None:
    """Test that summarise metadata includes all expected fields."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provider": {"action": {"f1": 0.8}}},
            "cache_path": "cache1.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean"],
            "output": str(output_path),
            "filter": "seed == 1",
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    metadata = result[1]
    assert "source_count" in metadata
    assert "source_caches" in metadata
    assert "metrics" in metadata
    assert "timestamp" in metadata
    assert "filter" in metadata
    assert metadata["filter"] == "seed == 1"
    assert "cache1.db" in metadata["source_caches"]


# Test summarise dry-run mode without aggregation entries.
def test_summarise_dry_run_direct_mode(capsys: Any) -> None:
    """Test that dry-run mode prints direct mode message."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    result = provider.run(
        action="summarise",
        parameters={
            "metric": ["f1.mean"],
            "input": ["test.db"],
        },
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"
    assert result[1]["aggregation_mode"] is False

    captured = capsys.readouterr()
    assert "Would summarise metrics from input files" in captured.out


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
            "metadata": {"provider": {"action": {"f1": 0.8}}},
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
            "metadata": {"provider": {"action": {"other": 0.8}}},
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
    assert result[1]["f1.mean"] is None


# Test summarise CSV write exception.
def test_summarise_csv_write_error(tmp_path: Any) -> None:
    """Test that CSV write error raises ActionExecutionError."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provider": {"action": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
    ]

    # Create a directory where output file should be (causes write error)
    output_path = tmp_path / "summary.csv"
    output_path.mkdir()

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": aggregation_entries,
                "metric": ["f1.mean"],
                "output": str(output_path),
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "Failed to write CSV output" in str(exc_info.value)


# Test summarise generic exception is wrapped.
def test_summarise_generic_exception_wrapped() -> None:
    """Test that unexpected exceptions are wrapped in ActionValidationError."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Pass invalid metric type - validation catches it
    with pytest.raises(
        ActionValidationError, match="must be a string or list"
    ):
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": [{"matrix_values": {}}],
                "metric": 123,  # Invalid type, should be string or list
                "output": "out.csv",
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test summarise with input as single string.
def test_summarise_input_as_string(tmp_path: Any) -> None:
    """Test that single string input is normalised to list."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create a cache with one entry
    cache_path = tmp_path / "single.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry = CacheEntry(metadata={"provider": {"action": {"f1": 0.8}}})
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


# Test summarise metric as single string is normalised.
def test_summarise_metric_as_string(tmp_path: Any) -> None:
    """Test that metric as string is normalised to list."""
    from causaliq_workflow.cache import CacheEntry, WorkflowCache

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Create a cache with one entry
    cache_path = tmp_path / "single.db"
    with WorkflowCache(str(cache_path)) as cache:
        entry = CacheEntry(metadata={"provider": {"action": {"f1": 0.8}}})
        cache.put({"seed": 1}, entry)

    output_path = tmp_path / "summary.csv"

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    result = provider.run(
        action="summarise",
        parameters={
            "metric": "f1.mean",  # String, not list
            "input": str(cache_path),
            "output": str(output_path),
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["f1.mean"] == 0.8


# Test summarise wraps generic exceptions in ActionExecutionError.
def test_summarise_wraps_generic_exception(tmp_path: Any) -> None:
    """Test that unexpected exceptions during summarise are wrapped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries: List[Dict[str, Any]] = [
        {
            "matrix_values": {"seed": 1},
            "metadata": {"provider": {"action": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    # Patch statistics.mean to raise a generic Exception
    with patch("statistics.mean", side_effect=RuntimeError("Mock error")):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="summarise",
                parameters={
                    "_aggregation_entries": aggregation_entries,
                    "metric": ["f1.mean"],
                    "output": str(output_path),
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
        assert "Summarise failed" in str(exc_info.value)
