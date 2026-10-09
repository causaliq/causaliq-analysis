"""
Migrate_trace workflow action.

Migrates legacy trace files into GraphML graphs for cache storage. The action
is stateless, so validation and execution delegate to module-level helpers and
each step stays within the module and method limits.
"""

from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.migrate import run_migrate_trace
from causaliq_analysis.validation import (
    parse_sample_size,
    parse_seed_workflow,
)
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionPattern,
    ActionResult,
)

__all__ = ["MigrateTraceAction"]


class MigrateTraceAction(AnalysisAction):
    """Migrate legacy trace files into GraphML graphs.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "migrate_trace"
    pattern = ActionPattern.CREATE

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate migrate_trace parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        _require_traces_or_series_network(parameters)
        _require_parseable_sample_size(parameters)
        _require_parseable_seed(parameters)
        _require_cache_output(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Execute trace migration to GraphML graphs.

        Migrates the matched trace files, returning one GraphML object per
        graph together with the flattened cache metadata.

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
            request = _migrate_request(parameters)
            partial_id = _partial_id(request)
            sample_size = _optional_sample_size(request)
            seed = parse_seed_workflow(request["seed"])
            if mode == "dry-run":
                return _dry_run_result(partial_id, logger)
            result = run_migrate_trace(
                partial_id=partial_id,
                root_dir=request["root_dir"],
                sample_size=sample_size,
                seed=seed if seed else None,
                log_fn=_log_fn(logger),
            )
            if result.num_graphs == 0:
                return _no_traces_result(partial_id, sample_size, seed)
            return _success_result(result)
        except ValueError as e:
            raise ActionExecutionError(f"Trace migration failed: {e}") from e
        except Exception as e:
            raise ActionExecutionError(f"Trace migration failed: {e}") from e


def _require_traces_or_series_network(parameters: Dict[str, Any]) -> None:
    """Require traces, or both a series and a network.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If neither input form is provided.

    """
    if _has_value(parameters, "traces"):
        return
    if _has_value(parameters, "series") and _has_value(parameters, "network"):
        return
    raise ValueError(
        "'migrate_trace' requires either 'traces' parameter or "
        "both 'series' and 'network' parameters"
    )


def _has_value(parameters: Dict[str, Any], name: str) -> bool:
    """Return True when a parameter holds a value.

    Args:
        parameters: Action parameter values.
        name: Parameter name to check.

    Returns:
        True if the parameter is present and not None.

    """
    return name in parameters and parameters[name] is not None


def _require_parseable_sample_size(parameters: Dict[str, Any]) -> None:
    """Validate the sample size when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the sample size cannot be parsed.

    """
    sample_size = parameters.get("sample_size")
    if sample_size is not None:
        parse_sample_size(sample_size)


def _require_parseable_seed(parameters: Dict[str, Any]) -> None:
    """Validate the seed when one is provided.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the seed cannot be parsed.

    """
    seed = parameters.get("seed")
    if seed is not None:
        parse_seed_workflow(seed)


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
            "migrate_trace output must be a workflow cache (.db). "
            f"Got: {output_path}"
        )


def _migrate_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the migration request from action parameters.

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding the trace pattern inputs and filters.

    """
    request: Dict[str, Any] = {
        "traces": parameters.get("traces"),
        "root_dir": parameters.get("root_dir", "experiments"),
        "series": parameters.get("series"),
        "network": parameters.get("network"),
        "sample_size": parameters.get("sample_size"),
        "seed": parameters.get("seed", ""),
    }
    return request


def _partial_id(request: Dict[str, Any]) -> str:
    """Build the trace path pattern for a request.

    Args:
        request: Migration request.

    Returns:
        Partial trace identifier used to locate trace files.

    Raises:
        ActionExecutionError: If neither input form is provided.

    """
    if request["traces"]:
        traces_pattern: str = request["traces"]
        return traces_pattern.replace(".pkl.gz", "")
    if request["series"] and request["network"]:
        return f"{request['series']}/{request['network']}"
    raise ActionExecutionError(  # pragma: no cover
        "Must provide either 'traces' or both 'series' and 'network'"
    )


