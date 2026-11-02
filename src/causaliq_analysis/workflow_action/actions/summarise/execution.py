"""Running one summarisation: collect, compute, render."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from causaliq_analysis.workflow_action.types import ActionResult

from .collect import _collect_values
from .render_csv import _write_csv
from .stats import _compute_stats

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
    """Summarise the requested metrics and append the CSV row.

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
    matrix_values = _context_matrix(context)
    values, sources, count = _collect_values(request, matrix_values, log_fn)
    results = _compute_stats(request["parsed_metrics"], values)
    metadata = _summarise_metadata(request, count, sources, results)
    _write_csv(request, matrix_values, results, metadata, log_fn)
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
    metadata.update(results)
    return metadata
