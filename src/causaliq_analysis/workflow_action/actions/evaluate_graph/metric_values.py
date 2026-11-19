"""Metric values and metrics objects for evaluate_graph."""

import json
from typing import Any, Dict, List

from causaliq_analysis.workflow_action.types import ActionExecutionError

from .context import _context_values

__all__ = [
    "_metric_values",
    "_metrics_objects",
]


def _metric_values(
    request: Dict[str, Any],
    metrics: Dict[str, Any],
    equiv_metrics: Dict[str, Any],
    graph: Any,
    reference: Any,
) -> Dict[str, Any]:
    """Return the requested metric values for the metrics object.

    Args:
        request: Evaluation request.
        metrics: Raw comparison metrics.
        equiv_metrics: Computed equivalence-class metrics.
        graph: Evaluated graph, used for the node count.
        reference: Reference graph, used for the reference arc count.

    Returns:
        Mapping of requested metric names to values.

    """
    wanted = _wanted_metrics(request["metrics"])
    all_metrics = _all_metrics(
        metrics, equiv_metrics, wanted, graph, reference, request
    )
    return {k: v for k, v in all_metrics.items() if k in wanted}


def _all_metrics(
    metrics: Dict[str, Any],
    equiv_metrics: Dict[str, Any],
    wanted: List[str],
    graph: Any,
    reference: Any,
    request: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the complete metric mapping for an evaluation.

    Args:
        metrics: Raw comparison metrics.
        equiv_metrics: Computed equivalence-class metrics.
        wanted: Requested metric names after group expansion.
        graph: Evaluated graph, used for the node count.
        reference: Reference graph, used for the arc count.
        request: Evaluation request, used for context values.

    Returns:
        Mapping of every standard, reference and equivalence metric name.

    """
    all_metrics: Dict[str, Any] = {
        "precision": metrics["p"],
        "recall": metrics["r"],
        "f1": metrics["f1"],
        "shd": metrics["shd"],
        **equiv_metrics,
    }
    if "node_count" in wanted:
        all_metrics["node_count"] = len(graph.nodes)
    if "reference_arc_count" in wanted:
        all_metrics["reference_arc_count"] = _reference_arc_count(reference)
    _add_context_metrics(all_metrics, wanted, request)
    if "edge" in wanted:
        _add_edge_counts(all_metrics, metrics)
    return all_metrics


def _add_context_metrics(
    all_metrics: Dict[str, Any],
    wanted: List[str],
    request: Dict[str, Any],
) -> None:
    """Add context provenance metrics when they are requested.

    Args:
        all_metrics: Metric mapping being built.
        wanted: Requested metric names after group expansion.
        request: Evaluation request holding the context path.

    Raises:
        ActionExecutionError: If a context metric is requested without a
            context path.
    """
    names = {"domain", "source_repository"} & set(wanted)
    if not names:
        return
    if not request.get("context"):
        raise ActionExecutionError(
            "evaluate_graph context metrics require a 'context' file: "
            + ", ".join(sorted(names))
        )
    values = _context_values(request.get("context"))
    for name in names:
        all_metrics[name] = values[name]


def _reference_arc_count(reference: Any) -> int:
    """Return the number of directed arcs in a reference graph.

    Args:
        reference: Reference graph.

    Returns:
        Number of directed arcs.
    """
    edges = getattr(reference, "edges", None)
    if edges is None:
        return 0
    if isinstance(edges, dict):
        try:
            from causaliq_core.graph import EdgeType

            return sum(
                1
                for edge_type in edges.values()
                if edge_type == EdgeType.DIRECTED
            )
        except Exception:  # pragma: no cover - defensive fallback
            return len(edges)
    return len(edges)


def _add_edge_counts(
    all_metrics: Dict[str, Any],
    metrics: Dict[str, Any],
) -> None:
    """Add the low-level edge counts to a metric mapping.

    Args:
        all_metrics: Metric mapping being built.
        metrics: Raw comparison metrics.

    """
    from causaliq_analysis.metrics import EDGE_METRICS

    for name in EDGE_METRICS:
        all_metrics[name] = metrics[name]


def _wanted_metrics(requested: List[str]) -> List[str]:
    """Expand metric group requests into individual metric names.

    'edge' and 'equiv.edge' are group requests which expand to the
    individual low-level comparison count metric names.

    Args:
        requested: Requested metric names.

    Returns:
        Requested metric names with groups expanded.

    """
    from causaliq_analysis.metrics import EDGE_METRICS

    wanted = set(requested)
    if "edge" in wanted:
        wanted.update(EDGE_METRICS)
    if "equiv.edge" in wanted:
        wanted.update(f"equiv.{name}" for name in EDGE_METRICS)
    return list(wanted)


def _metrics_objects(values: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build the metrics object written to the output cache.

    Args:
        values: Requested metric values.

    Returns:
        Single-element list holding the metrics object.

    """
    return [
        {
            "type": "metrics",
            "format": "json",
            "action": "evaluate_graph",
            "content": json.dumps(values),
        }
    ]
