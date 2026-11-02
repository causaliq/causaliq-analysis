"""Unit tests for evaluate_graph reference resolution."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from .conftest import (
    VALID_PDG_GRAPHML,
    create_mock_graphml_entry,
)
from .evaluate_graph_support import (
    _block,
    _metric,
)


# Test evaluate_graph handles nonexistent reference file.
def test_evaluate_graph_reference_not_found() -> None:
    """Test error when reference file does not exist."""
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

    # Patch graphml.read in workflow_action to use real parsing for entry
    # but raise FileNotFoundError for reference
    def mock_read(source: Any) -> Any:
        from io import StringIO

        if isinstance(source, StringIO):
            # This is the entry graph - return a mock
            return MagicMock()
        # This is the reference file - simulate not found
        raise FileNotFoundError(f"No such file: {source}")

    with patch(
        "causaliq_core.graph.io.graphml.read",
        side_effect=mock_read,
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "nonexistent.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "Reference graph not found" in str(exc_info.value)


# Test evaluate_graph handles reference read error.
def test_evaluate_graph_reference_read_error() -> None:
    """Test error when reference file cannot be read."""
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

    def mock_read(source: Any) -> Any:
        from io import StringIO

        if isinstance(source, StringIO):
            return MagicMock()
        raise ValueError("Corrupt file")

    with patch(
        "causaliq_core.graph.io.graphml.read",
        side_effect=mock_read,
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "corrupt.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "Failed to read reference graph" in str(exc_info.value)


# Test evaluate_graph reads xdsl reference files.
def test_evaluate_graph_xdsl_reference() -> None:
    """Test that .xdsl reference files are read via read_bn."""
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
        "p": 1.0,
        "r": 1.0,
        "f1": 1.0,
        "shd": 0,
    }

    # Mock read_bn to return a BN with a dag attribute
    mock_bn = MagicMock()
    mock_bn.dag = MagicMock()

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.bn.io.read_bn",
            return_value=mock_bn,
        ) as mock_read_bn:
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "networks/asia/asia.xdsl",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

            # Verify read_bn was called for .xdsl file
            mock_read_bn.assert_called_once_with("networks/asia/asia.xdsl")

    assert result[0] == "success"
    assert _block(result, "parameters")["reference"] == (
        "networks/asia/asia.xdsl"
    )


# Test evaluate_graph reads dsc reference files.
def test_evaluate_graph_dsc_reference() -> None:
    """Test that .dsc reference files are read via read_bn."""
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
        "shd": 2,
    }

    mock_bn = MagicMock()
    mock_bn.dag = MagicMock()

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.bn.io.read_bn",
            return_value=mock_bn,
        ) as mock_read_bn:
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "networks/asia/asia.dsc",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

            mock_read_bn.assert_called_once_with("networks/asia/asia.dsc")

    assert result[0] == "success"


# Test evaluate_graph resolves reference graph from a workflow cache.
def test_evaluate_graph_cache_reference_returns_metrics() -> None:
    """Test metrics computed against reference graph from a cache."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"network": "asia", "sample_size": 100},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics = {
        "p": 1.0,
        "r": 1.0,
        "f1": 1.0,
        "shd": 0,
    }

    # Reference cache with identical key structure and a graph entry
    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [
        {"matrix_values": {"network": "asia", "sample_size": 100}}
    ]
    mock_cache.get.return_value = create_mock_graphml_entry()
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            with patch(
                "causaliq_workflow.cache.WorkflowCache",
                return_value=mock_cache,
            ) as mock_workflow_cache:
                result = provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "results/legacy.db",
                        "metric": ["f1", "shd"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert _metric(result, "f1") == 1.0
    assert _metric(result, "shd") == 0
    assert _block(result, "parameters")["reference"] == "results/legacy.db"
    mock_workflow_cache.assert_called_once_with("results/legacy.db")
    mock_cache.get.assert_called_once_with(
        {"network": "asia", "sample_size": 100}
    )


# Test evaluate_graph rejects mismatched reference cache key names.
def test_evaluate_graph_cache_reference_key_structure_mismatch() -> None:
    """Test error when reference cache uses different matrix key names."""
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

    # Reference cache uses 'network' instead of 'seed'
    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [
        {"matrix_values": {"network": "asia"}}
    ]
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "key structure does not match" in str(exc_info.value)
    assert "seed" in str(exc_info.value)
    assert "network" in str(exc_info.value)


# Test evaluate_graph rejects empty reference cache.
def test_evaluate_graph_cache_reference_empty() -> None:
    """Test error when reference cache contains no entries."""
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

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = []
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "Reference cache is empty" in str(exc_info.value)


# Test evaluate_graph rejects reference cache without matching values.
def test_evaluate_graph_cache_reference_no_matching_entry() -> None:
    """Test error when no reference entry matches the input matrix values."""
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

    # Key names match but the value differs from the current input entry
    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 43}}]
    mock_cache.get.return_value = None
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "No entry in reference cache" in str(exc_info.value)
    assert "42" in str(exc_info.value)


# Test evaluate_graph reports missing graph in a reference cache entry.
def test_evaluate_graph_cache_reference_no_graph() -> None:
    """Test error when reference cache entry contains no graph."""
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

    # Matching entry exists but contains no evaluable graph
    empty_ref_entry = MagicMock()
    empty_ref_entry.object_types.return_value = []

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 42}}]
    mock_cache.get.return_value = empty_ref_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "No evaluable graph object found" in str(exc_info.value)
    assert "reference cache entry" in str(exc_info.value)


# Test evaluate_graph evaluates a PDG inside a reference cache entry.
def test_evaluate_graph_cache_reference_pdg() -> None:
    """Test PDG inside a reference cache entry is evaluated."""
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

    mock_pdg_obj = MagicMock()
    mock_pdg_obj.type = "pdg"
    mock_pdg_obj.format = "graphml"
    mock_pdg_obj.content = VALID_PDG_GRAPHML

    pdg_entry = MagicMock()
    pdg_entry.object_types.return_value = ["pdg"]
    pdg_entry.get_object.return_value = mock_pdg_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 42}}]
    mock_cache.get.return_value = pdg_entry
    mock_cache.__enter__ = MagicMock(return_value=mock_cache)
    mock_cache.__exit__ = MagicMock(return_value=False)

    mock_metrics = {"p": 0.5, "r": 0.5, "f1": 0.5, "shd": 0.5}

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        return_value=mock_cache,
    ):
        with patch(
            "causaliq_analysis.metrics.pdg_compare",
            return_value=mock_metrics,
        ):
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert _metric(result, "f1") == 0.5


# Test evaluate_graph handles reference cache read failures.
def test_evaluate_graph_cache_reference_read_error() -> None:
    """Test error when the reference cache cannot be opened."""
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

    with patch(
        "causaliq_workflow.cache.WorkflowCache",
        side_effect=RuntimeError("not a database"),
    ):
        with pytest.raises(Exception) as exc_info:
            provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "Failed to read reference cache" in str(exc_info.value)
