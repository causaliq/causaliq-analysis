"""
Summarise workflow action.

Aggregates numerical metrics from cache entries into summary statistics
(mean, standard deviation, count) and writes them to a CSV file. The action
is stateless, so validation and execution delegate to module-level helpers
and each step stays within the module and method limits.
"""

import csv
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.validation import (
    SUPPORTED_STATS,
    validate_filter_expression,
    validate_metric_specs,
)
from causaliq_analysis.workflow_action import helpers
from causaliq_analysis.workflow_action.actions.base import AnalysisAction
from causaliq_analysis.workflow_action.types import (
    ActionExecutionError,
    ActionPattern,
    ActionResult,
)

__all__ = ["SummariseAction"]


class SummariseAction(AnalysisAction):
    """Summarise metric values from cache entries into CSV output.

    Attributes:
        action_name: Action name as used in workflow definitions.
        pattern: Workflow action pattern used for cache validation.

    """

    action_name = "summarise"
    pattern = ActionPattern.AGGREGATE

    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate summarise parameters before execution.

        Args:
            parameters: Action parameter values.

        Raises:
            ValueError: If a parameter is missing or invalid. The provider
                converts this to an ActionValidationError.

        """
        validate_metric_specs(parameters.get("metric", []))
        validate_filter_expression(parameters.get("filter"))
        _require_csv_output(parameters)

    def run(
        self,
        parameters: Dict[str, Any],
        mode: str,
        context: Optional[Any] = None,
        logger: Optional[Any] = None,
    ) -> ActionResult:
        """Execute metric summarisation to a CSV file.

        Aggregation mode summarises the pre-scanned cache entries passed
        via '_aggregation_entries' per matrix combination; direct mode
        reads entries from the 'input' cache files and produces a single
        summary row.

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
            request = _summarise_request(parameters)
            if mode == "dry-run":
                return _dry_run_result(request, logger)
            return _summarise(request, context, logger)
        except ActionExecutionError:
            raise
        except Exception as e:
            raise ActionExecutionError(f"Summarise failed: {e}") from e


def _require_csv_output(parameters: Dict[str, Any]) -> None:
    """Require a CSV output path.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If no output path is given, or it is not a CSV file.

    """
    output_path = parameters.get("output")
    if output_path is None:
        raise ValueError(
            "summarise requires 'output' parameter with .csv file path."
        )
    if not str(output_path).lower().endswith(".csv"):
        raise ValueError(
            "summarise output must be a CSV file (.csv). "
            f"Got: {output_path}"
        )


