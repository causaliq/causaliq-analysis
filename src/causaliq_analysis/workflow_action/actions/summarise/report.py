"""Collecting grouped metric values for report-mode summarisation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.workflow_action.actions.summarise.collect import (
    _accumulate_values,
    _entry_matches,
    _entry_metadata,
    _log_processed,
    _require_cache_file,
    _resolve_filter,
)
from causaliq_analysis.workflow_action.actions.summarise.groups import (
    _group_matches,
)

__all__ = ["_collect_report_values"]


@dataclass
class _ReportValues:
    """Collected values for every report group.

    Attributes:
        values: Metric values per group, per field.
        argmax: Winning entry per group, per field.
        counts: Number of matching entries per group.
        sources: Input cache paths read.
    """

    values: List[Dict[str, List[float]]] = field(default_factory=list)
    argmax: List[Dict[str, Tuple[float, Dict[str, Any]]]] = field(
        default_factory=list
    )
    counts: List[int] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


def _collect_report_values(
    request: Dict[str, Any],
    groups: List[Dict[str, Any]],
    dimensions: List[str],
    log_fn: Optional[Any],
) -> _ReportValues:
    """Collect values for every group in one pass over the input caches.

    Args:
        request: Summarisation request.
        groups: Group matrix values, one per report row.
        dimensions: Grouping dimension names.
        log_fn: Logging callback for progress reporting.

    Returns:
        Values, argmax winners, entry counts and source paths per group.

    Raises:
        ActionExecutionError: If no input cache is provided or readable.

    """
    collected = _ReportValues(
        values=[
            {field: [] for field in request["unique_fields"]} for _ in groups
        ],
        argmax=[{} for _ in groups],
        counts=[0 for _ in groups],
    )
    for cache_path in request["input_files"]:
        _require_cache_file(cache_path)
        collected.sources.append(cache_path)
        _fold_cache(cache_path, request, groups, dimensions, collected, log_fn)
    if log_fn:
        log_fn(f"Collected values from {sum(collected.counts)} entries")
    return collected


def _fold_cache(
    cache_path: str,
    request: Dict[str, Any],
    groups: List[Dict[str, Any]],
    dimensions: List[str],
    collected: _ReportValues,
    log_fn: Optional[Any],
) -> None:
    """Append one cache's matching values to the per-group accumulator.

    Args:
        cache_path: Input cache to read.
        request: Summarisation request.
        groups: Group matrix values.
        dimensions: Grouping dimension names.
        collected: Accumulator updated in place.
        log_fn: Logging callback for progress reporting.

    """
    entries = _report_entries(cache_path)
    resolved, extra_names = _resolve_filter(request["filter"], entries)
    argmax_fields = [field for field, _ in request["argmax_specs"]]
    fields = request["unique_fields"]
    for entry_dict in entries:
        matrix_values, flat_meta = _entry_metadata(entry_dict)
        if not _entry_matches(resolved, flat_meta, extra_names):
            continue
        _fold_groups(
            matrix_values,
            flat_meta,
            groups,
            dimensions,
            fields,
            argmax_fields,
            collected,
            log_fn,
        )


def _fold_groups(
    matrix_values: Dict[str, Any],
    flat_meta: Dict[str, Any],
    groups: List[Dict[str, Any]],
    dimensions: List[str],
    fields: List[str],
    argmax_fields: List[str],
    collected: _ReportValues,
    log_fn: Optional[Any],
) -> None:
    """Append one entry's values to every group it belongs to.

    Args:
        matrix_values: Entry matrix values.
        flat_meta: Flattened entry values.
        groups: Group matrix values.
        dimensions: Grouping dimension names.
        fields: Field names to collect.
        argmax_fields: Fields whose argmax is tracked.
        collected: Accumulator updated in place.
        log_fn: Logging callback for progress reporting.

    """
    for index, group in enumerate(groups):
        if not _group_matches(matrix_values, group, dimensions):
            continue
        collected.counts[index] += 1
        _accumulate_values(
            collected.values[index],
            collected.argmax[index],
            flat_meta,
            matrix_values,
            fields,
            argmax_fields,
        )
        _log_processed(log_fn, matrix_values)


def _report_entries(cache_path: str) -> List[Dict[str, Any]]:
    """Load every entry of one workflow cache.

    Args:
        cache_path: Path to a workflow cache.

    Returns:
        List of entry descriptors holding matrix values, metadata and the
        entry object.

    Raises:
        ActionExecutionError: If the cache cannot be read.

    """
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    try:
        return _read_cache_entries(cache_path)
    except Exception as e:
        raise ActionExecutionError(
            f"Failed to read cache '{cache_path}': {e}"
        ) from e


def _read_cache_entries(cache_path: str) -> List[Dict[str, Any]]:
    """Read every entry of one cache into entry descriptors.

    Args:
        cache_path: Path to a workflow cache.

    Returns:
        Entry descriptors holding matrix values, metadata and the entry
        object.

    """
    from causaliq_workflow.cache import WorkflowCache

    entries: List[Dict[str, Any]] = []
    with WorkflowCache(cache_path) as cache:
        for info in cache.list_entries():
            entry = cache.get(info["matrix_values"])
            if entry is None:  # pragma: no cover
                continue
            entries.append(
                {
                    "matrix_values": info["matrix_values"],
                    "metadata": entry.metadata,
                    "entry": entry,
                }
            )
    return entries
