"""Unit tests for best_graph action with mocked dependencies."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def test_best_graph_creates_dag_entry() -> None:
    """Test that best_graph extracts DAG and returns graphml output."""
    from io import StringIO
    from unittest.mock import MagicMock

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Create a simple PDG
    pdg = PDG(
        ["A", "B", "C"],
        {
            ("A", "B"): EdgeProbabilities(forward=0.8, none=0.2),
            ("B", "C"): EdgeProbabilities(forward=0.7, none=0.3),
        },
    )
    buffer = StringIO()
    graphml.write_pdg(pdg, buffer)
    pdg_graphml = buffer.getvalue()

    with patch(
        "causaliq_core.graph.io.graphml.read_pdg",
    ) as mock_read:
        mock_read.return_value = pdg

        result = provider.run(
            action="best_graph",
            parameters={
                "input": pdg_graphml,
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )

    assert result[0] == "success"
    # Check metadata has extraction stats
    assert "edges_included" in result[1]
    assert result[1]["edges_included"] == 2
    # Check objects list contains optimal_dag graphml
    assert len(result[2]) == 1
    assert result[2][0]["name"] == "optimal_dag"
    assert result[2][0]["type"] == "graphml"


# Test best_graph dry-run mode skips execution.
def test_best_graph_dry_run_skips(capsys: Any) -> None:
    """Test that dry-run mode returns skipped without extracting."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    result = provider.run(
        action="best_graph",
        parameters={"input": "<pdg content>"},
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"


# Test best_graph requires input parameter.
def test_best_graph_requires_input() -> None:
    """Test that best_graph raises error without input."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="best_graph",
            parameters={},
            mode="run",
            context=None,
            logger=mock_logger,
        )

    assert "input" in str(exc_info.value)


# Test best_graph with threshold parameter.
def test_best_graph_with_threshold() -> None:
    """Test that best_graph respects threshold parameter."""
    from io import StringIO
    from unittest.mock import MagicMock

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    pdg = PDG(
        ["A", "B", "C"],
        {
            ("A", "B"): EdgeProbabilities(forward=0.8, none=0.2),
            ("B", "C"): EdgeProbabilities(forward=0.3, none=0.7),
        },
    )
    buffer = StringIO()
    graphml.write_pdg(pdg, buffer)
    pdg_graphml = buffer.getvalue()

    with patch(
        "causaliq_core.graph.io.graphml.read_pdg",
    ) as mock_read:
        mock_read.return_value = pdg

        result = provider.run(
            action="best_graph",
            parameters={
                "input": pdg_graphml,
                "threshold": 0.5,
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )

    assert result[0] == "success"
    # Should have skipped one edge (0.3 < 0.5)
    assert result[1]["edges_skipped_threshold"] == 1


# Test best_graph handles invalid PDG content.
def test_best_graph_invalid_pdg() -> None:
    """Test that best_graph handles invalid PDG content."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with patch(
        "causaliq_core.graph.io.graphml.read_pdg",
    ) as mock_read:
        mock_read.side_effect = ValueError("Invalid PDG")

        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="best_graph",
                parameters={"input": "invalid content"},
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert "PDG" in str(exc_info.value)


# Test best_graph handles FileNotFoundError.
def test_best_graph_file_not_found() -> None:
    """Test that best_graph handles FileNotFoundError."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with patch(
        "causaliq_core.graph.io.graphml.read_pdg",
    ) as mock_read:
        mock_read.side_effect = FileNotFoundError("No such file")

        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="best_graph",
                parameters={"input": "/nonexistent/file.graphml"},
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert "not found" in str(exc_info.value).lower()


# Test best_graph handles DAG extraction failure.
def test_best_graph_dag_extraction_error() -> None:
    """Test that best_graph handles to_dag_greedy failure."""
    from io import StringIO

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )
    buffer = StringIO()
    graphml.write_pdg(pdg, buffer)

    # Create a mock PDG that raises on to_dag_greedy
    mock_pdg = MagicMock()
    mock_pdg.to_dag_greedy.side_effect = RuntimeError("Algorithm failed")

    with patch(
        "causaliq_core.graph.io.graphml.read_pdg",
    ) as mock_read:
        mock_read.return_value = mock_pdg

        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="best_graph",
                parameters={"input": buffer.getvalue()},
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert "extraction failed" in str(exc_info.value).lower()


# Test best_graph with terminal logging enabled.
def test_best_graph_terminal_logging(capsys: Any) -> None:
    """Test that best_graph prints progress when terminal logging enabled."""
    from io import StringIO

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    pdg = PDG(
        ["A", "B", "C"],
        {
            ("A", "B"): EdgeProbabilities(forward=0.8, none=0.2),
            ("B", "C"): EdgeProbabilities(forward=0.7, none=0.3),
        },
    )
    buffer = StringIO()
    graphml.write_pdg(pdg, buffer)
    pdg_graphml = buffer.getvalue()

    with patch(
        "causaliq_core.graph.io.graphml.read_pdg",
    ) as mock_read:
        mock_read.return_value = pdg

        result = provider.run(
            action="best_graph",
            parameters={"input": pdg_graphml},
            mode="run",
            context=None,
            logger=mock_logger,
        )

    assert result[0] == "success"
    captured = capsys.readouterr()
    assert "Extracted DAG" in captured.out
    assert "edges" in captured.out


# Test best_graph dry-run with aggregation mode (terminal logging).
def test_best_graph_dry_run_aggregation_mode(capsys: Any) -> None:
    """Test best_graph dry-run prints aggregation mode message."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    result = provider.run(
        action="best_graph",
        parameters={
            "input": "cache.db",
            "_aggregation_entries": [{"matrix_values": {"network": "asia"}}],
        },
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"
    captured = capsys.readouterr()
    assert "Would extract DAG from 1 cache" in captured.out