def _summarise_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the summarisation request from action parameters.

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding metric specs, filter, output path and inputs.

    """
    metric_specs = parameters.get("metric", [])
    if isinstance(metric_specs, str):
        metric_specs = [metric_specs]
    if not metric_specs:  # pragma: no cover
        raise ActionExecutionError(
            "summarise requires 'metric' parameter with at least one "
            "metric specification (e.g., ['f1.mean', 'shd.sd'])"
        )
    parsed_metrics = _parse_metric_specs(metric_specs)
    return {
        "metric_specs": metric_specs,
        "parsed_metrics": parsed_metrics,
        "unique_fields": list(dict.fromkeys(f for f, _ in parsed_metrics)),
        "filter": parameters.get("filter"),
        "output": parameters.get("output"),
        "input_files": _input_files(parameters),
        "aggregation_entries": parameters.get("_aggregation_entries"),
        "is_aggregation": parameters.get("_aggregation_entries") is not None,
    }


def _input_files(parameters: Dict[str, Any]) -> List[str]:
    """Return the input cache paths as a list.

    Args:
        parameters: Action parameter values.

    Returns:
        Input paths, empty when none are provided.

    """
    input_raw = parameters.get("input", []) or []
    return [input_raw] if isinstance(input_raw, str) else list(input_raw)


def _parse_metric_specs(metric_specs: List[str]) -> List[Tuple[str, str]]:
    """Parse '<field>.<stat>' metric specifications.

    Args:
        metric_specs: Metric specifications to parse.

    Returns:
        List of (field, stat) tuples.

    Raises:
        ActionExecutionError: If a specification is invalid.

    """
    parsed: List[Tuple[str, str]] = []
    for spec in metric_specs:
        parsed.append(_parse_one_spec(spec))
    return parsed


def _parse_one_spec(spec: str) -> Tuple[str, str]:
    """Parse a single metric specification.

    Args:
        spec: Metric specification (e.g. 'f1.mean').

    Returns:
        Tuple of (field, stat).

    Raises:
        ActionExecutionError: If the specification is invalid.

    """
    if "," in spec:  # pragma: no cover
        raise ActionExecutionError(
            f"Invalid metric spec '{spec}': contains comma. "
            "Use YAML list syntax: metric: [f1.mean, shd.sd]"
        )
    if "." not in spec:  # pragma: no cover
        raise ActionExecutionError(
            f"Invalid metric spec '{spec}': must be <field>.<stat>"
        )
    field, stat = spec.rsplit(".", 1)
    if stat not in SUPPORTED_STATS:  # pragma: no cover
        raise ActionExecutionError(
            f"Unknown statistic '{stat}' in '{spec}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_STATS))}"
        )
    return field, stat


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


def _collect_values(
    request: Dict[str, Any],
    matrix_values: Dict[str, Any],
    log_fn: Optional[Any],
) -> Tuple[Dict[str, List[float]], List[str], int]:
    """Collect metric values from aggregation entries or cache files.

    Args:
        request: Summarisation request.
        matrix_values: Matrix values from the workflow context.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (values per field, source caches, source entry count).

    Raises:
        ActionExecutionError: If the input specification is invalid.

    """
    values: Dict[str, List[float]] = {
        field: [] for field in request["unique_fields"]
    }
    if request["is_aggregation"]:
        count, sources = _values_from_entries(request, values, log_fn)
    else:
        count, sources = _values_from_files(
            request, values, matrix_values, log_fn
        )
    if log_fn:
        log_fn(f"Collected values from {count} entries")
    return values, sources, count


def _values_from_entries(
    request: Dict[str, Any],
    values: Dict[str, List[float]],
    log_fn: Optional[Any],
) -> Tuple[int, List[str]]:
    """Collect metric values from pre-scanned cache entries.

    Args:
        request: Summarisation request.
        values: Values per field, updated in place.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (source entry count, source cache paths).

    """
    entries = request["aggregation_entries"] or []
    resolved, extra_names = _resolve_filter(request["filter"], entries)
    sources: List[str] = []
    count = 0
    for entry_dict in entries:
        matrix_values, flat_meta = _entry_metadata(entry_dict)
        sources.append(entry_dict.get("cache_path", "unknown"))
        if not _entry_matches(resolved, flat_meta, extra_names):
            continue
        count += 1
        _accumulate_values(values, flat_meta, request["unique_fields"])
        _log_entry(log_fn, matrix_values)
    return count, sources


def _entry_metadata(entry_dict: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
    """Return the matrix values and flattened metadata of an entry.

    Args:
        entry_dict: Pre-scanned cache entry descriptor.

    Returns:
        Tuple of (matrix values, flattened metadata).

    """
    matrix_values = entry_dict.get("matrix_values", {})
    flat_meta = helpers._flatten_entry_metadata(
        matrix_values, entry_dict.get("metadata", {})
    )
    return matrix_values, flat_meta


def _log_entry(log_fn: Optional[Any], matrix_values: Any) -> None:
    """Log a processed cache entry.

    Args:
        log_fn: Logging callback for progress reporting.
        matrix_values: Matrix values of the processed entry.

    """
    if log_fn:
        log_fn(f"Processed entry: {matrix_values}")


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
    from causaliq_core.utils import evaluate_filter

    try:
        names = {**flat_meta, **extra_names}
        return bool(evaluate_filter(resolved_filter, names))
    except Exception:
        return False


def _accumulate_values(
    values: Dict[str, List[float]],
    flat_meta: Dict[str, Any],
    unique_fields: List[str],
) -> None:
    """Append numeric metric values from one entry.

    Args:
        values: Values per field, updated in place.
        flat_meta: Flattened metadata of the entry.
        unique_fields: Fields to collect values for.

    """
    for field in unique_fields:
        value = helpers._get_nested_value(flat_meta, field)
        if value is not None and isinstance(value, (int, float)):
            values[field].append(float(value))


def _values_from_files(
    request: Dict[str, Any],
    values: Dict[str, List[float]],
    matrix_values: Dict[str, Any],
    log_fn: Optional[Any],
) -> Tuple[int, List[str]]:
    """Collect metric values from input workflow cache files.

    Args:
        request: Summarisation request.
        values: Values per field, updated in place.
        matrix_values: Matrix values from the workflow context.
        log_fn: Logging callback for progress reporting.

    Returns:
        Tuple of (source entry count, source cache paths).

    Raises:
        ActionExecutionError: If no input file, or a non-cache, is given.

    """
    input_files = _require_input_files(request["input_files"])
    sources: List[str] = []
    count = 0
    for cache_path in input_files:
        _require_cache_file(cache_path)
        sources.append(cache_path)
        count += helpers._collect_values_from_cache(
            cache_path,
            request["unique_fields"],
            values,
            request["filter"],
            matrix_values,
            log_fn,
        )
    return count, sources


def _require_input_files(input_files: List[str]) -> List[str]:
    """Require at least one input cache file.

    Args:
        input_files: Input paths from the action parameters.

    Returns:
        The input paths.

    Raises:
        ActionExecutionError: If no input path is provided.

    """
    if not input_files:
        raise ActionExecutionError(
            "summarise requires either aggregation entries or "
            "'input' parameter with cache file path(s)"
        )
    return input_files


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


def _compute_stats(
    parsed_metrics: List[Tuple[str, str]],
    values: Dict[str, List[float]],
) -> Dict[str, Any]:
    """Compute the summary statistics for each metric specification.

    Args:
        parsed_metrics: Parsed (field, stat) specifications.
        values: Collected values per field.

    Returns:
        Mapping of '<field>.<stat>' column names to computed values.

    """
    results: Dict[str, Any] = {}
    for field, stat in parsed_metrics:
        results[f"{field}.{stat}"] = _stat_value(stat, values[field])
    return results


def _stat_value(stat: str, values: List[float]) -> Any:
    """Compute a single summary statistic.

    Args:
        stat: Statistic name ('mean', 'sd' or 'count').
        values: Collected values for the field.

    Returns:
        Computed statistic, or an empty string when unavailable.

    """
    if stat == "count":
        return len(values)
    if stat == "mean":
        return statistics.mean(values) if values else ""
    if len(values) >= 2:
        return statistics.stdev(values)
    return ""


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


def _write_csv(
    request: Dict[str, Any],
    matrix_values: Dict[str, Any],
    results: Dict[str, Any],
    metadata: Dict[str, Any],
    log_fn: Optional[Any],
) -> None:
    """Append the summary row to the CSV output file.

    Args:
        request: Summarisation request.
        matrix_values: Matrix values from the workflow context.
        results: Computed metric values.
        metadata: Result metadata, updated with the output path.
        log_fn: Logging callback for progress reporting.

    Raises:
        ActionExecutionError: If the CSV file cannot be written.

    """
    output_path = request["output"]
    assert output_path is not None  # Validated by the action validator
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    row_data = _csv_row(matrix_values, results)
    try:
        file_exists = out_file.exists()
        _append_row(out_file, row_data, file_exists)
        verb = "appended to" if file_exists else "written to"
        metadata["csv_output"] = str(out_file)
        if log_fn:
            log_fn(f"Summary {verb} {out_file}")
    except Exception as e:
        raise ActionExecutionError(f"Failed to write CSV output: {e}") from e


def _csv_row(
    matrix_values: Dict[str, Any],
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the CSV row holding matrix values then metrics.

    Args:
        matrix_values: Matrix values from the workflow context.
        results: Computed metric values.

    Returns:
        Row mapping column names to values.

    """
    row_data: Dict[str, Any] = {}
    for key, value in matrix_values.items():
        row_data[key] = value
    row_data.update(results)
    return row_data


def _append_row(
    out_file: Path,
    row_data: Dict[str, Any],
    file_exists: bool,
) -> None:
    """Write a summary row, creating the header when needed.

    Args:
        out_file: CSV file to write to.
        row_data: Row mapping column names to values.
        file_exists: Whether the file already holds a header row.

    """
    mode = "a" if file_exists else "w"
    with open(out_file, mode, encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if not file_exists:
            writer.writerow(row_data.keys())
        writer.writerow(row_data.values())
