"""Collecting metric values from entries and input caches."""

import json
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.workflow_action import helpers
from causaliq_analysis.workflow_action.types import ActionExecutionError

from .stats import Argmax, Values

__all__ = ["_source_index", "_values_from_entries"]


def _values_from_entries(
    request: Dict[str, Any],
    values: Values,
    argmax: Argmax,
    log_fn: Optional[Any],
) -> Tuple[int, List[str]]:
    """Collect metric values from pre-scanned cache entries.

    Args:
        request: Summarisation request.
        values: Values per source and field, updated in place.
        argmax: Winning entry per source and field, updated in place.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (source entry count, source cache paths).

    """
    entries = request["aggregation_entries"] or []
    resolved, extra_names = _resolve_filter(request["filter"], entries)
    argmax_fields = request["argmax_fields"]
    sources: List[str] = []
    count = 0
    for entry_dict in entries:
        matrix_values, flat_meta = _entry_metadata(entry_dict)
        cache_path = entry_dict.get("cache_path", "unknown")
        sources.append(cache_path)
        if not _entry_matches(resolved, flat_meta, extra_names):
            continue
        count += 1
        where_matches = _matching_predicates(
            request.get("where_clauses", []), flat_meta
        )
        _accumulate_values(
            values,
            argmax,
            flat_meta,
            matrix_values,
            request["unique_fields"],
            argmax_fields,
            _source_index(cache_path, request["input_files"]),
            where_matches,
        )
        _log_entry(log_fn, matrix_values)
    return count, sources


def _source_index(cache_path: Any, input_files: List[str]) -> int:
    """Return the one-based position of a cache in the input list.

    Args:
        cache_path: Cache path recorded on a pre-scanned entry.
        input_files: Input cache paths, in declared order.

    Returns:
        One-based position of the cache, or 0 when the entry names no
        declared input cache.

    """
    for position, path in enumerate(input_files, start=1):
        if str(path) == str(cache_path):
            return position
    return 0


