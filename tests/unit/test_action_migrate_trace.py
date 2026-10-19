"""Unit tests for migrate_trace action with mocked dependencies."""

from typing import Any

import pytest

from causaliq_analysis.migrate import MigrateTraceResult
from causaliq_analysis.workflow_action.actions import migrate_trace


# Test migrate_trace returns skipped when no matching traces.
def test_migrate_trace_skips_no_matching_traces(mocker: Any) -> None:
    """Test action returns skipped when run_migrate_trace yields 0."""
    from causaliq_analysis.workflow_action import (
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = mocker.MagicMock()
    mock_logger.is_terminal_logging = False

    empty_result = MigrateTraceResult(graphs=[], skipped=0)

    mocker.patch.object(
        migrate_trace,
        "run_migrate_trace",
        return_value=empty_result,
    )

    result = provider.run(
        action="migrate_trace",
        parameters={
            "series": "TABU/STD",
            "network": "asia",
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"
    assert result[1]["num_graphs"] == 0
    assert "No traces for" in result[1]["message"]


# Test migrate_trace returns a single dag object and flattened metadata.
def test_migrate_trace_single_graph_success(mocker: Any) -> None:
    """Test migrate_trace returns one dag object for a single graph."""
    from causaliq_analysis.workflow_action import (
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = mocker.MagicMock()
    mock_logger.is_terminal_logging = False

    graph = mocker.MagicMock()
    graph.graphml = "<graphml/>"
    graph.trace_id = "TABU/STD/asia/N1000"
    graph.metadata = {"N": 1000}
    result = MigrateTraceResult(graphs=[graph], skipped=0)

    mocker.patch(
        "causaliq_analysis.workflow_action.actions.migrate_trace"
        ".run_migrate_trace",
        return_value=result,
    )

    status, metadata, objects = provider.run(
        action="migrate_trace",
        parameters={"series": "TABU/STD", "network": "asia"},
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert status == "success"
    assert metadata["num_graphs"] == 1
    assert metadata["N"] == 1000
    assert objects[0]["type"] == "dag"


# Test migrate_trace rejects several graphs for one cache key.
def test_migrate_trace_rejects_multiple_graphs(mocker: Any) -> None:
    """Test migrate_trace errors when several graphs match one key."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = mocker.MagicMock()
    mock_logger.is_terminal_logging = False

    result = MigrateTraceResult(
        graphs=[mocker.MagicMock(), mocker.MagicMock()], skipped=0
    )
    mocker.patch(
        "causaliq_analysis.workflow_action.actions.migrate_trace"
        ".run_migrate_trace",
        return_value=result,
    )

    with pytest.raises(ActionExecutionError, match="one cache key"):
        provider.run(
            action="migrate_trace",
            parameters={"series": "TABU/STD", "network": "asia"},
            mode="run",
            context=None,
            logger=mock_logger,
        )
