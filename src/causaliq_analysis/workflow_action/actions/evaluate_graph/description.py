"""Describing a PDG without a reference graph."""

from typing import Any, Dict, Optional

from causaliq_analysis.edge_analysis import pdg_edge_agreement
from causaliq_analysis.workflow_action.types import ActionResult

from .metric_values import _metrics_objects
from .request import _action_metadata

__all__ = ["_describe"]


def _describe(
    request: Dict[str, Any],
    parameters_block: Dict[str, Any],
    logger: Optional[Any],
    graph: Any,
) -> ActionResult:
    """Describe a graph's edge agreement without a reference.

    Args:
        request: Evaluation request without a reference graph.
        parameters_block: Effective parameters used by the action.
        logger: Logger for reporting.
        graph: Graph extracted from the matched entry.

    Returns:
        ActionResult tuple with status "success" and a metrics object.

    """
    values = pdg_edge_agreement(
        graph,
        request["present_threshold"],
        request["direction_threshold"],
    )
    selected = {
        name: values[name] for name in request["metrics"] if name in values
    }
    _log_description(logger, selected)
    return (
        "success",
        _action_metadata(parameters_block, "ok"),
        _metrics_objects(selected),
    )


def _log_description(
    logger: Optional[Any],
    values: Dict[str, list],
) -> None:
    """Report the number of values collected for each metric.

    Args:
        logger: Logger for reporting.
        values: Collected description metrics.

    """
    if logger and logger.is_terminal_logging:
        for name, items in values.items():
            print(f"Described {name}: {len(items)} values")
