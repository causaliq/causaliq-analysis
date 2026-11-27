"""Structural and equivalence comparisons for evaluate_graph."""

from typing import Any

from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = [
    "_compute_equiv",
    "_compute_metrics",
    "_equiv_metrics",
    "_to_cpdag",
]


def _compute_metrics(
    graph: Any,
    reference: Any,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Compute structural metrics, comparing PDGs probabilistically.

    When a threshold is given, both graphs are reduced to deterministic
    edge states before the comparison, so the low-level edge counts are
    integer counts of the thresholded graphs.

    Args:
        graph: Graph evaluated from the entry.
        reference: Reference graph.
        threshold: Minimum ``p_exist`` for an edge to be retained, or
            None to compare the probability vectors directly.

    Returns:
        Raw comparison metrics.

    Raises:
        ActionExecutionError: If the comparison fails.

    """
    from causaliq_core.graph import PDG

    from causaliq_analysis.edge_analysis import threshold_graph
    from causaliq_analysis.metrics import pdag_compare, pdg_compare

    try:
        if threshold is not None:
            graph = threshold_graph(graph, threshold)
            reference = threshold_graph(reference, threshold)
        if isinstance(graph, PDG) or isinstance(reference, PDG):
            return pdg_compare(graph, reference)
        return pdag_compare(graph, reference)
    except Exception as e:
        raise ActionExecutionError(f"Metric computation failed: {e}") from e


def _equiv_metrics(
    graph: Any,
    reference: Any,
    requested: list[str],
    logger: Any | None,
) -> dict[str, Any]:
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


def _warn_equiv_unavailable(logger: Any | None) -> None:
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
    requested: list[str],
) -> dict[str, Any]:
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
    equiv: dict[str, Any] = {
        "equiv.f1": result["f1"],
        "equiv.shd": result["shd"],
    }
    _add_equiv_edge_metrics(equiv, result, requested)
    return equiv


def _add_equiv_edge_metrics(
    equiv: dict[str, Any],
    result: dict[str, Any],
    requested: list[str],
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
