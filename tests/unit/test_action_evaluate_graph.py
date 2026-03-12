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
    mock_entry.object_names.return_value = []

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
    assert "No graphml object found" in str(exc_info.value)


# Test evaluate_graph handles invalid graphml in entry.
def test_evaluate_graph_invalid_graphml() -> None:
    """Test error when entry graphml content is invalid."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    mock_obj = MagicMock()
    mock_obj.type = "graphml"
    mock_obj.content = "invalid xml"

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["graph.graphml"]
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


# Test evaluate_graph includes Bayesys metrics when requested.
def test_evaluate_graph_with_bayesys() -> None:
    """Test that Bayesys metrics are included when bayesys parameter set."""
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

    # Note: pdag_compare uses 'p', 'r', 'p-b', 'r-b', 'f1-b', 'shd-b'
    mock_metrics = {
        "p": 0.8,
        "r": 0.9,
        "f1": 0.85,
        "shd": 2,
        "p-b": 0.7,
        "r-b": 0.8,
        "f1-b": 0.75,
        "shd-b": 3,
        "ddm": 1.5,
        "bsf": 0.9,
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
                    "bayesys": "3.0",
                    "metric": [
                        "precision_b",
                        "recall_b",
                        "f1_b",
                        "shd_b",
                        "ddm",
                        "bsf",
                    ],
                },
                mode="run",
                context=None,
                logger=mock_logger,
            )

    assert result[0] == "success"
    assert result[1]["precision_b"] == 0.7
    assert result[1]["ddm"] == 1.5
    assert result[1]["bsf"] == 0.9
    assert result[1]["bayesys"] == "3.0"


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


# Test evaluate_graph skips non-graphml objects.
def test_evaluate_graph_skips_non_graphml() -> None:
    """Test that non-graphml objects are skipped when finding graph."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # First object is not graphml, second is
    mock_obj_json = MagicMock()
    mock_obj_json.type = "json"

    mock_obj_graphml = MagicMock()
    mock_obj_graphml.type = "graphml"
    mock_obj_graphml.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["data.json", "graph.graphml"]
    mock_entry.get_object.side_effect = [mock_obj_json, mock_obj_graphml]

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
    assert result[1]["evaluated_graph"] == "graph.graphml"


# Test evaluate_graph handles None object in entry.
def test_evaluate_graph_skips_none_object() -> None:
    """Test that None objects in entry are skipped."""
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    provider = AnalysisActionProvider()
    mock_logger = MagicMock()
    mock_logger.is_terminal_logging = False

    # First object returns None, second is valid
    mock_obj_graphml = MagicMock()
    mock_obj_graphml.type = "graphml"
    mock_obj_graphml.content = VALID_GRAPHML

    mock_entry = MagicMock()
    mock_entry.object_names.return_value = ["orphan.graphml", "graph.graphml"]
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
