"""Unit tests for the plot workflow action."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from causaliq_analysis.workflow_action import AnalysisActionProvider


def _make_logger() -> MagicMock:
    """Create a mock logger without terminal logging."""
    logger = MagicMock()
    logger.is_terminal_logging = False
    return logger


def _valid_parameters() -> Dict[str, Any]:
    """Return valid plot action parameters."""
    return {
        "input": "results.csv",
        "output": "chart.png",
        "type": "line",
        "subplot": "network",
        "group": "series",
        "x": "sample_size",
        "y": "f1.mean",
        "properties": ["xaxis.label=Sample size"],
    }


# Plot action requires the input parameter.
def test_plot_requires_input() -> None:
    """Test plot raises error without the input parameter."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    del parameters["input"]

    with pytest.raises(ActionValidationError, match="requires 'input'"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action requires the output parameter.
def test_plot_requires_output() -> None:
    """Test plot raises error without the output parameter."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    del parameters["output"]

    with pytest.raises(ActionValidationError, match="requires 'output'"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action requires the column name parameters.
def test_plot_requires_columns() -> None:
    """Test plot raises error without subplot, group, x and y."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    del parameters["subplot"]
    del parameters["x"]

    with pytest.raises(ActionValidationError, match="requires 'subplot'"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action rejects invalid plot types.
def test_plot_rejects_invalid_type() -> None:
    """Test plot raises error for unsupported plot types."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    parameters["type"] = "pie"

    with pytest.raises(ActionValidationError, match="Unknown plot type"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action rejects non-CSV input files.
def test_plot_rejects_non_csv_input() -> None:
    """Test plot raises error when input is not a CSV file."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    parameters["input"] = "results.db"

    with pytest.raises(ActionValidationError, match="must be a CSV file"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action rejects non-image output files.
def test_plot_rejects_non_image_output() -> None:
    """Test plot raises error when output is not an image file."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    parameters["output"] = "chart.txt"

    with pytest.raises(ActionValidationError, match="must be an image file"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action rejects malformed property strings.
def test_plot_rejects_invalid_properties() -> None:
    """Test plot raises error for malformed property strings."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    parameters["properties"] = ["=bad"]

    with pytest.raises(ActionValidationError, match="Invalid plot properties"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action rejects legacy colon-separated properties.
def test_plot_rejects_legacy_properties() -> None:
    """Test plot raises error for legacy colon property strings."""
    from causaliq_core import ActionValidationError

    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    parameters["properties"] = ["xaxis.label:Sample size"]

    with pytest.raises(ActionValidationError, match="Invalid plot properties"):
        provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )


# Plot action accepts equals-separated Python literal properties.
def test_plot_accepts_equals_properties() -> None:
    """Test plot validation passes for Python literal properties."""
    provider = AnalysisActionProvider()
    parameters = _valid_parameters()
    parameters["properties"] = [
        "int.property=22",
        "dict.property={'key1': 1}",
        "list.property=['a', 1]",
    ]

    with patch(
        "causaliq_analysis.workflow_action.run_plot",
        return_value={"output": "chart.png", "type": "line"},
    ):
        status, _, _ = provider.run(
            action="plot",
            parameters=parameters,
            mode="run",
            context=None,
            logger=_make_logger(),
        )

    assert status == "success"


# Plot action supports dry-run mode.
def test_plot_dry_run() -> None:
    """Test plot returns skipped in dry-run mode."""
    provider = AnalysisActionProvider()

    status, metadata, objects = provider.run(
        action="plot",
        parameters=_valid_parameters(),
        mode="dry-run",
        context=None,
        logger=_make_logger(),
    )

    assert status == "skipped"
    assert "Dry-run mode" in metadata["message"]
    assert objects == []


# Plot action runs successfully and returns metadata.
def test_plot_runs_successfully() -> None:
    """Test plot returns success when run_plot completes."""
    provider = AnalysisActionProvider()

    with patch(
        "causaliq_analysis.workflow_action.run_plot",
        return_value={"output": "chart.png", "type": "line"},
    ) as mock_plot:
        status, metadata, objects = provider.run(
            action="plot",
            parameters=_valid_parameters(),
            mode="run",
            context=None,
            logger=_make_logger(),
        )

    assert status == "success"
    assert metadata["output"] == "chart.png"
    assert objects == []
    mock_plot.assert_called_once()
    call_kwargs = mock_plot.call_args.kwargs
    assert call_kwargs["kind"] == "line"
    assert call_kwargs["subplot"] == "network"
    assert call_kwargs["group"] == "series"


# Plot action reports execution failures.
def test_plot_run_failure() -> None:
    """Test plot raises ActionExecutionError when run_plot fails."""
    from causaliq_core import ActionExecutionError

    provider = AnalysisActionProvider()

    with patch(
        "causaliq_analysis.workflow_action.run_plot",
        side_effect=ValueError("boom"),
    ):
        with pytest.raises(ActionExecutionError, match="Plot failed"):
            provider.run(
                action="plot",
                parameters=_valid_parameters(),
                mode="run",
                context=None,
                logger=_make_logger(),
            )


# Plot action re-raises ActionExecutionError from run_plot.
def test_plot_re_raises_execution_error() -> None:
    """Test plot re-raises ActionExecutionError from run_plot."""
    from causaliq_core import ActionExecutionError

    provider = AnalysisActionProvider()

    with patch(
        "causaliq_analysis.workflow_action.run_plot",
        side_effect=ActionExecutionError("boom"),
    ):
        with pytest.raises(ActionExecutionError, match="boom"):
            provider.run(
                action="plot",
                parameters=_valid_parameters(),
                mode="run",
                context=None,
                logger=_make_logger(),
            )


# Plot action is registered as a nocaches pattern.
def test_plot_action_pattern() -> None:
    """Test plot is registered with the nocaches action pattern."""
    from causaliq_core import ActionPattern

    provider = AnalysisActionProvider()
    assert provider.action_patterns["plot"] == ActionPattern.NOCACHES
    assert "plot" in provider.supported_actions
    assert "plot_file" in provider.outputs


# Plot action dry-run logs to the terminal when enabled.
def test_plot_dry_run_terminal_logging(capsys) -> None:
    """Test plot dry-run prints a message with terminal logging."""
    provider = AnalysisActionProvider()
    logger = _make_logger()
    logger.is_terminal_logging = True

    status, _, _ = provider.run(
        action="plot",
        parameters=_valid_parameters(),
        mode="dry-run",
        context=None,
        logger=logger,
    )

    assert status == "skipped"
    captured = capsys.readouterr()
    assert "Would plot line from results.csv to chart.png" in captured.out


# Plot action uses print as the log function with terminal logging.
def test_plot_runs_with_terminal_logging(capsys) -> None:
    """Test plot passes print as the log function when enabled."""
    provider = AnalysisActionProvider()
    logger = _make_logger()
    logger.is_terminal_logging = True

    with patch(
        "causaliq_analysis.workflow_action.run_plot",
        return_value={"output": "chart.png", "type": "line"},
    ) as mock_plot:
        status, _, _ = provider.run(
            action="plot",
            parameters=_valid_parameters(),
            mode="run",
            context=None,
            logger=logger,
        )

    assert status == "success"
    mock_plot.assert_called_once()
    assert mock_plot.call_args.kwargs["log_fn"] is print
