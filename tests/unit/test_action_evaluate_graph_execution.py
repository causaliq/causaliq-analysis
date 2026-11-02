"""Unit tests for evaluate_graph execution and graph extraction."""

from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from causaliq_analysis.workflow_action import helpers

from .conftest import (
    VALID_GRAPHML,
    VALID_PDG_GRAPHML,
    create_mock_graphml_entry,
)
from .evaluate_graph_support import (
    _block,
    _metric,
)


# Test evaluate_graph records a failed input run as a failure.
def test_evaluate_graph_records_input_failure() -> None:
    """A failed input run is recorded, not evaluated."""
    from causaliq_workflow.cache import CacheEntry

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    update_entry = {
        "matrix_values": {"network": "asia"},
        "metadata": {
            "causaliq-discovery": {
                "learn_graph": {"status": "input_error", "error": "boom"}
            }
        },
        "entry": CacheEntry(),
    }

    result = provider.run(
        action="evaluate_graph",
        parameters={
            "_aggregation_entries": [update_entry],
            "output": "metrics.db",
            "reference": "ref.graphml",
            "metric": ["f1"],
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "error"
    assert _block(result, "result")["status"] == "input_failed"
    assert _block(result, "result")["error"] == "No graph present"
    assert _block(result, "parameters")["reference"] == "ref.graphml"
    assert result[2] == []


# Test _input_failure returns an error recorded in a history block.
def test_input_failure_uses_history_error() -> None:
    """A failed upstream result carried in history is reported."""
    from causaliq_analysis.workflow_action.actions.evaluate_graph import (
        _input_failure,
    )

    metadata = {
        "provenance": {
            "provider": "causaliq-analysis",
            "action": "evaluate_graph",
        },
        "inputs": {},
        "result": {"status": "ok"},
        "history": {
            "causaliq-discovery.learn_graph": {
                "inputs": {},
                "result": {"status": "input_error", "error": "history boom"},
            }
        },
    }

    assert _input_failure({"metadata": metadata}) == "history boom"


# Test _input_failure ignores a history value that is not a block.
def test_input_failure_ignores_non_mapping_history() -> None:
    """A scalar history value does not record a failure."""
    from causaliq_analysis.workflow_action.actions.evaluate_graph import (
        _input_failure,
    )

    metadata = {
        "provenance": {
            "provider": "causaliq-analysis",
            "action": "evaluate_graph",
        },
        "inputs": {},
        "result": {},
        "history": {"causaliq-discovery.learn_graph": "not a block"},
    }

    assert _input_failure({"metadata": metadata}) is None


# Test evaluate_graph ignores metadata that records no error.
def test_evaluate_graph_ignores_metadata_without_errors() -> None:
    """Test only a recorded error marks an input run as failed."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = create_mock_graphml_entry()

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {
            "causaliq-discovery": "ok",
            "causaliq-analysis": {"evaluate_graph": {"status": "ok"}},
        },
        "entry": mock_entry,
    }

    mock_metrics = {"p": 1.0, "r": 1.0, "f1": 1.0, "shd": 0}

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch("causaliq_core.graph.io.graphml.read") as mock_read:
            mock_read.return_value = MagicMock()

            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"


# Test evaluate_graph reports an input failure to the terminal.
def test_evaluate_graph_logs_input_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test the recorded failure is logged when terminal logging is on."""
    from causaliq_workflow.cache import CacheEntry

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = True

    update_entry = {
        "matrix_values": {"network": "asia"},
        "metadata": {
            "causaliq-discovery": {
                "learn_graph": {"status": "input_error", "error": "boom"}
            }
        },
        "entry": CacheEntry(),
    }

    result = provider.run(
        action="evaluate_graph",
        parameters={
            "_aggregation_entries": [update_entry],
            "output": "metrics.db",
            "reference": "ref.graphml",
            "metric": ["f1"],
        },
        mode="run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "error"
    assert "Recording input failure: boom" in capsys.readouterr().out


# Test evaluate_graph handles None entry object.
def test_evaluate_graph_no_entry_object() -> None:
    """Test error when entry object is None."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": None,
    }

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="evaluate_graph",
            parameters={
                "_aggregation_entries": [update_entry],
                "output": "metrics.db",
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "No entry object" in str(exc_info.value)


# Test evaluate_graph handles entry with no graphml.
def test_evaluate_graph_no_graphml_in_entry() -> None:
    """Test error when cache entry has no graphml object."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = []

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="evaluate_graph",
            parameters={
                "_aggregation_entries": [update_entry],
                "output": "metrics.db",
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "No evaluable graph object found" in str(exc_info.value)
    assert "--mode force" in str(exc_info.value)


# Test evaluate_graph rejects PDG-only entries.
def test_evaluate_graph_rejects_pdg_only() -> None:
    """Test error when entry only has PDG (not evaluable)."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_obj = MagicMock()
    mock_obj.type = "pdg"
    mock_obj.format = "graphml"
    mock_obj.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["pdg"]
    mock_entry.get_object.return_value = mock_obj

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="evaluate_graph",
            parameters={
                "_aggregation_entries": [update_entry],
                "output": "metrics.db",
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "No evaluable graph object found" in str(exc_info.value)
    assert "dag" in str(exc_info.value)
    assert "pdag" in str(exc_info.value)
    assert "cpdag" in str(exc_info.value)


# Test evaluate_graph evaluates PDG content as a PDG.
def test_evaluate_graph_accepts_pdg_content() -> None:
    """Test PDG content (with p_forward) is evaluated as a PDG."""
    from causaliq_core.graph import PDG

    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Object typed as 'dag' but content is PDG
    mock_obj = MagicMock()
    mock_obj.type = "dag"
    mock_obj.format = "graphml"
    mock_obj.content = VALID_PDG_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["dag"]
    mock_entry.get_object.return_value = mock_obj

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics = {"p": 0.5, "r": 0.5, "f1": 0.5, "shd": 0.5}

    with patch(
        "causaliq_analysis.graph_io.read_graph_or_pdg_file",
        return_value=MagicMock(spec=PDG),
    ):
        with patch(
            "causaliq_analysis.metrics.pdg_compare",
            return_value=mock_metrics,
        ) as mock_pdg_compare:
            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    mock_pdg_compare.assert_called_once()
    assert _metric(result, "f1") == 0.5


# Test evaluate_graph handles invalid graphml in entry.
def test_evaluate_graph_invalid_graphml() -> None:
    """Test error when entry graphml content is invalid."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_obj = MagicMock()
    mock_obj.type = "dag"
    mock_obj.format = "graphml"
    mock_obj.content = "invalid xml"

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["dag"]
    mock_entry.get_object.return_value = mock_obj

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    with pytest.raises(Exception) as exc_info:
        provider.run(
            action="evaluate_graph",
            parameters={
                "_aggregation_entries": [update_entry],
                "output": "metrics.db",
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "Failed to parse graph" in str(exc_info.value)


# Test evaluate_graph handles metric computation failure.
def test_evaluate_graph_metric_failure() -> None:
    """Test error when pdag_compare raises an exception."""
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
        "causaliq_analysis.metrics.pdag_compare",
        side_effect=ValueError("Node mismatch"),
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
            return_value=MagicMock(),
        ):
            with pytest.raises(Exception) as exc_info:
                provider.run(
                    action="evaluate_graph",
                    parameters={
                        "_aggregation_entries": [update_entry],
                        "output": "metrics.db",
                        "reference": "ref.graphml",
                        "metric": ["f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )
    assert "Metric computation failed" in str(exc_info.value)


# Test evaluate_graph logs result with terminal logging.
def test_evaluate_graph_logs_result(capsys: Any) -> None:
    """Test that result is logged when terminal logging enabled."""
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
            provider.run(
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

    captured = capsys.readouterr()
    assert "Evaluated" in captured.out
    assert "F1=" in captured.out
    assert "SHD=" in captured.out


# Test evaluate_graph skips non-evaluable object types.
def test_evaluate_graph_skips_non_graphml() -> None:
    """Test that non-evaluable types (e.g. pdg) are skipped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # pdg is skipped, dag is used
    mock_obj_pdg = MagicMock()
    mock_obj_pdg.type = "pdg"
    mock_obj_pdg.format = "graphml"
    mock_obj_pdg.content = VALID_GRAPHML

    mock_obj_graphml = MagicMock()
    mock_obj_graphml.type = "dag"
    mock_obj_graphml.format = "graphml"
    mock_obj_graphml.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["pdg", "dag"]
    # get_object only called for dag (pdg skipped by type filter)
    mock_entry.get_object.return_value = mock_obj_graphml

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

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
        ) as mock_read:
            mock_read.return_value = MagicMock()

            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    mock_entry.get_object.assert_called_with("dag")


# Test evaluate_graph prioritises DAG over PDG.
def test_evaluate_graph_uses_dag_not_pdg() -> None:
    """Test that evaluate_graph uses DAG when both PDG and DAG exist."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Entry has both pdg and dag - only dag should be evaluated
    mock_obj_dag = MagicMock()
    mock_obj_dag.type = "dag"
    mock_obj_dag.format = "graphml"
    mock_obj_dag.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["pdg", "dag"]
    mock_entry.get_object.return_value = mock_obj_dag

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics = {"p": 0.9, "r": 0.8, "f1": 0.85, "shd": 2}

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch("causaliq_core.graph.io.graphml.read") as mock_read:
            mock_read.return_value = MagicMock()

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
    # Verify get_object was only called for dag, not pdg
    mock_entry.get_object.assert_called_with("dag")


# Test evaluate_graph skips object types outside the evaluable set.
def test_evaluate_graph_skips_unknown_object_types() -> None:
    """Test that unsupported object types in an entry are skipped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Entry has an unsupported type before a valid dag object
    mock_obj = MagicMock()
    mock_obj.type = "dag"
    mock_obj.format = "graphml"
    mock_obj.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["bn", "dag"]
    mock_entry.get_object.return_value = mock_obj

    update_entry = {
        "matrix_values": {"seed": 42},
        "metadata": {},
        "entry": mock_entry,
    }

    mock_metrics = {"p": 1.0, "r": 1.0, "f1": 1.0, "shd": 0}

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch("causaliq_core.graph.io.graphml.read") as mock_read:
            mock_read.return_value = MagicMock()

            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    # The unsupported 'bn' type was skipped, never requested
    assert mock_entry.get_object.call_args_list == [call("dag")]


# Test evaluate_graph handles None object in entry.
def test_evaluate_graph_skips_none_object() -> None:
    """Test that None objects in entry are skipped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # First valid type returns None, second is valid
    mock_obj_graphml = MagicMock()
    mock_obj_graphml.type = "dag"
    mock_obj_graphml.format = "graphml"
    mock_obj_graphml.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_types.return_value = ["pdag", "dag"]
    mock_entry.get_object.side_effect = [None, mock_obj_graphml]

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

    with patch(
        "causaliq_analysis.metrics.pdag_compare",
        return_value=mock_metrics,
    ):
        with patch(
            "causaliq_core.graph.io.graphml.read",
        ) as mock_read:
            mock_read.return_value = MagicMock()

            result = provider.run(
                action="evaluate_graph",
                parameters={
                    "_aggregation_entries": [update_entry],
                    "output": "metrics.db",
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"


# Test the provider delegate for entry graph extraction.
def test_extract_graph_from_entry_helper() -> None:
    """Test the shared helper extracts a graph from an entry."""

    mock_entry = create_mock_graphml_entry()

    graph, graph_type = helpers._extract_graph_from_entry(
        mock_entry, "cache entry"
    )

    assert graph_type == "dag"
    assert graph is not None
