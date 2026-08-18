"""Unit tests for evaluate_graph action with mocked dependencies."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from .conftest import VALID_GRAPHML, create_mock_graphml_entry


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
                    "_update_entry": update_entry,
                    "reference": "ref.graphml",
                    "metric": ["f1", "shd", "precision", "recall"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert result[1]["precision"] == 1.0
    assert result[1]["recall"] == 1.0
    assert result[1]["f1"] == 1.0
    assert result[1]["shd"] == 0
    assert result[1]["reference"] == "ref.graphml"


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
            "_update_entry": update_entry,
            "reference": "ref.graphml",
            "metric": ["f1"],
        },
        mode="dry-run",
        context=None,
        logger=mock_logger,
    )

    assert result[0] == "skipped"
    captured = capsys.readouterr()
    assert "Would evaluate graph" in captured.out


# Test evaluate_graph requires _update_entry parameter.
def test_evaluate_graph_requires_update_entry() -> None:
    """Test error when _update_entry is not provided."""
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
    assert "_update_entry" in str(exc_info.value)


# Test evaluate_graph requires reference parameter.
def test_evaluate_graph_requires_reference() -> None:
    """Test error when reference is not provided."""
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
            parameters={"_update_entry": update_entry, "metric": ["f1"]},
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "reference" in str(exc_info.value)


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
                "_update_entry": update_entry,
                "reference": "ref.graphml",
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "metric" in str(exc_info.value)


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
                "_update_entry": update_entry,
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
                "_update_entry": update_entry,
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "No evaluable graph object found" in str(exc_info.value)


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
                "_update_entry": update_entry,
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


# PDG GraphML content for testing (has p_forward key).
PDG_GRAPHML = """<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="p_forward" for="edge" attr.name="p_forward" attr.type="double"/>
  <key id="p_reverse" for="edge" attr.name="p_reverse" attr.type="double"/>
  <graph id="G" edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <edge source="A" target="B">
      <data key="p_forward">0.8</data>
      <data key="p_reverse">0.2</data>
    </edge>
  </graph>
</graphml>"""


# Test evaluate_graph rejects PDG content even if typed as dag.
def test_evaluate_graph_rejects_pdg_content() -> None:
    """Test error when object content is actually PDG (has p_forward)."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # Object typed as 'dag' but content is PDG
    mock_obj = MagicMock()
    mock_obj.type = "dag"
    mock_obj.format = "graphml"
    mock_obj.content = PDG_GRAPHML

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
                "_update_entry": update_entry,
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "PDG data" in str(exc_info.value)
    assert "p_forward" in str(exc_info.value)


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
                "_update_entry": update_entry,
                "reference": "ref.graphml",
                "metric": ["f1"],
            },
            mode="run",
            context=None,
            logger=mock_logger,
        )
    assert "Failed to parse graph" in str(exc_info.value)


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
                    "_update_entry": update_entry,
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
                    "_update_entry": update_entry,
                    "reference": "corrupt.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "Failed to read reference graph" in str(exc_info.value)


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
                        "_update_entry": update_entry,
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
                    "_update_entry": update_entry,
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
                    "_update_entry": update_entry,
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert result[1]["evaluated_graph"] == "dag"


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
                    "_update_entry": update_entry,
                    "reference": "ref.graphml",
                    "metric": ["f1", "shd"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert result[1]["evaluated_graph"] == "dag"
    # Verify get_object was only called for dag, not pdg
    mock_entry.get_object.assert_called_with("dag")


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
                    "_update_entry": update_entry,
                    "reference": "ref.graphml",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"


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
                    "_update_entry": update_entry,
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
    assert result[1]["reference"] == "networks/asia/asia.xdsl"


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
                    "_update_entry": update_entry,
                    "reference": "networks/asia/asia.dsc",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

            mock_read_bn.assert_called_once_with("networks/asia/asia.dsc")

    assert result[0] == "success"


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
                    "_update_entry": update_entry,
                    "reference": "ref.graphml",
                    "metric": "f1",
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    # Should only contain f1, not precision/recall/shd
    assert "f1" in result[1]
    assert "precision" not in result[1]
    assert "recall" not in result[1]
    assert "shd" not in result[1]
    # Reference info always included
    assert "reference" in result[1]
    assert "evaluated_graph" in result[1]


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
                    "_update_entry": update_entry,
                    "reference": "ref.graphml",
                    "metric": ["f1", "shd"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    # Should contain f1 and shd, not precision/recall
    assert "f1" in result[1]
    assert "shd" in result[1]
    assert "precision" not in result[1]
    assert "recall" not in result[1]


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
                        "_update_entry": update_entry,
                        "reference": "ref.graphml",
                        "metric": ["equiv.f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert "equiv.f1" in result[1]
    assert result[1]["equiv.f1"] == 0.87
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
                        "_update_entry": update_entry,
                        "reference": "ref.graphml",
                        "metric": ["equiv.shd"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert "equiv.shd" in result[1]
    assert result[1]["equiv.shd"] == 2
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
                        "_update_entry": update_entry,
                        "reference": "ref.graphml",
                        "metric": ["f1", "shd", "equiv.f1", "equiv.shd"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    # Standard metrics
    assert result[1]["f1"] == 0.77
    assert result[1]["shd"] == 5
    # Equiv metrics
    assert result[1]["equiv.f1"] == 0.87
    assert result[1]["equiv.shd"] == 2


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
                        "_update_entry": update_entry,
                        "reference": "ref.graphml",
                        "metric": ["equiv.f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert "equiv.f1" not in result[1]


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
                    "_update_entry": update_entry,
                    "reference": "ref.graphml",
                    "metric": ["equiv.f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert "equiv.f1" not in result[1]


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
                        "_update_entry": update_entry,
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
                        "_update_entry": update_entry,
                        "reference": "ref.graphml",
                        "metric": ["equiv.f1"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert "equiv.f1" not in result[1]


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
                        "_update_entry": update_entry,
                        "reference": "results/legacy.db",
                        "metric": ["f1", "shd"],
                    },
                    mode="run",
                    context=None,
                    logger=mock_logger,
                )

    assert result[0] == "success"
    assert result[1]["f1"] == 1.0
    assert result[1]["shd"] == 0
    assert result[1]["reference"] == "results/legacy.db"
    assert result[1]["evaluated_graph"] == "dag"
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
                    "_update_entry": update_entry,
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
                    "_update_entry": update_entry,
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
                    "_update_entry": update_entry,
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
                    "_update_entry": update_entry,
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "No evaluable graph object found" in str(exc_info.value)
    assert "reference cache entry" in str(exc_info.value)


# Test evaluate_graph rejects a PDG inside a reference cache entry.
def test_evaluate_graph_cache_reference_pdg() -> None:
    """Test error when reference cache entry contains a PDG object."""
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
    mock_pdg_obj.type = "dag"
    mock_pdg_obj.format = "graphml"
    mock_pdg_obj.content = PDG_GRAPHML

    pdg_entry = MagicMock()
    pdg_entry.object_types.return_value = ["dag"]
    pdg_entry.get_object.return_value = mock_pdg_obj

    mock_cache = MagicMock()
    mock_cache.list_entries.return_value = [{"matrix_values": {"seed": 42}}]
    mock_cache.get.return_value = pdg_entry
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
                    "_update_entry": update_entry,
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "PDG data" in str(exc_info.value)
    assert "p_forward" in str(exc_info.value)


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
                    "_update_entry": update_entry,
                    "reference": "legacy.db",
                    "metric": ["f1"],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )
    assert "Failed to read reference cache" in str(exc_info.value)
