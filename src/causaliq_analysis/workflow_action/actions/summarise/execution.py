"""Running one summarisation: collect, compute, render."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionResult,
)

from .collect import _values_from_entries
from .groups import _report_groups
from .render import _is_csv_output, _write_single_table, _write_summary
from .render_csv import _write_csv
from .report import _collect_report_values
from .stats import Argmax, Values, _compute_stats

__all__ = [
    "_dry_run_result",
    "_summarise",
]


def _dry_run_result(
    request: Dict[str, Any],
    logger: Optional[Any],
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
        },
        [],
    )


def _print_dry_run(request: Dict[str, Any]) -> None:
    """Print the dry-run message for the active summarisation mode.

    Args:
        request: Summarisation request.

    """
    if request["is_aggregation"]:
        entry_count = len(request["aggregation_entries"] or [])
        print(f"Would summarise metrics from {entry_count} entries")
    else:
        print("Would summarise metrics from input files")


def _log_fn(logger: Optional[Any]) -> Optional[Any]:
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
    request: Dict[str, Any],
    context: Optional[Any],
    logger: Optional[Any],
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
    if request["input_files"]:
        return _summarise_report(request, context, log_fn)
    return _summarise_entries(request, context, log_fn)


def _summarise_report(
    request: Dict[str, Any],
    context: Optional[Any],
    log_fn: Optional[Any],
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
    _write_summary(request, rows, log_fn)
    metadata = _summarise_metadata(
        request,
        sum(collected.counts),
        collected.sources,
        _report_metadata(rows),
    )
    return ("success", metadata, [])


def _report_metadata(
    rows: List[Tuple[Dict[str, Any], Dict[str, Any]]],
) -> Dict[str, Any]:
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
    request: Dict[str, Any],
    context: Optional[Any],
    log_fn: Optional[Any],
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


def _context_matrix(context: Optional[Any]) -> Dict[str, Any]:
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
    request: Dict[str, Any],
    source_count: int,
    sources: List[str],
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the result metadata for a summarisation.

    Args:
        request: Summarisation request.
        source_count: Number of entries contributing values.
        sources: Source cache paths.
        results: Computed metric values.

    Returns:
        Action metadata describing the summary.

    """
    metadata: Dict[str, Any] = {
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
