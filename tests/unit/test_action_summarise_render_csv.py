"""Unit tests for summarise CSV rendering."""

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest


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
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
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
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
            "cache_path": "test.db",
        },
        {
            "matrix_values": {"algorithm": "pc", "seed": 1},
            "metadata": {"provenance": {}, "result": {"f1": 0.7}},
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


# Test CSV always appends, never auto-deletes.
def test_summarise_csv_always_appends(
    tmp_path: Any,
) -> None:
    """Verify all jobs append to existing CSV (no auto-deletion)."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    output_path = tmp_path / "summary.csv"

    # First job: creates the file
    aggregation_entries_1 = [
        {
            "matrix_values": {"seed": 0},
            "metadata": {"provenance": {}, "result": {"f1": 0.8}},
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

    # Second job: appends
    aggregation_entries_2 = [
        {
            "matrix_values": {"seed": 0},
            "metadata": {"provenance": {}, "result": {"f1": 0.6}},
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

    # Read CSV - should have header + 2 data rows
    with open(output_path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    assert len(lines) == 3  # header + 2 data rows
    header = lines[0].split(",")
    row1 = lines[1].split(",")
    row2 = lines[2].split(",")

    assert header[0] == "network"
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
