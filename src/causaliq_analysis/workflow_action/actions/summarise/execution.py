"""Running one summarisation: collect, compute, render."""

import json
from datetime import datetime, timezone
from typing import Any

from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionResult,
)

from .collect import _values_from_entries
from .groups import _report_groups
from .render import _is_csv_output, _write_single_table, _write_summary
from .render_csv import _write_csv
from .render_significance import _write_significance
from .report import _collect_report_values, _ReportValues
from .significance import _significance_rows
from .stats import Argmax, Values, _compute_stats

__all__ = [
    "_dry_run_result",
    "_summarise",
]


def _dry_run_result(
    request: dict[str, Any],
    logger: Any | None,
) -> ActionResult:
    """Return the dry-run result for a summarisation.

    Args:
        request: Summarisation request.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "skipped".

    """
    if logger and logger.is_terminal_logging:
        _print_dry_run(request)
    return (
        "skipped",
        {
            "message": "Dry-run mode",
            "aggregation_mode": request["is_aggregation"],
            "metrics": request["metric_specs"],
            "significance": len(request["significance"]),
        },
        [],
    )


def _print_dry_run(request: dict[str, Any]) -> None:
    """Print the dry-run message for the active summarisation mode.

    Args:
        request: Summarisation request.

    """
    if request["is_aggregation"]:
        entry_count = len(request["aggregation_entries"] or [])
        print(f"Would summarise metrics from {entry_count} entries")
    else:
        print("Would summarise metrics from input files")


def _log_fn(logger: Any | None) -> Any | None:
    """Build a logging callback from a workflow logger.

    Args:
        logger: Logger for reporting, if any.

    Returns:
        The print function when terminal logging is enabled, else None.

    """
    if logger and logger.is_terminal_logging:
        return print
    return None


def _summarise(
    request: dict[str, Any],
    context: Any | None,
    logger: Any | None,
) -> ActionResult:
    """Summarise the requested metrics and write the report file.

    Args:
        request: Summarisation request.
        context: Workflow context holding matrix values.
        logger: Logger for reporting.

    Returns:
        ActionResult tuple with status "success".

    Raises:
        ActionExecutionError: If collection or CSV output fails.

    """
    log_fn = _log_fn(logger)
    cache_mode = _is_cache_request(request, context)
    if request["output"] is None and not cache_mode:
        raise ActionExecutionError(
            "summarise requires 'output' parameter with a .csv, .tex, "
            ".md or .db path"
        )
    if cache_mode:
        return _summarise_cache(request, context, log_fn)
    if request["input_files"]:
        return _summarise_report(request, context, log_fn)
    return _summarise_entries(request, context, log_fn)


def _is_cache_request(
    request: dict[str, Any],
    context: Any | None,
) -> bool:
    """Return True when the summary is written to a metrics cache.

    Args:
        request: Summarisation request.
        context: Workflow context holding the open output cache, if any.

    Returns:
        True when a ``.db`` output was requested, or when no output path
        remains (the executor removes it) and an output cache is open.

    """
    if request.get("is_cache_output"):
        return True
    if request.get("output") is not None:
        return False
    return getattr(context, "cache", None) is not None


def _summarise_cache(
    request: dict[str, Any],
    context: Any | None,
    log_fn: Any | None,
) -> ActionResult:
    """Summarise the matched entries into a metrics object.

    One metrics object is returned for the current matrix combination;
    the workflow executor stores it under that combination's values.

    Args:
        request: Summarisation request.
        context: Workflow context holding the open output cache.
        log_fn: Logging callback for progress reporting.

    Returns:
        ActionResult tuple with status "success".

    Raises:
        ActionExecutionError: If the request cannot produce a cache entry.

    """
    if request["significance"]:
        raise ActionExecutionError(
            "significance requires table output, not a metrics cache"
        )
    if not request["is_aggregation"]:
        raise ActionExecutionError(
            "summarise metrics-cache output requires 'input' cache files"
        )
    values: Values = {}
    argmax: Argmax = {}
    count, sources = _values_from_entries(request, values, argmax, log_fn)
    results = _compute_stats(request["parsed_metrics"], values, argmax)
    metadata = _cache_metadata(request, context, count, sources)
    return ("success", metadata, _metrics_object(results))


