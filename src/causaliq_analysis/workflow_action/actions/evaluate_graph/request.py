"""Building evaluate_graph requests and action metadata."""

from typing import Any, Dict, List, Optional

from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionResult,
)

from .constants import DESCRIPTION_METRICS

__all__ = [
    "_action_metadata",
    "_dry_run_result",
    "_evaluate_request",
    "_parameter_block",
    "_requested_metrics",
    "_resolved_output",
]


def _requested_metrics(parameters: Dict[str, Any]) -> Optional[List[str]]:
    """Return the requested metrics as a list.

    Args:
        parameters: Action parameter values.

    Returns:
        List of metric names, or None when no metric is provided.

    """
    metric = parameters.get("metric")
    return [metric] if isinstance(metric, str) else metric


def _evaluate_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the evaluation request from action parameters.

    A missing reference selects description mode: the matched graph is
    described rather than compared. Comparison mode requires a metric.

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding the matched entry, reference path, metrics and
        thresholds.

    Raises:
        ActionExecutionError: If a required parameter is missing or more
            than one entry matches the current matrix combination.

    """
    entries = parameters.get("_aggregation_entries")
    if entries is None:
        raise ActionExecutionError(
            "evaluate_graph requires '_aggregation_entries' parameter "
            "(MAP pattern action)"
        )
    if not entries:
        raise ActionExecutionError(
            "evaluate_graph matched no cache entries for this job. "
            f"Check that the input cache '{parameters.get('input')}' "
            "exists and contains entries matching the matrix values."
        )
    if len(entries) != 1:
        raise ActionExecutionError(
            "evaluate_graph expects exactly one matching entry per job, "
            f"found {len(entries)}. Add a matrix key to distinguish them."
        )

    reference_path = parameters.get("reference")
    metrics = _requested_metrics(parameters)
    if reference_path and metrics is None:
        raise ActionExecutionError(
            "evaluate_graph requires 'metric' parameter when a "
            "'reference' is given"
        )
    if not reference_path and metrics is None:
        metrics = list(DESCRIPTION_METRICS)
    assert metrics is not None
    return {
        "entry": entries[0],
        "reference": reference_path,
        "context": parameters.get("context"),
        "metrics": metrics,
        "threshold": parameters.get("threshold"),
        "present_threshold": parameters.get("present_threshold", 0.0),
        "direction_threshold": parameters.get("direction_threshold", 0.0),
    }


def _parameter_block(
    parameters: Dict[str, Any],
    request: Dict[str, Any],
    context: Optional[Any],
) -> Dict[str, Any]:
    """Build the effective-parameters block for the action metadata.

    Every user-facing parameter is recorded, including those the workflow
    does not supply. The internal '_aggregation_entries' parameter is
    excluded because it carries live cache objects rather than a value.

    Args:
        parameters: Action parameter values.
        request: Evaluation request.
        context: Workflow context holding the open output cache, if any.

    Returns:
        Parameters block with every user-facing parameter present.

    """
    return {
        "input": parameters.get("input"),
        "reference": request["reference"],
        "context": request["context"],
        "metric": request["metrics"],
        "threshold": request["threshold"],
        "present_threshold": request["present_threshold"],
        "direction_threshold": request["direction_threshold"],
        "output": _resolved_output(parameters, context),
        "filter": parameters.get("filter"),
    }


def _resolved_output(
    parameters: Dict[str, Any],
    context: Optional[Any],
) -> Optional[str]:
    """Return the effective output path for the action metadata.

    The workflow executor removes 'output' before invoking an action that
    writes to a cache, so the open cache path is used instead.

    Args:
        parameters: Action parameter values.
        context: Workflow context holding the open output cache, if any.

    Returns:
        Output path, or None when the action writes no cache.

    """
    output = parameters.get("output")
    if output is not None:
        return str(output)
    cache = getattr(context, "cache", None)
    db_path = getattr(cache, "db_path", None)
    return None if db_path is None else str(db_path)


def _action_metadata(
    parameters_block: Dict[str, Any],
    status: str,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Build action metadata with explicit parameter and result blocks.

    Args:
        parameters_block: Effective parameters used by the action.
        status: Status recorded in the result block.
        error: Failure explanation, omitted when the run produced a result.

    Returns:
        Action metadata holding the parameters and result blocks.

    """
    result: Dict[str, Any] = {"status": status}
    if error is not None:
        result["error"] = error
    return {"parameters": parameters_block, "result": result}


def _dry_run_result(
    request: Dict[str, Any],
    parameters_block: Dict[str, Any],
    logger: Optional[Any],
) -> ActionResult:
    """Return the dry-run result for an evaluation.

    Args:
        request: Evaluation request.
        parameters_block: Effective parameters used by the action.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "skipped".

    """
    matrix_values = request["entry"].get("matrix_values", {})
    if logger and logger.is_terminal_logging:
        if request["reference"]:
            print(
                f"Would evaluate graph {matrix_values} "
                f"vs reference: {request['reference']}"
            )
        else:
            print(f"Would describe graph {matrix_values}")
    return ("skipped", _action_metadata(parameters_block, "skipped"), [])
