"""
Shared helper functions for analysis workflow actions.

These helpers perform cache parsing, metadata flattening and graph
extraction for the action provider. They are module-level functions so
that individual action sub-modules can reuse them without requiring a
provider instance.
"""

from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.graph_io import is_pdg_graphml
from causaliq_analysis.workflow_action.types import ActionExecutionError

# Graph object types that can be evaluated as graphs
_VALID_GRAPH_TYPES = ("dag", "pdag", "cpdag", "pdg")


def _log(log_fn: Optional[Any], message: str) -> None:
    """Log a message when a logging function is provided.

    Args:
        log_fn: Optional logging function.
        message: Message to log.
    """
    if log_fn:
        log_fn(message)


def _extract_graph_from_entry(
    entry: Any,
    source_label: str,
) -> Tuple[Any, str]:
    """Extract an evaluable graph from a cache entry.

    Locates a GraphML object of type 'dag', 'pdag', 'cpdag' or 'pdg'
    within the entry. Deterministic graphs are read as DAG/PDAG while
    PDG content (carrying edge probabilities) is read as a PDG.

    Args:
        entry: Cache entry containing typed objects.
        source_label: Human-readable description of the entry source,
            used in error messages.

    Returns:
        Tuple of (parsed graph, object type).

    Raises:
        ActionExecutionError: If no evaluable graph is found or the
            graph cannot be parsed.
    """
    for obj_type in entry.object_types():
        if obj_type not in _VALID_GRAPH_TYPES:
            continue
        obj = entry.get_object(obj_type)
        if obj is None or obj.format != "graphml":
            continue
        parsed = _read_graph_object(obj, obj_type, source_label)
        if parsed is not None:
            return parsed

    raise ActionExecutionError(
        f"No evaluable graph object found in {source_label}. "
        "evaluate_graph requires a 'dag', 'pdag', 'cpdag' or 'pdg' "
        "object."
    )


def _read_graph_object(
    obj: Any,
    obj_type: str,
    source_label: str,
) -> Optional[Tuple[Any, str]]:
    """Read one GraphML object into an evaluable graph.

    Args:
        obj: Cache object holding GraphML content.
        obj_type: Object type name (e.g. 'dag' or 'pdg').
        source_label: Source description used in error messages.

    Returns:
        Tuple of (parsed graph, object type), or None when a PDG-labelled
        object carries no probability data.

    Raises:
        ActionExecutionError: If the object cannot be parsed.
    """
    from io import StringIO

    from causaliq_core.graph.io import graphml

    is_pdg = is_pdg_graphml(obj.content)
    if obj_type == "pdg" and not is_pdg:
        # PDG-labelled object without probability data: skip
        return None
    try:
        if is_pdg:
            return graphml.read_pdg(StringIO(obj.content)), "pdg"
        return graphml.read(StringIO(obj.content)), obj_type
    except Exception as e:
        raise ActionExecutionError(
            f"Failed to parse graph '{obj_type}' from " f"{source_label}: {e}"
        ) from e


def _collect_values_from_cache(
    cache_path: str,
    fields: List[str],
    all_values: Dict[str, List[float]],
    filter_expr: Optional[str],
    matrix_filter: Optional[Dict[str, Any]],
    log_fn: Optional[Any],
) -> int:
    """Collect metric values from a workflow cache.

    Args:
        cache_path: Path to .db cache file.
        fields: List of field names to extract.
        all_values: Dictionary to append values to.
        filter_expr: Optional filter expression.
        matrix_filter: Optional matrix values to filter by.
        log_fn: Optional logging function.

    Returns:
        Number of entries processed.
    """
    try:
        from causaliq_workflow.cache import WorkflowCache
    except ImportError:  # pragma: no cover
        raise ActionExecutionError(
            "causaliq-workflow required to read .db caches"
        )

    try:
        with WorkflowCache(cache_path) as cache:
            count = _fold_cache_entries(
                cache,
                fields,
                all_values,
                filter_expr,
                matrix_filter,
                log_fn,
            )
    except FileNotFoundError:  # pragma: no cover
        raise ActionExecutionError(f"Cache file not found: {cache_path}")
    except Exception as e:
        if isinstance(e, ActionExecutionError):  # pragma: no cover
            raise
        raise ActionExecutionError(
            f"Failed to read cache '{cache_path}': {e}"
        ) from e

    return count


