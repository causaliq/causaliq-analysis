"""Unit tests for evaluate_graph metric values and objects."""

from unittest.mock import MagicMock, patch

from .conftest import (
    create_mock_graphml_entry,
)
from .evaluate_graph_support import (
    _block,
    _metric,
    _metric_keys,
)


# Test evaluate_graph respects metric filter parameter.
def test_evaluate_graph_metric_filter() -> None:
    """Test that metric parameter filters output to requested metrics."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics = {
        "p": 0.9,
        "r": 0.85,
        "f1": 0.875,
        "shd": 3,
    }

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": "f1",
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    # The metrics object holds only f1; metadata holds parameters and result
    assert _metric_keys(result) == {"f1"}
    assert set(result[1]) == {"parameters", "result"}
    assert set(_block(result, "result")) == {"status"}


# Test evaluate_graph accepts list of metrics.
def test_evaluate_graph_metric_filter_list() -> None:
    """Test that metric parameter accepts a list of metrics."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics = {
        "p": 0.9,
        "r": 0.85,
        "f1": 0.875,
        "shd": 3,
    }

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1", "shd"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    # Should contain f1 and shd, not precision/recall
    assert _metric_keys(result) == {"f1", "shd"}


# Test evaluate_graph expands 'edge' to the low-level count metrics.
def test_evaluate_graph_edge_metrics() -> None:
    """Test that 'edge' expands to the low-level comparison counts."""
    from causaliq_analysis.metrics import EDGE_METRICS
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    # Counts are numbered so each key can be checked independently
    mock_metrics: dict = {
        "p": 0.8,
        "r": 0.75,
        "f1": 0.77,
        "shd": 5,
        **{name: index for index, name in enumerate(EDGE_METRICS)},
    }

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["edge"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    for index, name in enumerate(EDGE_METRICS):
        assert _metric(result, name) == index
    # Derived aggregates are not part of an 'edge' request
    assert "f1" not in _block(result, "result")
    assert "shd" not in _block(result, "result")
    assert "precision" not in _block(result, "result")


# Test evaluate_graph expands 'equiv.edge' after CPDAG conversion.
def test_evaluate_graph_equiv_edge_metrics() -> None:
    """Test that 'equiv.edge' counts come from the CPDAG comparison."""
    from causaliq_core.graph import DAG

    from causaliq_analysis.metrics import EDGE_METRICS
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    direct_metrics: dict = {"p": 0.8, "r": 0.75, "f1": 0.77, "shd": 5}
    equiv_metrics: dict = {
        "p": 0.9,
        "r": 0.85,
        "f1": 0.87,
        "shd": 2,
        **{name: index for index, name in enumerate(EDGE_METRICS)},
    }

    mock_dag = MagicMock(spec=DAG)
    mock_cpdag = MagicMock()

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        side_effect=[direct_metrics, equiv_metrics],
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=mock_dag,
        ):
            with patch(
                "causaliq_core.graph.convert.dag_to_pdag",
                return_value=mock_cpdag,
            ) as mock_to_cpdag:
                result = provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "ref.graphml",
                        "metric": ["equiv.edge"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    for index, name in enumerate(EDGE_METRICS):
        assert _metric(result, f"equiv.{name}") == index
    assert "equiv.f1" not in _block(result, "result")
    assert "equiv.shd" not in _block(result, "result")
    assert "arc_matched" not in _block(result, "result")
    # Both graphs must be converted to CPDAGs
    assert mock_to_cpdag.call_count == 2


# Test evaluate_graph combines 'edge' counts with standard metrics.
def test_evaluate_graph_edge_with_standard_metric() -> None:
    """Test that 'edge' counts can be combined with standard metrics."""
    from causaliq_analysis.metrics import EDGE_METRICS
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics: dict = {
        "p": 0.8,
        "r": 0.75,
        "f1": 0.77,
        "shd": 5,
        **{name: index for index, name in enumerate(EDGE_METRICS)},
    }

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1", "edge"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert _metric(result, "f1") == 0.77
    for index, name in enumerate(EDGE_METRICS):
        assert _metric(result, name) == index
    assert "shd" not in _block(result, "result")
    assert "precision" not in _block(result, "result")


# Test evaluate_graph omits edge counts when 'edge' is not requested.
def test_evaluate_graph_edge_metrics_not_leaked() -> None:
    """Test that low-level counts require an explicit 'edge' request."""
    from causaliq_analysis.metrics import EDGE_METRICS
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics: dict = {
        "p": 0.8,
        "r": 0.75,
        "f1": 0.77,
        "shd": 5,
        **{name: index for index, name in enumerate(EDGE_METRICS)},
    }

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["precision"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert _metric(result, "precision") == 0.8
    assert _metric_keys(result) == {"precision"}
    assert set(result[1]) == {"parameters", "result"}
    assert set(_block(result, "result")) == {"status"}


# Test evaluate_graph reports the evaluated graph's node count.
def test_evaluate_graph_node_count_metric() -> None:
    """node_count is the number of nodes in the evaluated graph."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    graph = MagicMock()
    graph.nodes = ["A", "B", "C"]
    entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": create_mock_graphml_entry(),
    }
    mock_metrics = {"p": 1.0, "r": 1.0, "f1": 1.0, "shd": 0}

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=graph,
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["node_count"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert _metric(result, "node_count") == 3


# Test evaluate_graph omits node_count when it is not requested.
def test_evaluate_graph_node_count_not_requested() -> None:
    """node_count is absent unless it appears in the metric list."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    graph = MagicMock()
    graph.nodes = ["A", "B"]
    entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": create_mock_graphml_entry(),
    }
    mock_metrics = {"p": 1.0, "r": 1.0, "f1": 1.0, "shd": 0}

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=graph,
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert _metric_keys(result) == {"f1"}
