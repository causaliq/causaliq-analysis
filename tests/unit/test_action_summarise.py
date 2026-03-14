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
    assert "must be a CSV file" in str(exc_info.value)


# Test summarise requires output parameter.
def test_summarise_requires_output_parameter() -> None:
    """Test that summarise requires output parameter."""
    from causaliq_core import ActionValidationError

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionValidationError) as exc_info:
        provider.run(
            action="summarise",
            parameters={
                "_aggregation_entries": [],
                "metric": ["f1.mean"],
                # No output parameter
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "requires 'output' parameter" in str(exc_info.value)


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
    assert result[1]["f1.sd"] == ""  # Empty string for non-computable stats


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
def test_summarise_dry_run_direct_mode(tmp_path: Any, capsys: Any) -> None:
    """Test that dry-run mode prints direct mode message."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    output_path = tmp_path / "summary.csv"

    result = provider.run(
        action="summarise",
        parameters={
            "metric": ["f1.mean"],
            "input": ["test.db"],
            "output": str(output_path),
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
    assert result[1]["f1.mean"] == ""  # Empty string for non-computable stats


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


# Test CSV includes matrix values from context as first columns.
def test_summarise_csv_includes_context_matrix_values(tmp_path: Any) -> None:
    """Verify matrix values from context appear as first CSV columns."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    aggregation_entries = [
        {
            "matrix_values": {"algorithm": "pc", "seed": 0},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"algorithm": "pc", "seed": 1},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.7}}},
            "cache_path": "test.db",
        },
    ]

    output_path = tmp_path / "summary.csv"

    # Create mock context with matrix_values
    mock_context = MagicMock()
    mock_context.matrix_values = {"network": "asia", "sample_size": 1000}

    status, metadata, outputs = provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries,
            "metric": ["f1.mean"],
            "output": str(output_path),
        },
        mode="run",
        context=mock_context,
        logger=mock_logger,
    )

    assert status == "success"
    assert output_path.exists()

    # Read CSV and verify matrix values are first columns
    with open(output_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    assert len(lines) == 2  # header + 1 data row
    header = lines[0].split(",")
    data = lines[1].split(",")

    # Matrix values should be first columns
    assert header[0] == "network"
    assert header[1] == "sample_size"
    assert header[2] == "f1.mean"
    assert data[0] == "asia"
    assert data[1] == "1000"
    assert data[2] == "0.75"  # mean of 0.8 and 0.7


# Test CSV clears on first job and appends on subsequent jobs.
def test_summarise_csv_clears_on_first_job_appends_after(
    tmp_path: Any,
) -> None:
    """Verify first job clears file, subsequent jobs append rows."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    output_path = tmp_path / "summary.csv"

    # Pre-create a stale file (simulating previous workflow run)
    output_path.write_text("stale,data\nold,values\n")

    # First job: job_index=0, should clear the stale file
    aggregation_entries_1 = [
        {
            "matrix_values": {"seed": 0},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.8}}},
            "cache_path": "test.db",
        },
    ]
    mock_context_1 = MagicMock()
    mock_context_1.matrix_values = {"network": "asia", "sample_size": 1000}
    mock_context_1.job_index = 0
    mock_context_1.total_jobs = 2

    provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries_1,
            "metric": ["f1.mean"],
            "output": str(output_path),
        },
        mode="run",
        context=mock_context_1,
        logger=mock_logger,
    )

    # Second job: job_index=1, should append
    aggregation_entries_2 = [
        {
            "matrix_values": {"seed": 0},
            "metadata": {"causaliq-analysis": {"evaluate_graph": {"f1": 0.6}}},
            "cache_path": "test.db",
        },
    ]
    mock_context_2 = MagicMock()
    mock_context_2.matrix_values = {"network": "alarm", "sample_size": 500}
    mock_context_2.job_index = 1
    mock_context_2.total_jobs = 2

    provider.run(
        action="summarise",
        parameters={
            "_aggregation_entries": aggregation_entries_2,
            "metric": ["f1.mean"],
            "output": str(output_path),
        },
        mode="run",
        context=mock_context_2,
        logger=mock_logger,
    )

    # Read CSV - should have both rows and no stale data
    with open(output_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    assert len(lines) == 3  # header + 2 data rows (stale data cleared)
    header = lines[0].split(",")
    row1 = lines[1].split(",")
    row2 = lines[2].split(",")

    # Verify no stale data
    assert header[0] == "network"  # not "stale"
    assert header[1] == "sample_size"
    assert header[2] == "f1.mean"

    # Verify first job data
    assert row1[0] == "asia"
    assert row1[1] == "1000"
    assert row1[2] == "0.8"

    # Verify second job data (appended)
    assert row2[0] == "alarm"
    assert row2[1] == "500"
    assert row2[2] == "0.6"


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
            CacheEntry(metadata={"provider": {"action": {"f1": 0.8}}}),
        )
        cache.put(
            {"network": "asia", "seed": 1},
            CacheEntry(metadata={"provider": {"action": {"f1": 0.9}}}),
        )
        # Alarm entries (should be filtered out)
        cache.put(
            {"network": "alarm", "seed": 0},
            CacheEntry(metadata={"provider": {"action": {"f1": 0.5}}}),
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
            CacheEntry(metadata={"provider": {"action": {"f1": 0.8}}}),
        )
        cache.put(
            {"seed": 1},
            CacheEntry(metadata={"provider": {"action": {"f1": 0.9}}}),
        )
        cache.put(
            {"seed": 2},
            CacheEntry(metadata={"provider": {"action": {"f1": 0.5}}}),
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
            CacheEntry(metadata={"provider": {"action": {"f1": 0.8, "x": 5}}}),
        )
        # Entry without x (filter will fail)
        cache.put(
            {"seed": 1},
            CacheEntry(metadata={"provider": {"action": {"f1": 0.9}}}),
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
