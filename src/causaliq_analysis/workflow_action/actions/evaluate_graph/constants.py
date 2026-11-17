"""Shared constants for the evaluate_graph action."""

__all__ = [
    "DESCRIPTION_METRICS",
    "NO_GRAPH_ERROR",
    "VALID_DESCRIPTION_METRICS",
    "VALID_EVALUATE_METRICS",
]

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
"""Metric names supported by comparison mode."""

VALID_DESCRIPTION_METRICS = frozenset({"exist_agree", "dir_agree"})
"""Metric names supported by description mode (no reference graph)."""

DESCRIPTION_METRICS = ("exist_agree", "dir_agree")
"""Description metrics reported when no metric is requested."""

NO_GRAPH_ERROR = "No graph present"
"""Error recorded when the input run produced no learnt graph."""
