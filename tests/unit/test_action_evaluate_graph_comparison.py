"""Unit tests for evaluate_graph structural and equivalence metrics."""

from typing import Any
from unittest.mock import MagicMock, patch

from .conftest import (
    create_mock_graphml_entry,
)
from .evaluate_graph_support import (
    _block,
    _metric,
)


# Test evaluate_graph computes equiv.f1 metric.
def test_evaluate_graph_equiv_f1() -> None:
    """Test that equiv.f1 converts graphs to CPDAGs before comparison."""
    from causaliq_core.graph import DAG

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

    # Standard metrics from direct comparison
    mock_standard_metrics = {"p": 0.8, "r": 0.75, "f1": 0.77, "shd": 5}
    # Equiv metrics from CPDAG comparison
    mock_equiv_metrics = {"p": 0.9, "r": 0.85, "f1": 0.87, "shd": 2}

    mock_dag = MagicMock(spec=DAG)
    mock_cpdag = MagicMock()

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        side_effect=[mock_standard_metrics, mock_equiv_metrics],
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
                        "metric": ["equiv.f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert _metric(result, "equiv.f1") == 0.87
    # Should have converted both graphs to CPDAG
    assert mock_to_cpdag.call_count == 2


# Test evaluate_graph computes equiv.shd metric.
def test_evaluate_graph_equiv_shd() -> None:
    """Test that equiv.shd converts graphs to CPDAGs before comparison."""
    from causaliq_core.graph import PDAG

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

    mock_standard_metrics = {"p": 0.8, "r": 0.75, "f1": 0.77, "shd": 5}
    mock_equiv_metrics = {"p": 0.9, "r": 0.85, "f1": 0.87, "shd": 2}

    mock_pdag = MagicMock(spec=PDAG)
    mock_cpdag = MagicMock()

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        side_effect=[mock_standard_metrics, mock_equiv_metrics],
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=mock_pdag,
        ):
            with patch(
                "causaliq_core.graph.convert.pdag_to_cpdag",
                return_value=mock_cpdag,
            ) as mock_to_cpdag:
                result = provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "ref.graphml",
                        "metric": ["equiv.shd"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert _metric(result, "equiv.shd") == 2
    # Should have converted both graphs to CPDAG
    assert mock_to_cpdag.call_count == 2


# Test evaluate_graph with both standard and equiv metrics.
def test_evaluate_graph_mixed_metrics() -> None:
    """Test that both standard and equiv metrics can be requested."""
    from causaliq_core.graph import DAG

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

    mock_standard_metrics = {"p": 0.8, "r": 0.75, "f1": 0.77, "shd": 5}
    mock_equiv_metrics = {"p": 0.9, "r": 0.85, "f1": 0.87, "shd": 2}

    mock_dag = MagicMock(spec=DAG)
    mock_cpdag = MagicMock()

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        side_effect=[mock_standard_metrics, mock_equiv_metrics],
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=mock_dag,
        ):
            with patch(
                "causaliq_core.graph.convert.dag_to_pdag",
                return_value=mock_cpdag,
            ):
                result = provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "ref.graphml",
                        "metric": ["f1", "shd", "equiv.f1", "equiv.shd"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    # Standard metrics
    assert _metric(result, "f1") == 0.77
    assert _metric(result, "shd") == 5
    # Equiv metrics
    assert _metric(result, "equiv.f1") == 0.87
    assert _metric(result, "equiv.shd") == 2


# Test evaluate_graph skips equiv when PDAG not extendable to CPDAG.
def test_evaluate_graph_equiv_pdag_not_extendable() -> None:
    """Test equiv metrics skipped when PDAG not extendable."""
    from causaliq_core.graph import PDAG

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

    mock_standard_metrics = {"p": 0.8, "r": 0.75, "f1": 0.77, "shd": 5}
    mock_pdag = MagicMock(spec=PDAG)

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_standard_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=mock_pdag,
        ):
            with patch(
                "causaliq_core.graph.convert.pdag_to_cpdag",
                return_value=None,  # PDAG not extendable
            ):
                result = provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "ref.graphml",
                        "metric": ["equiv.f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert "equiv.f1" not in _block(result, "result")


# Test evaluate_graph skips equiv with unsupported graph type.
def test_evaluate_graph_equiv_unsupported_graph_type() -> None:
    """Test equiv metrics skipped when graph is neither DAG nor PDAG."""
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

    mock_standard_metrics = {"p": 0.8, "r": 0.75, "f1": 0.77, "shd": 5}
    # Create a mock that is neither DAG nor PDAG
    mock_unknown_graph = MagicMock()
    mock_unknown_graph.__class__.__name__ = "UnknownGraph"

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_standard_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=mock_unknown_graph,
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["equiv.f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert "equiv.f1" not in _block(result, "result")


# Test evaluate_graph logs warning when equiv skipped with terminal.
def test_evaluate_graph_equiv_skip_logs_warning(capsys: Any) -> None:
    """Test terminal warning printed when equiv metrics skipped."""
    from causaliq_core.graph import PDAG

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_standard_metrics = {
        "p": 0.8,
        "r": 0.75,
        "f1": 0.77,
        "shd": 5,
    }
    mock_pdag = MagicMock(spec=PDAG)

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_standard_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=mock_pdag,
        ):
            with patch(
                "causaliq_core.graph.convert.pdag_to_cpdag",
                return_value=None,
            ):
                result = provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "ref.graphml",
                        "metric": ["equiv.f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    captured = capsys.readouterr()
    assert "skipping equiv metrics" in captured.out


# Test evaluate_graph skips equiv on computation failure.
def test_evaluate_graph_equiv_computation_failure() -> None:
    """Test equiv metrics skipped when computation fails."""
    from causaliq_core.graph import DAG

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

    mock_standard_metrics = {"p": 0.8, "r": 0.75, "f1": 0.77, "shd": 5}
    mock_dag = MagicMock(spec=DAG)
    mock_cpdag = MagicMock()

    # First call to pdag_compare succeeds, second (equiv) fails
    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        side_effect=[mock_standard_metrics, ValueError("Comparison failed")],
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=mock_dag,
        ):
            with patch(
                "causaliq_core.graph.convert.dag_to_pdag",
                return_value=mock_cpdag,
            ):
                result = provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "ref.graphml",
                        "metric": ["equiv.f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert "equiv.f1" not in _block(result, "result")
