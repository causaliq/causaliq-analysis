"""
Merge_graphs workflow action.

Merges multiple graphs into a probabilistic DAG (PDG). The action is
stateless, so validation and execution delegate to module-level helpers and
each step stays within the module and method limits.
"""

from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.validation import validate_filter_expression
from causaliq_analysis.workflow_action import helpers
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionPattern,
    ActionResult,
)

__all__ = ["MergeGraphsAction"]

# Supported merge strategies
_VALID_STRATEGIES = ("average", "noisy_or", "max")


class MergeGraphsAction(AnalysisAction):
    """Merge multiple graphs into a probabilistic DAG.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "merge_graphs"
    pattern = ActionPattern.AGGREGATE

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate merge_graphs parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        _require_entries_or_input(parameters)
        _require_valid_filter(parameters)
        _require_valid_weights(parameters)
        _require_cache_output(parameters)
        _require_valid_strategy(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Execute graph merging to produce a PDG.

        Aggregation mode merges graphs from pre-scanned cache entries passed
        via '_aggregation_entries'; direct mode merges graphs read from the
        'input' file paths (.graphml or .db files).

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
        try:
            request = _merge_request(parameters)
            _require_input(request)
            return _execute_merge(request, mode, logger)
        except ActionExecutionError:
            raise
        except ValueError as e:
            raise ActionExecutionError(f"Graph merge failed: {e}") from e
        except Exception as e:
            raise ActionExecutionError(f"Graph merge failed: {e}") from e


def _execute_merge(
    request: Dict[str, Any],
    mode: str,
    logger: Optional[Any],
) -> ActionResult:
    """Execute a merge for a validated request.

    Args:
        request: Merge request.
        mode: Execution mode ('dry-run', 'run' or 'compare').
        logger: Logger for reporting.

    Returns:
        Tuple of (status, metadata, objects).

    Raises:
        ActionExecutionError: If execution fails.

    """
    if mode == "dry-run":
        return _dry_run_result(request, logger)
    log_fn = _log_fn(logger)
    graphs, graph_metadata, source_info = _load_graphs(request, log_fn)
    _require_graphs(graphs)
    final_weights, weights_applied = _final_weights(
        request, graph_metadata, log_fn
    )
    content = _merge_pdg(request, graphs, final_weights, log_fn)
    metadata = _success_metadata(
        request, graphs, final_weights, weights_applied, source_info
    )
    return ("success", metadata, _pdg_objects(content))


def _require_entries_or_input(parameters: Dict[str, Any]) -> None:
    """Require aggregation entries or input file paths.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If neither input form is provided.

    """
    has_aggregation = "_aggregation_entries" in parameters
    has_input = parameters.get("input") is not None
    if not has_aggregation and not has_input:
        raise ValueError(
            "'merge_graphs' requires either '_aggregation_entries' "
            "(aggregation mode) or 'input' parameter"
        )


def _require_valid_filter(parameters: Dict[str, Any]) -> None:
    """Validate filter expression syntax when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the filter expression cannot be parsed.

    """
    validate_filter_expression(parameters.get("filter"))


def _require_valid_weights(parameters: Dict[str, Any]) -> None:
    """Validate a weight specification when provided as a dict.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the weight specification is invalid.

    """
    weights = parameters.get("weights")
    if weights is not None and isinstance(weights, dict):
        _validate_weight_spec(weights)


def _validate_weight_spec(weights: Dict[str, Any]) -> None:
    """Validate a weight specification, reporting invalid ones.

    Args:
        weights: Weight specification to validate.

    Raises:
        ValueError: If the weight specification is invalid.

    """
    from causaliq_core.utils import WeightSpecError, validate_weight_spec

    try:
        validate_weight_spec(weights)
    except WeightSpecError as e:
        raise ValueError(f"Invalid weight specification: {e}")


def _require_cache_output(parameters: Dict[str, Any]) -> None:
    """Validate the output path when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the output path is not a workflow cache.

    """
    output_path = parameters.get("output")
    if output_path is not None:
        _require_db_path(output_path)


def _require_db_path(output_path: Any) -> None:
    """Require a workflow cache (.db) output path.

    Args:
        output_path: Output path to check.

    Raises:
        ValueError: If the path is not a workflow cache.

    """
    if not str(output_path).lower().endswith(".db"):
        raise ValueError(
            "merge_graphs output must be a workflow cache (.db). "
            f"Got: {output_path}"
        )


def _require_valid_strategy(parameters: Dict[str, Any]) -> None:
    """Validate the merge strategy when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the strategy is not supported.

    """
    strategy = parameters.get("strategy")
    if strategy is not None and strategy not in _VALID_STRATEGIES:
        raise ValueError(
            f"strategy must be 'average', 'noisy_or', "
            f"or 'max', got '{strategy}'"
        )


def _merge_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the merge request from action parameters.

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding the aggregation entries, input paths and merge
        settings.

    """
    input_raw = parameters.get("input", []) or []
    input_files = (
        [input_raw] if isinstance(input_raw, str) else list(input_raw)
    )
    object_type = parameters.get("object_type")
    request: Dict[str, Any] = {
        "aggregation_entries": parameters.get("_aggregation_entries"),
        "input_files": input_files,
        "weights": parameters.get("weights"),
        "filter": parameters.get("filter"),
        "object_type": object_type,
        "cpdag": object_type == "cpdag",
        "obj_filter": "dag" if object_type == "cpdag" else object_type,
        "strategy": parameters.get("strategy", "average"),
        "is_aggregation": parameters.get("_aggregation_entries") is not None,
    }
    return request


