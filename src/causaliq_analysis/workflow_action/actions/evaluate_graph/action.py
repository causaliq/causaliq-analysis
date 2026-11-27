"""The evaluate_graph action class and parameter validation."""

from typing import Any

from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionPattern,
    ActionResult,
)

from .constants import (
    DESCRIPTION_METRICS,
    VALID_DESCRIPTION_METRICS,
    VALID_EVALUATE_METRICS,
)
from .execution import _evaluate
from .request import (
    _dry_run_result,
    _evaluate_request,
    _parameter_block,
    _requested_metrics,
)

__all__ = ["EvaluateGraphAction"]

# Probability parameters and their default values
_PROBABILITY_PARAMETERS = (
    "threshold",
    "present_threshold",
    "direction_threshold",
)

# Description mode reports these metrics when none is requested
_DESCRIPTION_DEFAULTS = tuple(DESCRIPTION_METRICS)


class EvaluateGraphAction(AnalysisAction):
    """Evaluate or describe a graph, with a reference graph optional.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "evaluate_graph"
    pattern = ActionPattern.MAP

    def validate(self, parameters: dict[str, Any]) -> None:
        """Validate evaluate_graph parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        _require_valid_metrics(parameters)
        _require_probabilities(parameters)
        _require_cache_output(parameters)
        _require_context(parameters)

    def run(
        self,
        parameters: dict[str, Any],
        mode: str,
        context: Any | None = None,
        logger: Any | None = None,
    ) -> ActionResult:
        """Evaluate the matched entry graph against a reference.

        MAP pattern action: exactly one graph arrives via the
        '_aggregation_entries' parameter. A missing reference selects
        description mode; otherwise the reference may be a single
        ground-truth graph file or a workflow cache (.db) whose entries
        share the input cache's key structure.

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
        request = _evaluate_request(parameters)
        block = _parameter_block(parameters, request, context)
        if mode == "dry-run":
            return _dry_run_result(request, block, logger)
        return _evaluate(request, block, logger)


def _require_valid_metrics(parameters: dict[str, Any]) -> None:
    """Validate the requested metric names for the active mode.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If a requested metric is not supported, or a required
            metric is missing in comparison mode.

    """
    metrics = _requested_metrics(parameters)
    if not metrics:
        if parameters.get("reference"):
            raise ValueError(
                "'evaluate_graph' requires 'metric' parameter when a "
                "'reference' is given"
            )
        metrics = list(_DESCRIPTION_DEFAULTS)
    valid = (
        VALID_EVALUATE_METRICS
        if parameters.get("reference")
        else VALID_DESCRIPTION_METRICS
    )
    invalid = set(metrics) - valid
    if invalid:
        raise ValueError(_invalid_metric_message(invalid, valid))


def _invalid_metric_message(invalid: Any, valid: Any) -> str:
    """Build the error message for unsupported metrics.

    Args:
        invalid: Unsupported metric names.
        valid: Supported metric names.

    Returns:
        Error message listing the invalid and valid metric names.

    """
    valid_list = ", ".join(sorted(valid))
    return (
        f"Invalid metric(s): {', '.join(sorted(invalid))}. "
        f"Valid metrics are: {valid_list}"
    )


def _require_probabilities(parameters: dict[str, Any]) -> None:
    """Validate the optional probability parameters.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If a probability is outside the [0, 1] range.

    """
    for name in _PROBABILITY_PARAMETERS:
        value = parameters.get(name)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"'{name}' must be a number between 0 and 1")
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"'{name}' must be between 0.0 and 1.0, got {value}"
            )


def _require_cache_output(parameters: dict[str, Any]) -> None:
    """Validate the output path when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the output path is not a workflow cache.

    """
    output_path = parameters.get("output")
    if output_path is None:
        return
    if not str(output_path).lower().endswith(".db"):
        raise ValueError(
            "evaluate_graph output must be a workflow cache (.db). "
            f"Got: {output_path}"
        )


def _require_context(parameters: dict[str, Any]) -> None:
    """Validate the optional context path.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the context path is not a string.
    """
    context = parameters.get("context")
    if context is None or isinstance(context, str):
        return
    raise ValueError(
        f"'context' must be a path string, got {type(context).__name__}"
    )
