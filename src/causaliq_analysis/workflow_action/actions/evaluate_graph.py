"""
Evaluate_graph workflow action.

Compares a learned graph against a ground-truth reference and returns
structural metrics as action metadata. The action is stateless, so
validation and execution delegate to module-level helpers and each step
stays within the module and method limits.
"""

from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis import graph_io
from causaliq_analysis.validation import require_param
from causaliq_analysis.workflow_action import helpers
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionPattern,
    ActionResult,
)

__all__ = ["EvaluateGraphAction"]

VALID_EVALUATE_METRICS = frozenset(
    {
        "f1",
        "shd",
        "precision",
        "recall",
        "edge",
        "equiv.f1",
        "equiv.shd",
        "equiv.edge",
    }
)
"""Metric names supported by the evaluate_graph action."""


class EvaluateGraphAction(AnalysisAction):
    """Evaluate a learned graph against a ground-truth reference.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "evaluate_graph"
    pattern = ActionPattern.UPDATE

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate evaluate_graph parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        require_param(parameters, "reference", "evaluate_graph")
        require_param(parameters, "metric", "evaluate_graph")
        _require_valid_metrics(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Evaluate the entry graph against the reference graph.

        UPDATE pattern action: the graph to evaluate arrives via the
        '_update_entry' parameter, and the reference may be a single
        ground-truth graph file or a workflow cache (.db) whose entries
        share the input cache's key structure.

        Args:
            parameters: Action parameter values.
            mode: Execution mode ('dry-run', 'run' or 'compare').
            context: Workflow context for optimisation.
            logger: Logger for reporting.

        Returns:
            Tuple of (status, metadata, objects).

        Raises:
            ActionExecutionError: If execution fails.

        """
        request = _evaluate_request(parameters)
        if mode == "dry-run":
            return _dry_run_result(request, logger)
        return _evaluate(request, logger)


def _require_valid_metrics(parameters: Dict[str, Any]) -> None:
    """Validate the requested metric names.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If any requested metric is not supported.

    """
    metrics = _requested_metrics(parameters)
    if not metrics:
        return
    invalid = set(metrics) - VALID_EVALUATE_METRICS
    if invalid:
        raise ValueError(_invalid_metric_message(invalid))