def _require_input(request: Dict[str, Any]) -> None:
    """Require aggregation entries or input file paths.

    Args:
        request: Merge request.

    Raises:
        ActionExecutionError: If neither input form is provided.

    """
    if not request["is_aggregation"] and not request["input_files"]:
        raise ActionExecutionError(  # pragma: no cover
            "merge_graphs requires 'input' (list of .graphml or "
            ".db files). For aggregation mode, use AGGREGATE action "
            "pattern with .db input."
        )


def _dry_run_result(
    request: Dict[str, Any],
    logger: Optional[Any],
) -> ActionResult:
    """Return the dry-run result for a merge.

    Args:
        request: Merge request.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "skipped".

    """
    if logger and logger.is_terminal_logging:
        _print_dry_run(request)
    metadata: Dict[str, Any] = {
        "message": "Dry-run mode",
        "aggregation_mode": request["is_aggregation"],
        "num_inputs": _num_inputs(request),
    }
    return ("skipped", metadata, [])


def _num_inputs(request: Dict[str, Any]) -> int:
    """Return the number of inputs a merge request carries.

    Args:
        request: Merge request.

    Returns:
        Number of aggregation entries or input files.

    """
    if request["is_aggregation"]:
        return len(request["aggregation_entries"] or [])
    return len(request["input_files"])


def _print_dry_run(request: Dict[str, Any]) -> None:
    """Print the dry-run message for the active merge mode.

    Args:
        request: Merge request.

    """
    if request["is_aggregation"]:
        entry_count = _num_inputs(request)
        print(f"Would merge graphs from {entry_count} aggregated entries")
    else:
        print(f"Would merge from {len(request['input_files'])} input files")


def _log_fn(logger: Optional[Any]) -> Optional[Any]:
    """Build a logging callback from a workflow logger.

    Args:
        logger: Logger for reporting, if any.

    Returns:
        Callback accepting a message, or None without a logger.

    """
    if logger is None:
        return None
    return getattr(logger, "log", print)


