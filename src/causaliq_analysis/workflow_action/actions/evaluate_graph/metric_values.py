"""Metric values and metrics objects for evaluate_graph."""

import json
from typing import Any, Dict, List

__all__ = [
    "_metric_values",
    "_metrics_objects",
]


def _metric_values(
    request: Dict[str, Any],
    metrics: Dict[str, Any],
    equiv_metrics: Dict[str, Any],
    graph: Any,
) -> Dict[str, Any]:
    """Return the requested metric values for the metrics object.

    Args:
        request: Evaluation request.
        metrics: Raw comparison metrics.
        equiv_metrics: Computed equivalence-class metrics.
        graph: Evaluated graph, used for the node count.

    Returns:
        Mapping of requested metric names to values.

    """
    wanted = _wanted_metrics(request["metrics"])
    all_metrics = _all_metrics(metrics, equiv_metrics, wanted, graph)
    return {k: v for k, v in all_metrics.items() if k in wanted}


def _all_metrics(
    metrics: Dict[str, Any],
    equiv_metrics: Dict[str, Any],
    wanted: List[str],
    graph: Any,
) -> Dict[str, Any]:
    """Build the complete metric mapping for an evaluation.

    Args:
        metrics: Raw comparison metrics.
        equiv_metrics: Computed equivalence-class metrics.
        wanted: Requested metric names after group expansion.
        graph: Evaluated graph, used for the node count.

    Returns:
        Mapping of every standard and equivalence metric name.

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
    if "edge" in wanted:
        _add_edge_counts(all_metrics, metrics)
    return all_metrics


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
