"""Unit tests for migrate_trace action with mocked dependencies."""

from typing import Any

from causaliq_analysis.migrate import MigrateTraceResult


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

    mocker.patch(
        "causaliq_analysis.workflow_action.actions.migrate_trace"
        ".run_migrate_trace",
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
