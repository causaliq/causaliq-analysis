"""Unit tests for the evaluate_graph action interface."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from .conftest import (
    create_mock_graphml_entry,
)
from .evaluate_graph_support import (
    _block,
    _metric,
    _run_evaluate,
)


def test_evaluate_graph_returns_metrics() -> None:
    """Test that evaluate_graph computes and returns structural metrics."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Create mock entry with graph
    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    # Mock pdag_compare to return known metrics
    # Note: pdag_compare uses 'p' and 'r' for precision/recall
    mock_metrics = {
        "p": 1.0,
        "r": 1.0,
        "f1": 1.0,
        "shd": 0,
    }

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
        ) as mock_read:
            # Return a mock graph object for both reads
            mock_read.return_value = MagicMock()

            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1", "shd", "precision", "recall"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert _metric(result, "precision") == 1.0
    assert _metric(result, "recall") == 1.0
    assert _metric(result, "f1") == 1.0
    assert _metric(result, "shd") == 0
    assert _block(result, "parameters")["reference"] == "ref.graphml"


# Test evaluate_graph records every user-facing parameter.
def test_evaluate_graph_records_all_parameters() -> None:
    """Test that unset parameters are recorded as None."""
    result = _run_evaluate({"reference": "ref.graphml", "metric": "f1"})

    assert _block(result, "parameters") == {
        "input": None,
        "reference": "ref.graphml",
        "context": None,
        "metric": ["f1"],
        "threshold": None,
        "present_threshold": 0.0,
        "direction_threshold": 0.0,
        "output": None,
        "filter": None,
    }


# Test evaluate_graph records supplied input and filter parameters.
def test_evaluate_graph_records_input_and_filter() -> None:
    """Test that input and filter values are recorded unchanged."""
    result = _run_evaluate(
        {
            "input": "results/learn.db",
            "reference": "ref.graphml",
            "metric": ["f1"],
            "filter": "algorithm == 'pc'",
        }
    )

    parameters = _block(result, "parameters")
    assert parameters["input"] == "results/learn.db"
    assert parameters["filter"] == "algorithm == 'pc'"


# Test evaluate_graph resolves output from the open step cache.
def test_evaluate_graph_resolves_output_from_context() -> None:
    """Test that the open output cache supplies an omitted output."""
    context = MagicMock()
    context.cache.db_path = "results/metrics.db"

    result = _run_evaluate(
        {"reference": "ref.graphml", "metric": ["f1"]}, context
    )

    assert _block(result, "parameters")["output"] == "results/metrics.db"


# Test evaluate_graph prefers an explicit output parameter.
def test_evaluate_graph_prefers_explicit_output() -> None:
    """Test that an explicit output is not replaced by the context."""
    context = MagicMock()
    context.cache.db_path = "context.db"

    result = _run_evaluate(
        {
            "reference": "ref.graphml",
            "metric": ["f1"],
            "output": "metrics.db",
        },
        context,
    )

    assert _block(result, "parameters")["output"] == "metrics.db"


# Test evaluate_graph result block records the status only.
def test_evaluate_graph_result_block_holds_status_only() -> None:
    """Test that the result block omits reference and evaluated graph."""
    result = _run_evaluate({"reference": "ref.graphml", "metric": ["f1"]})

    assert _block(result, "result") == {"status": "ok"}


# Test evaluate_graph dry-run mode skips execution.
def test_evaluate_graph_dry_run_skips(capsys: Any) -> None:
    """Test that dry-run mode returns skipped without computing."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": MagicMock(),
    }

    result = provider.run(
        action="evaluate_graph",
        parameters={
            "_aggregation_entries": [update_entry],
            "output": "metrics.db",
            "reference": "ref.graphml",
            "metric": ["f1"],
        },
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"
    assert _block(result, "result") == {"status": "skipped"}
    assert _block(result, "parameters")["reference"] == "ref.graphml"
    captured = capsys.readouterr()
    assert "Would evaluate graph" in captured.out


# Test evaluate_graph requires _aggregation_entries parameter.
def test_evaluate_graph_requires_aggregation_entries() -> None:
    """Test error when _aggregation_entries is not provided."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="evaluate_graph",
            parameters={"reference": "ref.graphml", "metric": ["f1"]},
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "_aggregation_entries" in str(exc_info.value)