def _entry_metadata(entry_dict: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    """Return the matrix values and flattened values of an entry.

    Metric values live in the entry's typed JSON object; metadata supplies
    the provenance fields used by filters.

    Args:
        entry_dict: Pre-scanned cache entry descriptor.

    Returns:
        Tuple of (matrix values, flattened values).

    """
    matrix_values = entry_dict.get("matrix_values", {})
    from causaliq_workflow.cache.reporting import build_entry_view

    return matrix_values, build_entry_view(
        matrix_values,
        entry_dict.get("metadata", {}),
        _object_values(entry_dict),
    )


def _object_values(entry_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return the values held in an entry's JSON object.

    Args:
        entry_dict: Pre-scanned cache entry descriptor.

    Returns:
        Mapping of object fields, empty when no JSON object is present.

    """
    entry = entry_dict.get("entry")
    if entry is None:
        return {}
    values: Dict[str, Any] = {}
    for name in entry.object_types():
        obj = entry.get_object(name)
        if obj is None or obj.format != "json":
            continue
        values.update(_parse_json_object(obj.content))
    return values


def _parse_json_object(content: Any) -> Dict[str, Any]:
    """Parse a JSON object's content, returning {} for non-mappings."""
    try:
        data = json.loads(content or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _log_entry(log_fn: Optional[Any], matrix_values: Any) -> None:
    """Log a processed cache entry.

    Args:
        log_fn: Logging callback for progress reporting.
        matrix_values: Matrix values of the processed entry.

    """
    if log_fn:
        log_fn(f"Processed entry: {matrix_values}")


def _log_processed(log_fn: Optional[Any], matrix_values: Any) -> None:
    """Log a processed cache entry in cache-scan wording.

    Args:
        log_fn: Logging callback for progress reporting.
        matrix_values: Matrix values of the processed entry.

    """
    if log_fn:
        log_fn(f"Processed: {matrix_values}")


def _resolve_filter(
    filter_expr: Optional[str],
    entries: List[Dict[str, Any]],
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Resolve random() calls in a filter expression.

    Args:
        filter_expr: Filter expression, if any.
        entries: Pre-scanned cache entries providing metadata.

    Returns:
        Tuple of (resolved filter, extra names used by the filter).

    """
    if not filter_expr or "random(" not in filter_expr:
        return filter_expr, {}
    from causaliq_core.utils import resolve_random_calls

    metadata = [
        helpers._flatten_entry_metadata(
            entry.get("matrix_values", {}), entry.get("metadata", {})
        )
        for entry in entries
    ]
    return resolve_random_calls(filter_expr, metadata)


def _entry_matches(
    resolved_filter: Optional[str],
    flat_meta: Dict[str, Any],
    extra_names: Dict[str, Any],
) -> bool:
    """Return whether a cache entry passes the filter expression.

    Args:
        resolved_filter: Resolved filter expression, if any.
        flat_meta: Flattened metadata of the entry.
        extra_names: Extra names resolved for the filter.

    Returns:
        True when the entry matches the filter, or no filter is set.

    """
    if not resolved_filter:
        return True
    from causaliq_workflow.cache.reporting import evaluate_entry_filter

    try:
        names = {**flat_meta, **extra_names}
        return bool(evaluate_entry_filter(resolved_filter, names))
    except Exception:
        return False


def _matching_predicates(
    clauses: List[str],
    flat_meta: Dict[str, Any],
) -> List[str]:
    """Return the column predicates an entry satisfies.

    Args:
        clauses: Distinct ``where`` predicates used by the table.
        flat_meta: Flattened metadata of the entry.

    Returns:
        Predicates that match the entry, in the order declared.
    """
    if not clauses:
        return []
    from causaliq_workflow.cache.reporting import evaluate_entry_filter

    matches: List[str] = []
    for clause in clauses:
        try:
            if evaluate_entry_filter(clause, flat_meta):
                matches.append(clause)
        except Exception:
            continue
    return matches


def _accumulate_values(
    values: Values,
    argmax: Argmax,
    flat_meta: Dict[str, Any],
    matrix_values: Dict[str, Any],
    unique_fields: List[str],
    argmax_fields: List[str],
    source_index: int,
    where_matches: List[str],
) -> None:
    """Append numeric metric values from one entry.

    Every value is recorded once without a predicate, for plain columns,
    and once per satisfied predicate, for predicate-qualified columns.

    Args:
        values: Values per source, field and predicate, updated in place.
        argmax: Winning entry per source, field and predicate, updated in
            place.
        flat_meta: Flattened metadata of the entry.
        matrix_values: Matrix values of the entry.
        unique_fields: Fields to collect values for.
        argmax_fields: Fields whose argmax is tracked.
        source_index: One-based position of the entry's input cache.
        where_matches: Predicates the entry satisfies.

    """
    for field in unique_fields:
        value = helpers._get_nested_value(flat_meta, field)
        if value is None or not isinstance(value, (int, float)):
            continue
        number = float(value)
        values.setdefault((source_index, field, None), []).append(number)
        for clause in where_matches:
            values.setdefault((source_index, field, clause), []).append(number)
        if field in argmax_fields:
            _track_argmax(
                argmax,
                source_index,
                field,
                number,
                matrix_values,
                None,
            )
            for clause in where_matches:
                _track_argmax(
                    argmax,
                    source_index,
                    field,
                    number,
                    matrix_values,
                    clause,
                )


def _track_argmax(
    argmax: Argmax,
    source_index: int,
    field: str,
    value: float,
    matrix_values: Dict[str, Any],
    where: Optional[str],
) -> None:
    """Record the entry holding a field's maximum value.

    Args:
        argmax: Winning entry per source, field and predicate, updated in
            place.
        source_index: One-based position of the entry's input cache.
        field: Field whose maximum is tracked.
        value: Candidate value.
        matrix_values: Matrix values of the candidate entry.
        where: Entry predicate, or None for the unpredicated column.

    """
    current = argmax.get((source_index, field, where))
    if current is None or value > current[0]:
        argmax[(source_index, field, where)] = (
            value,
            dict(matrix_values),
        )


def _require_cache_file(cache_path: str) -> None:
    """Require an input path to be a workflow cache.

    Args:
        cache_path: Input path to check.

    Raises:
        ActionExecutionError: If the path is not a .db cache.

    """
    if not cache_path.lower().endswith(".db"):
        raise ActionExecutionError(
            f"summarise workflow action only supports .db "
            f"cache files, got: {cache_path}"
        )
