"""
Evaluate_graph workflow action.

Compares a learned graph against a ground-truth reference and returns
structural metrics. The action reads the matched entry of the input graph
cache (MAP pattern) and writes a single ``metrics`` object to the output
cache. Metric values live only in that object: the action metadata records
the effective parameters and the outcome status. The action is stateless, so
validation and execution delegate to module-level helpers and each step stays
within the module and method limits.

The action class lives in ``action`` and delegates to ``request``,
``execution``, ``comparison``, ``reference`` and ``metric_values``; shared
constants live in ``constants``. Public names are re-exported here so the
provider and existing imports keep working.
"""

from .action import EvaluateGraphAction
from .constants import NO_GRAPH_ERROR, VALID_EVALUATE_METRICS

# Test seam: the failure helpers are exercised directly by unit tests.
from .execution import _input_failure  # noqa: F401

__all__ = [
    "EvaluateGraphAction",
    "NO_GRAPH_ERROR",
    "VALID_EVALUATE_METRICS",
]
