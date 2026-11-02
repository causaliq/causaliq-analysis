"""The evaluate_graph action class and parameter validation."""

from typing import Any, Dict, Optional

from causaliq_analysis.validation import require_param
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionPattern,
    ActionResult,
)

from .constants import VALID_EVALUATE_METRICS
from .execution import _evaluate
from .request import (
    _dry_run_result,
    _evaluate_request,
    _parameter_block,
    _requested_metrics,
)

__all__ = ["EvaluateGraphAction"]


class EvaluateGraphAction(AnalysisAction):
    """Evaluate a learned graph against a ground-truth reference.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "evaluate_graph"
    pattern = ActionPattern.MAP

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate evaluate_graph parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        require_param(parameters, "reference", "evaluate_graph")
        require_param(parameters, "metric", "evaluate_graph")
        _require_valid_metrics(parameters)
        _require_cache_output(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Evaluate the matched entry graph against the reference graph.

        MAP pattern action: exactly one graph arrives via the
        '_aggregation_entries' parameter, and the reference may be a single
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


def _require_valid_metrics(parameters: Dict[str, Any]) -> None:
    """Validate the requested metric names.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If any requested metric is not supported.

    """
    metrics = _requested_metrics(parameters)
    if not metrics:
        return
    invalid = set(metrics) - VALID_EVALUATE_METRICS
    if invalid:
        raise ValueError(_invalid_metric_message(invalid))


def _invalid_metric_message(invalid: Any) -> str:
    """Build the error message for unsupported metrics.

    Args:
        invalid: Unsupported metric names.

    Returns:
        Error message listing the invalid and valid metric names.

    """
    valid_list = ", ".join(sorted(VALID_EVALUATE_METRICS))
    return (
        f"Invalid metric(s): {', '.join(sorted(invalid))}. "
        f"Valid metrics are: {valid_list}"
    )


def _require_cache_output(parameters: Dict[str, Any]) -> None:
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
