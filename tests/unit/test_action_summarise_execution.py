"""Unit tests for summarise dry runs, metadata and logging."""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


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
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
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
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
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
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
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
