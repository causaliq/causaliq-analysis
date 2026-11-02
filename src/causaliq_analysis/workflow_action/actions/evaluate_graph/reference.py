"""Resolving the ground-truth reference graph for evaluate_graph."""

from typing import Any, Dict, List

from causaliq_analysis import graph_io
from causaliq_analysis.workflow_action import helpers
from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = [
    "_reference_cache_entry",
    "_require_matching_keys",
    "_resolve_reference_graph",
]


def _resolve_reference_graph(
    reference_path: str,
    entry: Dict[str, Any],
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
        entry: Matched aggregation entry holding the 'matrix_values' for
            the current input entry.

    Returns:
        The parsed reference graph.

    Raises:
        ActionExecutionError: If the reference cannot be resolved.

    """
    if not str(reference_path).lower().endswith(".db"):
        return _reference_from_file(reference_path)
    return _reference_from_cache(reference_path, entry)


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
    entry: Dict[str, Any],
) -> Any:
    """Resolve a reference graph from a reference workflow cache.

    Args:
        reference_path: Path to the reference workflow cache (.db).
        entry: Matched aggregation entry data.

    Returns:
        The parsed reference graph.

    Raises:
        ActionExecutionError: If the reference cannot be resolved.

    """
    from causaliq_workflow.cache import WorkflowCache

    matrix_values = entry.get("matrix_values", {})
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