def _load_graphs(
    request: Dict[str, Any],
    log_fn: Optional[Any],
) -> Tuple[List[Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Read the graphs to merge from entries or input files.

    Args:
        request: Merge request.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (graphs, per-graph metadata, source information).

    Raises:
        ActionExecutionError: If no graphs can be read.

    """
    if request["is_aggregation"]:
        return _graphs_from_entries(request, log_fn)
    return _graphs_from_files(request, log_fn)


def _graphs_from_entries(
    request: Dict[str, Any],
    log_fn: Optional[Any],
) -> Tuple[List[Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Read the graphs to merge from pre-scanned cache entries.

    Args:
        request: Merge request.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (graphs, per-graph metadata, source information).

    Raises:
        ActionExecutionError: If no cache entries matched.

    """
    entries = request["aggregation_entries"]
    if not entries:
        raise ActionExecutionError(
            "No cache entries matched the current matrix values. "
            "Check that matrix values in workflow match those in "
            "the input cache (values are case-sensitive)."
        )
    return helpers._extract_graphs_from_entries(
        entries,
        log_fn,
        object_type=request["obj_filter"],
    )


def _graphs_from_files(
    request: Dict[str, Any],
    log_fn: Optional[Any],
) -> Tuple[List[Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Read the graphs to merge from input file paths.

    Args:
        request: Merge request.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (graphs, per-graph metadata, source information).

    Raises:
        ActionExecutionError: If an input file cannot be read.

    """
    graphs: List[Any] = []
    cache_entries_read = 0
    for input_path in request["input_files"]:
        if str(input_path).lower().endswith(".db"):
            cache_graphs, entries = _read_cache_graphs(
                request, input_path, log_fn
            )
            graphs.extend(cache_graphs)
            cache_entries_read += entries
        else:
            graphs.append(_read_graphml_file(input_path, log_fn))
    source_info: Dict[str, Any] = {}
    if cache_entries_read > 0:
        source_info["cache_entries_read"] = cache_entries_read
    return graphs, [], source_info


def _read_cache_graphs(
    request: Dict[str, Any],
    input_path: Any,
    log_fn: Optional[Any],
) -> Tuple[List[Any], int]:
    """Read the graphs to merge from a workflow cache file.

    Args:
        request: Merge request.
        input_path: Path to the .db workflow cache.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (graphs, number of cache entries read).

    """
    return helpers._read_graphs_from_cache(
        input_path,
        log_fn,
        object_type=request["obj_filter"],
    )


def _read_graphml_file(input_path: Any, log_fn: Optional[Any]) -> Any:
    """Read a single GraphML graph file.

    Args:
        input_path: Path to the GraphML file.
        log_fn: Logging callback for progress reporting.

    Returns:
        Parsed graph.

    Raises:
        ActionExecutionError: If the file cannot be read.

    """
    from causaliq_core.graph.io import graphml

    try:
        graph = graphml.read(input_path)
        if log_fn:
            log_fn(f"Loaded file: {input_path}")
        return graph
    except Exception as e:
        raise ActionExecutionError(f"Failed to read {input_path}: {e}") from e


def _require_graphs(graphs: List[Any]) -> None:
    """Require at least one graph to merge.

    Args:
        graphs: Graphs read for the merge.

    Raises:
        ActionExecutionError: If no graphs were read.

    """
    if not graphs:
        raise ActionExecutionError("No graphs found to merge. Check inputs.")


def _final_weights(
    request: Dict[str, Any],
    graph_metadata: List[Dict[str, Any]],
    log_fn: Optional[Any],
) -> Tuple[Optional[List[float]], bool]:
    """Resolve the weights to apply to the merge.

    Args:
        request: Merge request.
        graph_metadata: Per-graph metadata of the graphs being merged.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (resolved weights, whether a weight spec was applied).

    Raises:
        ActionExecutionError: If the weights are invalid or unusable.

    """
    weights = request["weights"]
    if weights is None:
        return None, False
    if isinstance(weights, dict):
        _require_weight_metadata(graph_metadata)
        computed = helpers._compute_weights_from_metadata(
            graph_metadata, weights, log_fn
        )
        return computed, True
    if isinstance(weights, list):
        explicit: List[float] = weights
        return explicit, False
    raise ActionExecutionError(
        f"weights must be a list or dict, got {type(weights).__name__}"
    )


def _require_weight_metadata(graph_metadata: List[Dict[str, Any]]) -> None:
    """Require graph metadata for metadata-driven weights.

    Args:
        graph_metadata: Per-graph metadata of the graphs being merged.

    Raises:
        ActionExecutionError: If no graph metadata is available.

    """
    if not graph_metadata:
        raise ActionExecutionError(
            "Metadata-driven weights require aggregation "
            "mode (AGGREGATE pattern with .db input) or "
            "provide explicit weight list."
        )


def _merge_pdg(
    request: Dict[str, Any],
    graphs: List[Any],
    final_weights: Optional[List[float]],
    log_fn: Optional[Any],
) -> str:
    """Merge the graphs into a PDG and serialise it to GraphML.

    Args:
        request: Merge request.
        graphs: Graphs to merge.
        final_weights: Weights to apply to the merge.
        log_fn: Logging callback for progress reporting.

    Returns:
        PDG GraphML content.

    """
    from causaliq_analysis.merge import merge_graphs

    pdg = merge_graphs(
        graphs,
        weights=final_weights,
        cpdag=request["cpdag"],
        strategy=request["strategy"],
    )
    buffer = StringIO()
    _write_pdg(pdg, buffer)
    if log_fn:
        log_fn(f"Merged {len(graphs)} graphs into PDG")
    return buffer.getvalue()


def _write_pdg(pdg: Any, buffer: StringIO) -> None:
    """Write a PDG to a GraphML buffer.

    Args:
        pdg: PDG to serialise.
        buffer: Buffer receiving the GraphML document.

    """
    from causaliq_core.graph.io import graphml

    graphml.write_pdg(pdg, buffer)


def _success_metadata(
    request: Dict[str, Any],
    graphs: List[Any],
    final_weights: Optional[List[float]],
    weights_applied: bool,
    source_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the success metadata for a merge.

    Args:
        request: Merge request.
        graphs: Graphs that were merged.
        final_weights: Weights applied to the merge.
        weights_applied: Whether a weight specification was applied.
        source_info: Source information from graph loading.

    Returns:
        Action metadata describing the merged PDG.

    """
    metadata: Dict[str, Any] = {
        "action": "merge_graphs",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "num_graphs": len(graphs),
        "cpdag": request["cpdag"],
        "strategy": request["strategy"],
        "aggregation_mode": request["is_aggregation"],
        "output": {"type": "pdg", "format": "graphml"},
    }
    _add_optional_metadata(metadata, request, final_weights, weights_applied)
    metadata.update(source_info)
    return metadata


def _add_optional_metadata(
    metadata: Dict[str, Any],
    request: Dict[str, Any],
    final_weights: Optional[List[float]],
    weights_applied: bool,
) -> None:
    """Add the optional metadata keys for a merge.

    Args:
        metadata: Metadata being built.
        request: Merge request.
        final_weights: Weights applied to the merge.
        weights_applied: Whether a weight specification was applied.

    """
    if request["object_type"] is not None:
        metadata["object_type"] = request["object_type"]
    if request["filter"] is not None:
        metadata["filter"] = request["filter"]
    if weights_applied:
        metadata["weights_spec"] = request["weights"]
        metadata["weights_computed"] = final_weights
    elif final_weights:
        metadata["weights"] = final_weights


def _pdg_objects(content: str) -> List[Dict[str, Any]]:
    """Build the action objects for a merged PDG.

    Args:
        content: PDG GraphML content.

    Returns:
        Single-element list holding the PDG object.

    """
    return [{"type": "pdg", "format": "graphml", "content": content}]