def _optional_sample_size(request: Dict[str, Any]) -> Optional[int]:
    """Parse the optional sample size filter.

    Args:
        request: Migration request.

    Returns:
        Parsed sample size, or None when not provided.

    """
    sample_size = None
    if request["sample_size"] is not None:
        sample_size = parse_sample_size(request["sample_size"])
    return sample_size


def _dry_run_result(
    partial_id: str,
    logger: Optional[Any],
) -> ActionResult:
    """Return the dry-run result for a migration.

    Args:
        partial_id: Partial trace identifier used to locate trace files.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "skipped".

    """
    if logger and logger.is_terminal_logging:
        print(f"Would migrate traces from {partial_id}")
    metadata: Dict[str, Any] = {"message": "Dry-run mode", "num_graphs": 0}
    return ("skipped", metadata, [])


def _log_fn(logger: Optional[Any]) -> Optional[Any]:
    """Return the logging callback for a migration.

    Args:
        logger: Logger for reporting.

    Returns:
        print when terminal logging is enabled, otherwise None.

    """
    if logger and logger.is_terminal_logging:
        return print
    return None


def _no_traces_result(
    partial_id: str,
    sample_size: Optional[int],
    seed: Tuple[int, ...],
) -> ActionResult:
    """Return the skipped result for a migration without matching traces.

    Args:
        partial_id: Partial trace identifier used to locate trace files.
        sample_size: Parsed sample size filter.
        seed: Parsed seed filter.

    Returns:
        ActionResult tuple with status "skipped".

    """
    metadata: Dict[str, Any] = {
        "message": (
            f"No traces for {partial_id} "
            f"sample_size={sample_size} "
            f"seed={seed}"
        ),
        "num_graphs": 0,
    }
    return ("skipped", metadata, [])


def _graph_objects(result: Any) -> List[Dict[str, Any]]:
    """Build the GraphML objects for a migration result.

    Args:
        result: Migration result holding the migrated graphs.

    Returns:
        One GraphML object per migrated graph.

    """
    total = len(result.graphs)
    return [
        _graph_object(index, graph, total)
        for index, graph in enumerate(result.graphs)
    ]


def _graph_object(index: int, graph: Any, total: int) -> Dict[str, Any]:
    """Build the GraphML object for a single migrated graph.

    Args:
        index: Position of the graph in the result.
        graph: Migrated graph holding the GraphML content.
        total: Total number of graphs in the result.

    Returns:
        Cache object holding the GraphML document.

    """
    return {
        "type": _object_type(index, total),
        "format": "graphml",
        "action": "migrate_trace",
        "content": graph.graphml,
    }


def _object_type(index: int, total: int) -> str:
    """Return the cache object type for a migrated graph.

    Args:
        index: Position of the graph in the result.
        total: Total number of graphs in the result.

    Returns:
        'dag' for a single graph, 'dag_<index>' otherwise.

    """
    return "dag" if total == 1 else f"dag_{index}"


def _graph_metadata(result: Any) -> Dict[str, Any]:
    """Build the per-graph metadata for a migration result.

    Args:
        result: Migration result holding the migrated graphs.

    Returns:
        Flattened metadata for a single graph, nested metadata otherwise.

    """
    metadata: Dict[str, Any] = {}
    total = len(result.graphs)
    for index, graph in enumerate(result.graphs):
        graph_meta = {"trace_id": graph.trace_id, **graph.metadata}
        object_type = _object_type(index, total)
        _add_graph_metadata(metadata, object_type, graph_meta, total)
    return metadata


def _add_graph_metadata(
    metadata: Dict[str, Any],
    object_type: str,
    graph_meta: Dict[str, Any],
    total: int,
) -> None:
    """Add the metadata of a single graph to the result metadata.

    Args:
        metadata: Metadata being built.
        object_type: Cache object type of the graph.
        graph_meta: Metadata of a single graph.
        total: Total number of graphs in the result.

    """
    if total == 1:
        metadata.update(graph_meta)
    else:
        metadata[object_type] = graph_meta


def _success_result(result: Any) -> ActionResult:
    """Build the successful action result.

    Args:
        result: Migration result holding the graphs and counters.

    Returns:
        ActionResult tuple with status "success".

    """
    metadata: Dict[str, Any] = {
        "num_graphs": result.num_graphs,
        "skipped": result.skipped,
    }
    metadata.update(_graph_metadata(result))
    return ("success", metadata, _graph_objects(result))