def _invalid_metric_message(invalid: Any) -> str:
    """Build the error message for unsupported metrics.

    Args:
        invalid: Unsupported metric names.

    Returns:
        Error message listing the invalid and valid metric names.

    """
    valid_list = ", ".join(sorted(VALID_EVALUATE_METRICS))
    return (
        f"Invalid metric(s): {', '.join(sorted(invalid))}. "
        f"Valid metrics are: {valid_list}"
    )


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

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding the update entry, reference path and metrics.

    Raises:
        ActionExecutionError: If a required parameter is missing.

    """
    update_entry = parameters.get("_update_entry")
    if not update_entry:
        raise ActionExecutionError(
            "evaluate_graph requires _update_entry parameter "
            "(UPDATE pattern action)"
        )

    reference_path = parameters.get("reference")
    if not reference_path:  # pragma: no cover
        raise ActionExecutionError(
            "evaluate_graph requires 'reference' parameter"
        )

    metrics = _requested_metrics(parameters)
    # Type assertion: metric is required, so this is always a list
    assert metrics is not None, "metric is required"
    return {
        "update_entry": update_entry,
        "reference": reference_path,
        "metrics": metrics,
    }


def _dry_run_result(
    request: Dict[str, Any],
    logger: Optional[Any],
) -> ActionResult:
    """Return the dry-run result for an evaluation.

    Args:
        request: Evaluation request.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "skipped".

    """
    matrix_values = request["update_entry"].get("matrix_values", {})
    if logger and logger.is_terminal_logging:
        print(
            f"Would evaluate graph {matrix_values} "
            f"vs reference: {request['reference']}"
        )
    return ("skipped", {"reference": request["reference"]}, [])


def _evaluate(
    request: Dict[str, Any],
    logger: Optional[Any],
) -> ActionResult:
    """Evaluate the entry graph against the reference graph.

    Args:
        request: Evaluation request.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "success".

    Raises:
        ActionExecutionError: If evaluation fails.

    """
    graph, graph_type = _entry_graph(request)
    reference = _resolve_reference_graph(
        request["reference"], request["update_entry"]
    )
    metrics = _compute_metrics(graph, reference)
    equiv_metrics = _equiv_metrics(
        graph, reference, request["metrics"], logger
    )
    metadata = _metric_metadata(request, metrics, equiv_metrics, graph_type)
    _log_evaluation(logger, graph_type, metrics)
    return ("success", metadata, [])


def _entry_graph(request: Dict[str, Any]) -> Tuple[Any, str]:
    """Extract the graph to evaluate from the update entry.

    Args:
        request: Evaluation request.

    Returns:
        Tuple of (parsed graph, object type).

    Raises:
        ActionExecutionError: If the entry holds no evaluable graph.

    """
    entry = request["update_entry"].get("entry")
    if entry is None:
        raise ActionExecutionError("No entry object in _update_entry")
    return helpers._extract_graph_from_entry(entry, "cache entry")


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


def _resolve_reference_graph(
    reference_path: str,
    update_entry: Dict[str, Any],
) -> Any:
    """Resolve the reference graph from a file or workflow cache.

    When reference_path points to a workflow cache (.db), the reference
    graph is resolved from the reference cache entry whose matrix
    variable values match the current input entry. The reference cache
    must use the same key structure (matrix variable names) as the input
    cache.

    Args:
        reference_path: Path to a reference graph file or a workflow
            cache (.db) containing reference graphs.
        update_entry: UPDATE action entry data containing the
            'matrix_values' for the current input entry.

    Returns:
        The parsed reference graph.

    Raises:
        ActionExecutionError: If the reference cannot be resolved.

    """
    if not str(reference_path).lower().endswith(".db"):
        return _reference_from_file(reference_path)
    return _reference_from_cache(reference_path, update_entry)


def _reference_from_file(reference_path: str) -> Any:
    """Read a ground-truth reference graph file.

    Args:
        reference_path: Path to the reference graph file.

    Returns:
        The parsed reference graph.

    Raises:
        ActionExecutionError: If the file cannot be read.

    """
    try:
        return graph_io.read_graph_or_pdg_file(reference_path)
    except FileNotFoundError:
        raise ActionExecutionError(
            f"Reference graph not found: {reference_path}"
        )
    except Exception as e:
        raise ActionExecutionError(
            f"Failed to read reference graph: {e}"
        ) from e


def _reference_from_cache(
    reference_path: str,
    update_entry: Dict[str, Any],
) -> Any:
    """Resolve a reference graph from a reference workflow cache.

    Args:
        reference_path: Path to the reference workflow cache (.db).
        update_entry: UPDATE action entry data.

    Returns:
        The parsed reference graph.

    Raises:
        ActionExecutionError: If the reference cannot be resolved.

    """
    from causaliq_workflow.cache import WorkflowCache

    matrix_values = update_entry.get("matrix_values", {})
    try:
        with WorkflowCache(reference_path) as ref_cache:
            return _reference_cache_entry(
                ref_cache, matrix_values, reference_path
            )
    except ActionExecutionError:
        raise
    except Exception as e:
        raise ActionExecutionError(
            f"Failed to read reference cache: {e}"
        ) from e


def _reference_cache_entry(
    ref_cache: Any,
    matrix_values: Dict[str, Any],
    reference_path: str,
) -> Any:
    """Resolve the reference entry matching the matrix values.

    Args:
        ref_cache: Open reference workflow cache.
        matrix_values: Matrix variable values of the current entry.
        reference_path: Path to the reference cache, for messages.

    Returns:
        The parsed reference graph.

    Raises:
        ActionExecutionError: If no matching reference entry exists.

    """
    ref_entries = ref_cache.list_entries()
    if not ref_entries:
        raise ActionExecutionError(
            f"Reference cache is empty: {reference_path}"
        )
    _require_matching_keys(ref_entries, matrix_values)
    ref_entry = ref_cache.get(matrix_values)
    if ref_entry is None:
        raise ActionExecutionError(
            "No entry in reference cache for matrix values "
            f"{dict(matrix_values)}"
        )
    source_label = f"reference cache entry {dict(matrix_values)}"
    graph, _ = helpers._extract_graph_from_entry(ref_entry, source_label)
    return graph


def _require_matching_keys(
    ref_entries: List[Dict[str, Any]],
    matrix_values: Dict[str, Any],
) -> None:
    """Require reference cache entries to share the input key structure.

    Args:
        ref_entries: Entries listed from the reference cache.
        matrix_values: Matrix variable values of the current entry.

    Raises:
        ActionExecutionError: If the key structures differ.

    """
    input_keys = set(matrix_values.keys())
    for ref_info in ref_entries:
        ref_keys = set(ref_info.get("matrix_values", {}).keys())
        if ref_keys != input_keys:
            raise ActionExecutionError(
                "Reference cache key structure does not match "
                "input cache. Input keys: "
                f"{sorted(input_keys)}, reference keys: "
                f"{sorted(ref_keys)}"
            )


def _metric_metadata(
    request: Dict[str, Any],
    metrics: Dict[str, Any],
    equiv_metrics: Dict[str, Any],
    graph_type: str,
) -> Dict[str, Any]:
    """Build the result metadata for an evaluation.

    Args:
        request: Evaluation request.
        metrics: Raw comparison metrics.
        equiv_metrics: Computed equivalence-class metrics.
        graph_type: Object type of the evaluated graph.

    Returns:
        Action metadata holding the requested metrics.

    """
    wanted = _wanted_metrics(request["metrics"])
    all_metrics = _all_metrics(metrics, equiv_metrics, wanted)
    filtered = {k: v for k, v in all_metrics.items() if k in wanted}
    return {
        **filtered,
        "reference": request["reference"],
        "evaluated_graph": graph_type,
    }


def _all_metrics(
    metrics: Dict[str, Any],
    equiv_metrics: Dict[str, Any],
    wanted: List[str],
) -> Dict[str, Any]:
    """Build the complete metric mapping for an evaluation.

    Args:
        metrics: Raw comparison metrics.
        equiv_metrics: Computed equivalence-class metrics.
        wanted: Requested metric names after group expansion.

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