def _cache_metadata(
    request: dict[str, Any],
    context: Any | None,
    source_count: int,
    sources: list[str],
) -> dict[str, Any]:
    """Build the metadata for a metrics-cache summary entry.

    The computed values live in the metrics object rather than the
    metadata, so the cache entry keeps one source of truth.

    Args:
        request: Summarisation request.
        context: Workflow context holding the open output cache.
        source_count: Number of entries contributing values.
        sources: Source cache paths.

    Returns:
        Action metadata describing the metrics object.

    """
    metadata: dict[str, Any] = {
        "source_count": source_count,
        "source_caches": sorted(set(sources)),
        "metrics": request["metric_specs"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output": {"type": "metrics", "format": "json"},
    }
    if request["filter"]:
        metadata["filter"] = request["filter"]
    db_path = getattr(getattr(context, "cache", None), "db_path", None)
    if db_path is not None:
        metadata["output_path"] = str(db_path)
    return metadata


def _metrics_object(results: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the metrics object written to the output cache.

    Args:
        results: Computed column values.

    Returns:
        Single-element list holding the metrics object.

    """
    return [
        {
            "type": "metrics",
            "format": "json",
            "action": "summarise",
            "content": json.dumps(results),
        }
    ]


def _summarise_report(
    request: dict[str, Any],
    context: Any | None,
    log_fn: Any | None,
) -> ActionResult:
    """Summarise grouped input caches and rewrite the report file.

    One row is produced per workflow matrix combination, and the file is
    rewritten from scratch so repeated runs cannot duplicate rows.

    Args:
        request: Summarisation request.
        context: Workflow context holding the matrix definition.
        log_fn: Logging callback for progress reporting.

    Returns:
        ActionResult tuple with status "success".

    Raises:
        ActionExecutionError: If collection or CSV output fails.

    """
    groups, dimensions = _report_groups(context)
    collected = _collect_report_values(request, groups, dimensions, log_fn)
    rows = [
        (
            group,
            _compute_stats(
                request["parsed_metrics"],
                collected.values[index],
                collected.argmax[index],
            ),
        )
        for index, group in enumerate(groups)
    ]
    if request["significance"]:
        return _significance_result(request, collected, rows, log_fn)
    _write_summary(request, rows, log_fn)
    metadata = _summarise_metadata(
        request,
        sum(collected.counts),
        collected.sources,
        _report_metadata(rows),
    )
    return ("success", metadata, [])


def _significance_result(
    request: dict[str, Any],
    collected: _ReportValues,
    rows: list[tuple[dict[str, Any], dict[str, Any]]],
    log_fn: Any | None,
) -> ActionResult:
    """Write a significance table and return its result metadata.

    Args:
        request: Summarisation request.
        collected: Collected values and source paths per group.
        rows: Group matrix values and computed metric values.
        log_fn: Logging callback for progress reporting.

    Returns:
        ActionResult tuple with status "success".

    Raises:
        ActionExecutionError: If the table cannot be written.
    """
    test_rows = _significance_rows(request["significance"], rows)
    _write_significance(request, test_rows, log_fn)
    metadata: dict[str, Any] = {
        "source_count": sum(collected.counts),
        "source_caches": sorted(set(collected.sources)),
        "metrics": request["metric_specs"],
        "significance": [dict(result) for _, result in test_rows],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "table_output": str(request["output"]),
    }
    if request["filter"]:
        metadata["filter"] = request["filter"]
    return ("success", metadata, [])


def _report_metadata(
    rows: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """Return the result metadata block for a report run.

    A single-group report records its statistics directly, preserving the
    metadata shape of an ungrouped run. A grouped report records the group
    count instead, because per-group statistics already live in the report
    file and their names would collide as flat metadata keys.

    Args:
        rows: Group matrix values and computed results.

    Returns:
        Result metadata block for the action.

    """
    if len(rows) == 1:
        return dict(rows[0][1])
    return {"groups": len(rows)}


def _summarise_entries(
    request: dict[str, Any],
    context: Any | None,
    log_fn: Any | None,
) -> ActionResult:
    """Summarise pre-scanned entries into a single table row.

    Args:
        request: Summarisation request.
        context: Workflow context holding matrix values.
        log_fn: Logging callback for progress reporting.

    Returns:
        ActionResult tuple with status "success".

    Raises:
        ActionExecutionError: If collection or the output write fails.

    """
    if request["significance"]:
        raise ActionExecutionError(
            "significance requires 'input' cache files and a workflow "
            "matrix"
        )
    if not request["is_aggregation"]:
        raise ActionExecutionError(
            "summarise requires either aggregation entries or "
            "'input' parameter with cache file path(s)"
        )
    values: Values = {}
    argmax: Argmax = {}
    count, sources = _values_from_entries(request, values, argmax, log_fn)
    results = _compute_stats(request["parsed_metrics"], values, argmax)
    metadata = _summarise_metadata(request, count, sources, results)
    matrix_values = _context_matrix(context)
    if _is_csv_output(request["output"]):
        _write_csv(request, matrix_values, results, metadata, log_fn)
    else:
        _write_single_table(request, matrix_values, results, log_fn)
    return ("success", metadata, [])


def _context_matrix(context: Any | None) -> dict[str, Any]:
    """Return the matrix values carried by a workflow context.

    Args:
        context: Workflow context, if any.

    Returns:
        Matrix values, empty when the context carries none.

    """
    if context and hasattr(context, "matrix_values"):
        return context.matrix_values or {}
    return {}


def _summarise_metadata(
    request: dict[str, Any],
    source_count: int,
    sources: list[str],
    results: dict[str, Any],
) -> dict[str, Any]:
    """Build the result metadata for a summarisation.

    Args:
        request: Summarisation request.
        source_count: Number of entries contributing values.
        sources: Source cache paths.
        results: Computed metric values.

    Returns:
        Action metadata describing the summary.

    """
    metadata: dict[str, Any] = {
        "source_count": source_count,
        "source_caches": sorted(set(sources)),
        "metrics": request["metric_specs"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if request["filter"]:
        metadata["filter"] = request["filter"]
    output = request.get("output")
    if output and not _is_csv_output(output):
        metadata["table_output"] = str(output)
    metadata.update(results)
    return metadata
