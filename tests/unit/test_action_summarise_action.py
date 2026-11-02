"""Unit tests for summarise validation and error handling."""

from typing import Any
from unittest.mock import MagicMock

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


# Test summarise metric as single string is normalised.
def test_summarise_metric_as_string(tmp_path: Any) -> None:
    """Test that metric as string is normalised to list."""
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
