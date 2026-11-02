"""Shared constants for the evaluate_graph action."""

__all__ = ["NO_GRAPH_ERROR", "VALID_EVALUATE_METRICS"]

VALID_EVALUATE_METRICS = frozenset(
    {
        "f1",
        "shd",
        "precision",
        "recall",
        "edge",
        "node_count",
        "equiv.f1",
        "equiv.shd",
        "equiv.edge",
    }
)
"""Metric names supported by the evaluate_graph action."""

NO_GRAPH_ERROR = "No graph present"
"""Error recorded when the input run produced no learnt graph."""
