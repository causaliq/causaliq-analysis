"""
Plot workflow action.

Generates a publication-ready chart from a summarise CSV output. The action
is stateless, so validation and execution delegate to module-level helpers
and each step stays within the module and method limits.
"""

from typing import Any, Dict, Optional

from causaliq_analysis.plot import run_plot
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionPattern,
    ActionResult,
)

__all__ = ["PlotAction"]

# Image formats accepted for the chart output
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".svg", ".pdf")

# Column name parameters required by every plot
_COLUMN_PARAMETERS = ("subplot", "group", "x", "y")


class PlotAction(AnalysisAction):
    """Generate a chart from a summarise CSV output.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "plot"
    pattern = ActionPattern.NOCACHES

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate plot parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        _require_csv_input(parameters)
        _require_image_output(parameters)
        _require_column_parameters(parameters)
        _require_known_kind(parameters)
        _require_parseable_properties(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Execute chart generation from a summarise CSV output.

        Reads the input CSV, builds the long-form data required by the
        legacy plotting functions and writes the output chart file.

        Args:
            parameters: Action parameter values.
            mode: Execution mode ('dry-run', 'run' or 'compare').
            context: Workflow context for optimisation.
            logger: Logger for reporting.

        Returns:
            Tuple of (status, metadata, objects).

        Raises:
            ActionExecutionError: If execution fails.

        """
        try:
            request = _plot_request(parameters)
            if mode == "dry-run":
                return _dry_run_result(request, logger)
            metadata = run_plot(**request, log_fn=_log_fn(logger))
            return ("success", metadata, [])
        except ActionExecutionError:
            raise
        except Exception as e:
            raise ActionExecutionError(f"Plot failed: {e}") from e


def _require_csv_input(parameters: Dict[str, Any]) -> None:
    """Require a CSV input path.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If 'input' is missing or is not a CSV file.

    """
    input_path = parameters.get("input")
    if input_path is None:
        raise ValueError(
            "plot requires 'input' parameter with a .csv file path."
        )
    if not str(input_path).lower().endswith(".csv"):
        raise ValueError(
            f"plot input must be a CSV file (.csv). Got: {input_path}"
        )


def _require_image_output(parameters: Dict[str, Any]) -> None:
    """Require an image output path.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If 'output' is missing or is not an image file.

    """
    output_path = parameters.get("output")
    if output_path is None:
        raise ValueError(
            "plot requires 'output' parameter with an image file path."
        )
    if not str(output_path).lower().endswith(_IMAGE_EXTENSIONS):
        raise ValueError(
            "plot output must be an image file "
            f"({' or '.join(_IMAGE_EXTENSIONS)}). Got: {output_path}"
        )


def _require_column_parameters(parameters: Dict[str, Any]) -> None:
    """Require the subplot, group, x and y column names.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If a column parameter is missing.

    """
    for column_param in _COLUMN_PARAMETERS:
        if not parameters.get(column_param):
            raise ValueError(
                f"plot requires '{column_param}' parameter identifying "
                "a column in the input CSV."
            )


def _require_known_kind(parameters: Dict[str, Any]) -> None:
    """Require a supported plot type.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the plot type is not supported.

    """
    from causaliq_analysis.plot import SUPPORTED_KINDS

    plot_type = parameters.get("type", "line")
    if plot_type not in SUPPORTED_KINDS:
        raise ValueError(
            f"Unknown plot type '{plot_type}'. Supported types are: "
            f"{', '.join(sorted(SUPPORTED_KINDS))}"
        )


def _require_parseable_properties(parameters: Dict[str, Any]) -> None:
    """Require parseable plot property strings.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the properties cannot be parsed.

    """
    properties = parameters.get("properties")
    if properties is not None:
        _parse_properties(properties)


def _parse_properties(properties: Any) -> None:
    """Parse plot property strings, reporting invalid ones.

    Args:
        properties: Property strings to parse.

    Raises:
        ValueError: If the properties cannot be parsed.

    """
    try:
        from causaliq_analysis.plot import parse_properties

        parse_properties(properties)
    except ValueError as e:
        raise ValueError(f"Invalid plot properties: {e}")


def _plot_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the run_plot keyword arguments from action parameters.

    Args:
        parameters: Action parameter values.

    Returns:
        Keyword arguments for causaliq_analysis.plot.run_plot.

    Raises:
        AssertionError: If a required value is not a string.

    """
    request = {
        "input_csv": parameters.get("input"),
        "output": parameters.get("output"),
        "kind": parameters.get("type", "line"),
        "subplot": parameters.get("subplot"),
        "group": parameters.get("group"),
        "x": parameters.get("x"),
        "y": parameters.get("y"),
        "properties": parameters.get("properties"),
    }
    _require_string_request(request)
    return request


def _require_string_request(request: Dict[str, Any]) -> None:
    """Assert that every required request value is a string.

    Args:
        request: Keyword arguments for run_plot.

    Raises:
        AssertionError: If a required value is not a string.

    """
    assert isinstance(request["input_csv"], str)
    assert isinstance(request["output"], str)
    assert isinstance(request["kind"], str)
    assert isinstance(request["subplot"], str)
    assert isinstance(request["group"], str)
    assert isinstance(request["x"], str)
    assert isinstance(request["y"], str)


def _dry_run_result(
    request: Dict[str, Any],
    logger: Optional[Any],
) -> ActionResult:
    """Return the dry-run result for a plot request.

    Args:
        request: Keyword arguments for run_plot.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "skipped".

    """
    if logger and logger.is_terminal_logging:
        print(
            f"Would plot {request['kind']} from {request['input_csv']} "
            f"to {request['output']}"
        )
    return (
        "skipped",
        {
            "message": "Dry-run mode",
            "input": str(request["input_csv"]),
            "output": str(request["output"]),
            "type": request["kind"],
        },
        [],
    )


def _log_fn(logger: Optional[Any]) -> Optional[Any]:
    """Return the logging callback for a plot run.

    Args:
        logger: Logger for reporting.

    Returns:
        print when terminal logging is enabled, otherwise None.

    """
    if logger and logger.is_terminal_logging:
        return print
    return None
