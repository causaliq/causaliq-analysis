"""Structural and equivalence comparisons for evaluate_graph."""

from typing import Any, Dict, List, Optional

from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = [
    "_compute_equiv",
    "_compute_metrics",
    "_equiv_metrics",
    "_to_cpdag",
]


def _compute_metrics(graph: Any, reference: Any) -> Dict[str, Any]:
    """Compute structural metrics, comparing PDGs probabilistically.

    Args:
        graph: Graph evaluated from the entry.
        reference: Reference graph.

    Returns:
        Raw comparison metrics.

    Raises:
        ActionExecutionError: If the comparison fails.

    """
    from causaliq_core.graph import PDG

    from causaliq_analysis.metrics import pdag_compare, pdg_compare

    try:
        if isinstance(graph, PDG) or isinstance(reference, PDG):
            return pdg_compare(graph, reference)
        return pdag_compare(graph, reference)
    except Exception as e:
        raise ActionExecutionError(f"Metric computation failed: {e}") from e


def _equiv_metrics(
    graph: Any,
    reference: Any,
    requested: List[str],
    logger: Optional[Any],
) -> Dict[str, Any]:
    """Compute equivalence-class metrics when they are requested.

    Args:
        graph: Graph evaluated from the entry.
        reference: Reference graph.
        requested: Requested metric names.
        logger: Logger for reporting.

    Returns:
        Computed equivalence-class metrics, empty when unavailable.

    """
    if not any(name.startswith("equiv.") for name in requested):
        return {}
    try:
        return _compute_equiv(graph, reference, requested)
    except (ActionExecutionError, ValueError, TypeError):
        # PDAG not extendable to CPDAG (e.g. PC output with conflicting
        # orientations). Skip equiv metrics and continue with skeleton
        # metrics.
        _warn_equiv_unavailable(logger)
        return {}


def _warn_equiv_unavailable(logger: Optional[Any]) -> None:
    """Warn that equivalence-class metrics are unavailable.

    Args:
        logger: Logger for reporting.

    """
    if logger and logger.is_terminal_logging:
        print(
            "Warning: equivalence class not available, "
            "skipping equiv metrics"
        )


def _compute_equiv(
    graph: Any,
    reference: Any,
    requested: List[str],
) -> Dict[str, Any]:
    """Compute equivalence-class metrics for two graphs.

    Args:
        graph: Graph evaluated from the entry.
        reference: Reference graph.
        requested: Requested metric names.

    Returns:
        Mapping of equivalence-class metric names to values.

    """
    from causaliq_analysis.metrics import pdag_compare

    learned_cpdag = _to_cpdag(graph)
    reference_cpdag = _to_cpdag(reference)
    result = pdag_compare(learned_cpdag, reference_cpdag)
    equiv: Dict[str, Any] = {
        "equiv.f1": result["f1"],
        "equiv.shd": result["shd"],
    }
    _add_equiv_edge_metrics(equiv, result, requested)
    return equiv


def _add_equiv_edge_metrics(
    equiv: Dict[str, Any],
    result: Dict[str, Any],
    requested: List[str],
) -> None:
    """Add equivalence-class edge counts when requested.

    Args:
        equiv: Equivalence-class metrics being built.
        result: Raw comparison result.
        requested: Requested metric names.

    """
    from causaliq_analysis.metrics import EDGE_METRICS

    if "equiv.edge" not in requested:
        return
    for name in EDGE_METRICS:
        equiv[f"equiv.{name}"] = result[name]


def _to_cpdag(graph: Any) -> Any:
    """Convert a graph to its CPDAG (equivalence class).

    Args:
        graph: Graph to convert.

    Returns:
        The CPDAG for the graph.

    Raises:
        ActionExecutionError: If the graph cannot be converted.

    """
    from causaliq_core.graph import DAG, PDAG
    from causaliq_core.graph.convert import dag_to_pdag, pdag_to_cpdag

    if isinstance(graph, DAG):
        return dag_to_pdag(graph)
    if isinstance(graph, PDAG):
        cpdag = pdag_to_cpdag(graph)
        if cpdag is None:
            raise ActionExecutionError("PDAG is not extendable to a CPDAG")
        return cpdag
    raise ActionExecutionError(
        f"Cannot convert {type(graph).__name__} to CPDAG"
    )