# Test best_graph aggregation mode with no matching entries.
def test_best_graph_aggregation_no_entries() -> None:
    """Test best_graph raises error when no entries match."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionExecutionError, match="No cache entries matched"):
        provider.run(
            action="best_graph",
            parameters={
                "input": "cache.db",
                "_aggregation_entries": [],  # Empty entries
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test best_graph aggregation mode with multiple entries.
def test_best_graph_aggregation_multiple_entries() -> None:
    """Test best_graph raises error when multiple entries match."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionExecutionError, match="expects one entry"):
        provider.run(
            action="best_graph",
            parameters={
                "input": "cache.db",
                "_aggregation_entries": [
                    {"matrix_values": {"seed": 1}},
                    {"matrix_values": {"seed": 2}},
                ],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test best_graph aggregation mode with missing entry object.
def test_best_graph_aggregation_missing_merged_pdg() -> None:
    """Test best_graph raises error when entry lacks merged_pdg object."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionExecutionError, match="merged_pdg"):
        provider.run(
            action="best_graph",
            parameters={
                "input": "cache.db",
                "_aggregation_entries": [
                    {"matrix_values": {"network": "asia"}, "objects": {}},
                ],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test best_graph aggregation mode with invalid PDG content.
def test_best_graph_aggregation_invalid_pdg() -> None:
    """Test best_graph raises error when merged_pdg is invalid."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    with pytest.raises(ActionExecutionError, match="Failed to parse"):
        provider.run(
            action="best_graph",
            parameters={
                "input": "cache.db",
                "_aggregation_entries": [
                    {
                        "matrix_values": {"network": "asia"},
                        "objects": {"merged_pdg": "not valid graphml"},
                    },
                ],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )


# Test best_graph aggregation mode success.
def test_best_graph_aggregation_success() -> None:
    """Test best_graph aggregation mode extracts DAG from cache entry."""
    from io import StringIO

    from causaliq_core.graph import PDG, EdgeProbabilities
    from causaliq_core.graph.io import graphml

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Create a PDG and serialize it
    pdg = PDG(
        ["A", "B"],
        {("A", "B"): EdgeProbabilities(forward=0.8, none=0.2)},
    )
    buffer = StringIO()
    graphml.write_pdg(pdg, buffer)
    pdg_graphml = buffer.getvalue()

    result = provider.run(
        action="best_graph",
        parameters={
            "input": "cache.db",
            "_aggregation_entries": [
                {
                    "matrix_values": {"network": "asia"},
                    "objects": {"merged_pdg": pdg_graphml},
                },
            ],
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "success"
    assert result[1]["edges_included"] == 1
    assert len(result[2]) == 1
    assert result[2][0]["name"] == "optimal_dag"


# Test best_graph direct mode without input path.
def test_best_graph_direct_mode_no_input() -> None:
    """Test best_graph raises error in direct mode without input."""
    from causaliq_analysis.workflow_action import (
        ActionExecutionError,
        AnalysisActionProvider,
    )

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Empty input string passes validation but fails at runtime
    with pytest.raises(ActionExecutionError, match="requires 'input'"):
        provider.run(
            action="best_graph",
            parameters={
                "input": "",  # Empty string passes validation
                "threshold": 0.5,
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