def _fold_cache_entries(
    cache: Any,
    fields: List[str],
    all_values: Dict[str, List[float]],
    filter_expr: Optional[str],
    matrix_filter: Optional[Dict[str, Any]],
    log_fn: Optional[Any],
) -> int:
    """Collect metric values from every matching cache entry.

    Args:
        cache: Open workflow cache.
        fields: List of field names to extract.
        all_values: Dictionary to append values to.
        filter_expr: Optional filter expression.
        matrix_filter: Optional matrix values to filter by.
        log_fn: Optional logging function.

    Returns:
        Number of entries processed.
    """
    entries = cache.list_entries()
    filters: Tuple[Optional[str], Dict[str, Any]] = (filter_expr, {})
    if filter_expr and "random(" in filter_expr:
        filters = _resolve_random_filter(entries, cache, filter_expr)

    count = 0
    for entry_info in entries:
        entry = cache.get(entry_info["matrix_values"])
        if entry is None:  # pragma: no cover
            continue
        if _collect_entry_values(
            entry_info,
            entry,
            fields,
            all_values,
            filters,
            matrix_filter,
            log_fn,
        ):
            count += 1

    return count


def _resolve_random_filter(
    entries: List[Dict[str, Any]],
    cache: Any,
    filter_expr: str,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Pre-resolve random() calls in a filter expression.

    Args:
        entries: Cache entry infos to inspect.
        cache: Open workflow cache.
        filter_expr: Filter expression containing random() calls.

    Returns:
        Tuple of (resolved filter expression, extra names).
    """
    from causaliq_core.utils import resolve_random_calls

    metadata = []
    for entry_info in entries:
        entry = cache.get(entry_info["matrix_values"])
        if entry is not None:
            metadata.append(
                _flatten_entry_metadata(
                    entry_info["matrix_values"], entry.metadata
                )
            )
    return resolve_random_calls(filter_expr, metadata)


def _is_matrix_filter_match(
    matrix_values: Dict[str, Any],
    matrix_filter: Optional[Dict[str, Any]],
) -> bool:
    """Check entry matrix values against the matrix filter.

    Args:
        matrix_values: Entry matrix variable values.
        matrix_filter: Optional matrix values to filter by.

    Returns:
        True when the entry matches, or when no filter was given.
    """
    if not matrix_filter:
        return True
    return all(
        matrix_values.get(key) == value for key, value in matrix_filter.items()
    )


def _is_entry_filter_match(
    flat_meta: Dict[str, Any],
    filters: Tuple[Optional[str], Dict[str, Any]],
) -> bool:
    """Check flattened metadata against the resolved entry filter.

    Args:
        flat_meta: Flattened entry metadata.
        filters: Resolved filter expression and extra names.

    Returns:
        True when the entry should be processed.
    """
    resolved_filter, extra_names = filters
    if not resolved_filter:
        return True
    try:
        from causaliq_core.utils import evaluate_filter

        values = {**flat_meta, **extra_names}
        return bool(evaluate_filter(resolved_filter, values))
    except Exception:
        return False


def _collect_entry_values(
    entry_info: Dict[str, Any],
    entry: Any,
    fields: List[str],
    all_values: Dict[str, List[float]],
    filters: Tuple[Optional[str], Dict[str, Any]],
    matrix_filter: Optional[Dict[str, Any]],
    log_fn: Optional[Any],
) -> bool:
    """Collect metric values from a single cache entry.

    Args:
        entry_info: Entry info from the cache scan.
        entry: Cache entry object.
        fields: List of field names to extract.
        all_values: Dictionary to append values to.
        filters: Resolved filter expression and extra names.
        matrix_filter: Optional matrix values to filter by.
        log_fn: Optional logging function.

    Returns:
        True when the entry was processed, False when it was filtered out.
    """
    matrix_values = entry_info["matrix_values"]
    if not _is_matrix_filter_match(matrix_values, matrix_filter):
        return False
    flat_meta = _flatten_entry_metadata(matrix_values, entry.metadata)
    if not _is_entry_filter_match(flat_meta, filters):
        return False
    _append_metric_values(flat_meta, fields, all_values)
    _log(log_fn, f"Processed: {matrix_values}")
    return True


def _append_metric_values(
    flat_meta: Dict[str, Any],
    fields: List[str],
    all_values: Dict[str, List[float]],
) -> None:
    """Append numeric metric values from flattened metadata.

    Args:
        flat_meta: Flattened entry metadata.
        fields: List of field names to extract.
        all_values: Dictionary to append values to.
    """
    for field in fields:
        value = _get_nested_value(flat_meta, field)
        if value is not None and isinstance(value, (int, float)):
            all_values[field].append(float(value))


def _get_nested_value(data: Dict[str, Any], field: str) -> Any:
    """Get value from dict using dotted path notation.

    Args:
        data: Dictionary to search.
        field: Field name, optionally with dots for nested access.

    Returns:
        Value if found, None otherwise.
    """
    # First try direct key lookup
    if field in data:
        return data[field]

    # Dotted path traversal (defensive - flattened dicts don't need this)
    parts = field.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]  # pragma: no cover
        else:
            return None
    return current  # pragma: no cover


def _extract_graphs_from_entries(
    entries: List[Dict[str, Any]],
    log_fn: Optional[Any],
    *,
    object_type: Optional[str] = None,
) -> Tuple[List[Any], List[Dict[str, Any]], Dict[str, Any]]:
    """Extract graphs from aggregation entries.

    Reads graphml objects from pre-scanned cache entries provided
    by the workflow executor in aggregation mode.

    Args:
        entries: List of entry dictionaries from aggregation scan.
            Each entry has: matrix_values, metadata, cache_path,
            entry_hash, entry (the CacheEntry object).
        log_fn: Optional logging function.
        object_type: If set, only extract objects with this type
            name (e.g., 'pdg'). If None, all graphml objects
            are extracted.

    Returns:
        Tuple of:
        - list of graphs
        - list of flattened metadata dicts (one per graph)
        - source_info dict with provenance

    Raises:
        ActionExecutionError: If graph extraction fails.
    """
    sources = [item for item in entries if item.get("entry") is not None]
    loaded = [
        _load_entry_graphs(item, object_type, log_fn) for item in sources
    ]
    found = [item for item in loaded if item is not None]
    graphs = [graph for item in found for graph in item[0]]
    graph_metadata = [item[1] for item in found for _ in item[0]]
    source_info = {
        "source_count": len(found),
        "source_caches": sorted(
            {item.get("cache_path", "unknown") for item in sources}
        ),
    }

    return graphs, graph_metadata, source_info


def _load_entry_graphs(
    entry_dict: Dict[str, Any],
    object_type: Optional[str],
    log_fn: Optional[Any],
) -> Optional[Tuple[List[Any], Dict[str, Any]]]:
    """Load graphs and metadata for one aggregation entry.

    Args:
        entry_dict: Entry dictionary from the aggregation scan.
        object_type: If set, only extract objects with this type name.
        log_fn: Optional logging function.

    Returns:
        Tuple of (graphs, flattened metadata), or None when the entry
        holds no graphml objects.
    """
    matrix_values = entry_dict.get("matrix_values", {})
    graphs = _load_graphs_from_entry(
        entry_dict["entry"],
        matrix_values,
        object_type,
        log_fn,
        "entry",
    )
    if not graphs:
        return None
    flat_meta = _flatten_entry_metadata(
        matrix_values, entry_dict.get("metadata", {})
    )
    return graphs, flat_meta


def _load_graphs_from_entry(
    entry: Any,
    matrix_values: Dict[str, Any],
    object_type: Optional[str],
    log_fn: Optional[Any],
    location: str,
) -> List[Any]:
    """Load every matching GraphML object from one cache entry.

    Args:
        entry: Cache entry to scan.
        matrix_values: Entry matrix values, used in log messages.
        object_type: If set, only extract objects with this type name.
        log_fn: Optional logging function.
        location: Source description used in error messages.

    Returns:
        List of parsed graphs found in the entry.

    Raises:
        ActionExecutionError: If an object cannot be parsed.
    """
    graphs: List[Any] = []
    for obj_type in entry.object_types():
        if object_type is not None and obj_type != object_type:
            continue
        obj = entry.get_object(obj_type)
        if obj is None or obj.format != "graphml":
            continue
        source_label = f"{location} {matrix_values}"
        graphs.append(_parse_cache_object(obj, obj_type, source_label))
        _log(log_fn, f"Loaded '{obj_type}' from {matrix_values}")

    if not graphs:
        _log(log_fn, f"Entry {matrix_values} has no graphml objects")
    return graphs


def _parse_cache_object(obj: Any, obj_type: str, source_label: str) -> Any:
    """Read one GraphML cache object into a graph.

    Args:
        obj: Cache object holding GraphML content.
        obj_type: Object type name (e.g. 'dag' or 'pdg').
        source_label: Source description used in error messages.

    Returns:
        Parsed graph.

    Raises:
        ActionExecutionError: If the object cannot be parsed.
    """
    from io import StringIO

    from causaliq_core.graph.io import graphml

    try:
        if obj_type == "pdg":
            return graphml.read_pdg(StringIO(obj.content))
        return graphml.read(StringIO(obj.content))
    except Exception as e:
        raise ActionExecutionError(
            f"Failed to parse graph '{obj_type}' from " f"{source_label}: {e}"
        ) from e


def _flatten_entry_metadata(
    matrix_values: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Flatten entry metadata for filter/weight evaluation.

    Combines matrix values with nested metadata structure into a flat
    dictionary suitable for filter expression or weight computation.

    Args:
        matrix_values: Entry's matrix variable values.
        metadata: Entry's nested metadata dictionary.

    Returns:
        Flat dictionary with all metadata fields.
    """
    flat: Dict[str, Any] = dict(matrix_values)
    for provider_name, provider_data in metadata.items():
        _flatten_provider_metadata(provider_name, provider_data, flat)
    return flat


def _flatten_provider_metadata(
    provider_name: str,
    provider_data: Any,
    flat: Dict[str, Any],
) -> None:
    """Flatten one provider's metadata section into a flat dictionary.

    Args:
        provider_name: Provider key in the nested metadata.
        provider_data: Provider metadata section.
        flat: Flat dictionary, updated in place.
    """
    if not isinstance(provider_data, dict):
        flat[provider_name] = provider_data
        return

    for action_name, action_data in provider_data.items():
        _flatten_action_metadata(provider_name, action_name, action_data, flat)


def _flatten_action_metadata(
    provider_name: str,
    action_name: str,
    action_data: Any,
    flat: Dict[str, Any],
) -> None:
    """Flatten one action's metadata section into a flat dictionary.

    Args:
        provider_name: Provider key in the nested metadata.
        action_name: Action key in the nested metadata.
        action_data: Action metadata section.
        flat: Flat dictionary, updated in place.
    """
    qual_key = f"{provider_name}.{action_name}"
    if not isinstance(action_data, dict):
        flat[qual_key] = action_data
        return

    for key, value in action_data.items():
        if key not in flat:
            flat[key] = value
        flat[f"{qual_key}.{key}"] = value


def _compute_weights_from_metadata(
    graph_metadata: List[Dict[str, Any]],
    weight_spec: Dict[str, Dict[str, float]],
    log_fn: Optional[Any],
) -> List[float]:
    """Compute normalised weights from graph metadata.

    Uses the weight specification to compute a weight for each graph
    based on its metadata. Weights are normalised to sum to 1.0.

    Args:
        graph_metadata: List of flattened metadata dicts (one per graph).
        weight_spec: Mapping from metadata field to value-weight pairs.
        log_fn: Optional logging function.

    Returns:
        List of normalised weights (one per graph, sum to 1.0).

    Raises:
        ActionExecutionError: If weight computation fails.
    """
    from causaliq_core.utils import (
        WeightSpecError,
        compute_weight,
        validate_weight_spec,
    )

    try:
        validate_weight_spec(weight_spec)
    except WeightSpecError as e:
        raise ActionExecutionError(f"Invalid weight specification: {e}")

    raw_weights = [
        compute_weight(meta, weight_spec) for meta in graph_metadata
    ]
    return _normalise_weights(raw_weights, log_fn)


def _normalise_weights(
    raw_weights: List[float],
    log_fn: Optional[Any],
) -> List[float]:
    """Normalise raw weights so that they sum to 1.0.

    Args:
        raw_weights: Unnormalised weight per graph.
        log_fn: Optional logging function.

    Returns:
        List of normalised weights (one per graph, sum to 1.0).

    Raises:
        ActionExecutionError: If the weights sum to zero or less.
    """
    total = sum(raw_weights)
    if total <= 0:
        raise ActionExecutionError(
            "Computed weights sum to zero or negative. "
            "Check weight specification."
        )
    normalised = [weight / total for weight in raw_weights]
    _log(
        log_fn,
        f"Computed weights from metadata: "
        f"raw={raw_weights}, normalised={normalised}",
    )
    return normalised


def _read_graphs_from_cache(
    cache_path: str,
    log_fn: Optional[Any],
    *,
    object_type: Optional[str] = None,
) -> Tuple[List[Any], int]:
    """Read graphs from a WorkflowCache database.

    Finds graphml objects in all cache entries.

    Args:
        cache_path: Path to WorkflowCache database file (.db).
        log_fn: Optional logging function.
        object_type: If set, only extract objects with this type
            name (e.g., 'pdg'). If None, all graphml objects
            are extracted.

    Returns:
        Tuple of (list of graphs, number of entries with graphs).

    Raises:
        ActionExecutionError: If cache cannot be read.
    """
    from causaliq_workflow.cache import WorkflowCache

    try:
        with WorkflowCache(cache_path) as cache:
            return _read_graphs_from_open_cache(cache, log_fn, object_type)
    except FileNotFoundError:
        raise ActionExecutionError(f"Cache file not found: {cache_path}")
    except Exception as e:
        if isinstance(e, ActionExecutionError):
            raise
        raise ActionExecutionError(
            f"Failed to read from cache '{cache_path}': {e}"
        ) from e


def _read_graphs_from_open_cache(
    cache: Any,
    log_fn: Optional[Any],
    object_type: Optional[str],
) -> Tuple[List[Any], int]:
    """Read graphs from every entry of an open workflow cache.

    Args:
        cache: Open workflow cache.
        log_fn: Optional logging function.
        object_type: If set, only extract objects with this type name.

    Returns:
        Tuple of (list of graphs, number of entries with graphs).
    """
    entries = cache.list_entries()
    _log(log_fn, f"Found {len(entries)} entries in cache")

    graphs: List[Any] = []
    entries_with_graphs = 0
    for entry_info in entries:
        matrix_values = entry_info.get("matrix_values", {})
        entry = cache.get(matrix_values)
        if entry is None:
            continue
        entry_graphs = _load_graphs_from_entry(
            entry,
            matrix_values,
            object_type,
            log_fn,
            "cache entry",
        )
        if not entry_graphs:
            continue
        graphs.extend(entry_graphs)
        entries_with_graphs += 1

    return graphs, entries_with_graphs
