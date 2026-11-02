"""Executing one evaluate_graph comparison."""

from typing import Any, Dict, Optional, Tuple

from causaliq_analysis.workflow_action import helpers
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionResult,
)

from .comparison import _compute_metrics, _equiv_metrics
from .constants import NO_GRAPH_ERROR
from .metric_values import _metric_values, _metrics_objects
from .reference import _resolve_reference_graph
from .request import _action_metadata

__all__ = [
    "_entry_graph",
    "_evaluate",
    "_input_failure",
    "_log_evaluation",
]


def _evaluate(
    request: Dict[str, Any],
    parameters_block: Dict[str, Any],
    logger: Optional[Any],
) -> ActionResult:
    """Evaluate the entry graph against the reference graph.

    Args:
        request: Evaluation request.
        parameters_block: Effective parameters used by the action.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "success", or "error" when the
        input run failed (so the metrics cache records the failure).

    Raises:
        ActionExecutionError: If evaluation fails.

    """
    failure = _input_failure(request["entry"])
    if failure is not None:
        _log_input_failure(logger, failure)
        return (
            "error",
            _action_metadata(parameters_block, "input_failed", NO_GRAPH_ERROR),
            [],
        )
    graph, graph_type = _entry_graph(request)
    reference = _resolve_reference_graph(
        request["reference"], request["entry"]
    )
    metrics = _compute_metrics(graph, reference)
    equiv_metrics = _equiv_metrics(
        graph, reference, request["metrics"], logger
    )
    metadata = _action_metadata(parameters_block, "ok")
    _log_evaluation(logger, graph_type, metrics)
    return (
        "success",
        metadata,
        _metrics_objects(_metric_values(request, metrics, equiv_metrics)),
    )


def _input_failure(entry_data: Dict[str, Any]) -> Optional[str]:
    """Return the recorded error of a failed run, or None.

    A failed run holds provenance only: no object exists to evaluate, and
    its entry is recorded in the metrics cache as a failure instead.

    Args:
        entry_data: Aggregation entry data (entry plus its metadata).

    Returns:
        The recorded error message, or None when the run succeeded.

    """
    from causaliq_core.metadata import split_metadata

    metadata = entry_data.get("metadata") or {}
    parts = split_metadata(metadata)
    message = _result_error(parts.result)
    if message is not None:
        return message
    for blocks in parts.history.values():
        message = _history_error(blocks)
        if message is not None:
            return message
    return None


def _history_error(blocks: Any) -> Optional[str]:
    """Return the recorded error of one history block, or None."""
    if not isinstance(blocks, dict):
        return None
    return _result_error(blocks.get("result", {}))


def _result_error(result: Any) -> Optional[str]:
    """Return the error field of a result block, or None."""
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"])
    return None


def _entry_graph(request: Dict[str, Any]) -> Tuple[Any, str]:
    """Extract the graph to evaluate from the matched entry.

    Args:
        request: Evaluation request.

    Returns:
        Tuple of (parsed graph, object type).

    Raises:
        ActionExecutionError: If the entry holds no evaluable graph.

    """
    entry = request["entry"].get("entry")
    if entry is None:
        raise ActionExecutionError("No entry object in _aggregation_entries")
    return helpers._extract_graph_from_entry(entry, "cache entry")


def _log_input_failure(logger: Optional[Any], error: str) -> None:
    """Report an input failure when terminal logging is enabled.

    Args:
        logger: Logger for reporting.
        error: Recorded error of the input run.

    """
    if logger and logger.is_terminal_logging:
        print(f"Recording input failure: {error}")


def _log_evaluation(
    logger: Optional[Any],
    graph_type: str,
    metrics: Dict[str, Any],
) -> None:
    """Report the evaluation result when terminal logging is enabled.

    Args:
        logger: Logger for reporting.
        graph_type: Object type of the evaluated graph.
        metrics: Raw comparison metrics.

    """
    if logger and logger.is_terminal_logging:
        print(
            f"Evaluated {graph_type}: F1={metrics['f1']:.3f}, "
            f"SHD={metrics['shd']}"
        )