# Test evaluate_graph reports an empty input match clearly.
def test_evaluate_graph_reports_empty_aggregation_entries() -> None:
    """Test error names the input cache when no entries matched."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="evaluate_graph",
            parameters={
                "_aggregation_entries": [],
                "input": "results/learn.db",
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "matched no cache entries" in str(exc_info.value)
    assert "results/learn.db" in str(exc_info.value)


# Test evaluate_graph describes a graph when no reference is provided.
def test_evaluate_graph_describes_without_reference() -> None:
    """Test that a missing reference selects description mode."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    entry = {
        "matrix_values": {"network": "asia"},
        "metadata": {},
        "entry": MagicMock(),
    }
    values = {"exist_agree": [1.0, 0.6], "dir_agree": [1.0]}

    with patch(
        "causaliq_analysis.workflow_action.actions.evaluate_graph.execution"
        "._entry_graph",
        return_value=(MagicMock(), "pdg"),
    ):
        with patch(
            "causaliq_analysis.workflow_action.actions.evaluate_graph"
            ".description.pdg_edge_agreement",
            return_value=values,
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [entry],
                    "output": "metrics.db",
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert _metric(result, "exist_agree") == [1.0, 0.6]
    assert _metric(result, "dir_agree") == [1.0]


def test_evaluate_graph_describes_with_terminal_logger(capsys: Any) -> None:
    """Description mode reports the number of collected values."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    logger = MagicMock()
    logger.is_terminal_logging = True
    entry = {
        "matrix_values": {"network": "asia"},
        "metadata": {},
        "entry": MagicMock(),
    }

    with patch(
        "causaliq_analysis.workflow_action.actions.evaluate_graph.execution"
        "._entry_graph",
        return_value=(MagicMock(), "pdg"),
    ):
        with patch(
            "causaliq_analysis.workflow_action.actions.evaluate_graph"
            ".description.pdg_edge_agreement",
            return_value={"exist_agree": [1.0], "dir_agree": [0.9]},
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [entry],
                    "output": "metrics.db",
                },
                mode="run",
                context=None,
                logger=logger,
            )

    assert result[0] == "success"
    assert "Described exist_agree: 1 values" in capsys.readouterr().out


def test_evaluate_request_requires_metric_with_reference() -> None:
    """The request builder rejects a reference without a metric."""
    from causaliq_analysis.workflow_action.actions.evaluate_graph import (
        request as evaluate_request,
    )
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    with pytest.raises(ActionExecutionError, match="requires 'metric'"):
        evaluate_request._evaluate_request(
            {
                "_aggregation_entries": [{"matrix_values": {}}],
                "reference": "ref.graphml",
            }
        )


def test_evaluate_graph_dry_run_describes(capsys: Any) -> None:
    """A dry run without a reference previews description mode."""
    from causaliq_analysis.workflow_action.actions.evaluate_graph import (
        request as evaluate_request,
    )

    logger = MagicMock()
    logger.is_terminal_logging = True
    request = evaluate_request._evaluate_request(
        {"_aggregation_entries": [{"matrix_values": {"network": "asia"}}]}
    )
    block = evaluate_request._parameter_block({}, request, None)

    result = evaluate_request._dry_run_result(request, block, logger)

    assert result[0] == "skipped"
    assert "Would describe graph" in capsys.readouterr().out


@pytest.mark.parametrize("forward, expected", [(0.8, 1), (0.2, 0)])
def test_evaluate_graph_thresholds_before_comparison(
    forward: float,
    expected: int,
) -> None:
    """A threshold reduces the graph before the counts are computed."""
    from causaliq_core.graph import PDG, EdgeProbabilities

    from causaliq_analysis.workflow_action.actions.evaluate_graph import (
        comparison as evaluate_comparison,
    )

    graph = PDG(
        ["A", "B"],
        {
            ("A", "B"): EdgeProbabilities(
                forward=forward,
                backward=0.0,
                undirected=0.0,
                none=1.0 - forward,
            )
        },
    )
    reference = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=1.0, none=0.0)},
    )

    metrics = evaluate_comparison._compute_metrics(
        graph, reference, threshold=0.3
    )

    assert metrics["arc_matched"] == expected
    assert metrics["arc_missing"] == 1 - expected


# Test evaluate_graph requires metric parameter.
def test_evaluate_graph_requires_metric() -> None:
    """Test error when metric is not provided."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": MagicMock(),
    }

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="evaluate_graph",
            parameters={
                "_aggregation_entries": [update_entry],
                "output": "metrics.db",
                "reference": "ref.graphml",
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "metric" in str(exc_info.value)


# Test evaluate_graph rejects more than one matched aggregation entry.
def test_evaluate_graph_rejects_multiple_entries() -> None:
    """Test evaluate_graph raises when several entries match one job."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionExecutionError, match="exactly one"):
        provider.run(
            action="evaluate_graph",
            parameters={
                "reference": "ref.graphml",
                "metric": ["f1"],
                "_aggregation_entries": [{}, {}],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test evaluate_graph rejects a non-cache output path.
def test_evaluate_graph_rejects_non_cache_output() -> None:
    """Test evaluate_graph validate rejects a non-.db output."""
    from causaliq_analysis.workflow_action.actions.evaluate_graph import (
        EvaluateGraphAction,
    )

    with pytest.raises(ValueError, match="must be a workflow cache"):
        EvaluateGraphAction().validate(
            {
                "reference": "ref.graphml",
                "metric": ["f1"],
                "output": "metrics.csv",
            }
        )
