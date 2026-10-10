"""The ``summarise`` command."""

import csv
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from causaliq_analysis.cli.common import (
    _flatten_metadata,
    _get_nested_value,
    _print_summary_table,
)
from causaliq_analysis.validation import (
    SUPPORTED_STATS,
    single_value_callback,
)

__all__ = ["summarise_cmd"]


@click.command(name="summarise")
@click.option(
    "--metric",
    "-m",
    "metrics",
    multiple=True,
    required=True,
    help="Metric specification: <field>.<stat> (e.g., f1.mean, shd.sd). "
    "Supported stats: mean, sd, count. Can specify multiple.",
)
@click.option(
    "--input",
    "-i",
    "input_files",
    multiple=True,
    required=True,
    type=click.Path(exists=True),
    help="Input file(s): JSON metrics or workflow cache (.db). "
    "Can specify multiple.",
)
@click.option(
    "--output",
    "-o",
    multiple=True,
    callback=single_value_callback,
    required=True,
    help="Output path: CSV file or '-' for terminal output.",
)
@click.option(
    "--filter",
    "-f",
    "filter_expr",
    multiple=True,
    callback=single_value_callback,
    default=(),
    help="Filter expression to select entries (e.g., 'status == completed').",
)
def summarise_cmd(
    metrics: Tuple[str, ...],
    input_files: Tuple[str, ...],
    output: str,
    filter_expr: Optional[str],
) -> None:
    """
    Summarise numerical metrics across experiments.

    Computes summary statistics (mean, SD, count) for numerical metrics
    extracted from JSON files or workflow cache (.db) entries. Produces
    publication-ready tabular output in CSV format.

    Metric specifications use the format <field>.<statistic>:
    - f1.mean - compute mean of 'f1' values
    - shd.sd - compute standard deviation of 'shd' values
    - precision.count - count non-null 'precision' values

    The field name follows a dotted path convention for nested metadata.
    For workflow caches, metrics are extracted from entry metadata
    (e.g., 'causaliq-analysis.evaluate_graph.f1' becomes 'f1').

    Example:
        causaliq-analysis summarise -m f1.mean -m f1.sd -m shd.mean \\
            -i results.json -o summary.csv

        causaliq-analysis summarise -m precision.mean -m recall.mean \\
            -i cache.db -o metrics_summary.csv

        causaliq-analysis summarise -m f1.mean -i cache.db \\
            -f "network == 'asia'" -o asia_summary.csv

        causaliq-analysis summarise -m f1.mean -m f1.sd -i cache.db -o -
    """
    parsed_metrics = _parse_metric_specs(metrics)
    unique_fields = list(dict.fromkeys(f for f, _ in parsed_metrics))
    all_values = _collect_values(input_files, unique_fields, filter_expr)
    results = _summarise_values(parsed_metrics, all_values)
    _write_summary(results, output)


def _parse_metric_specs(
    metric_specs: Tuple[str, ...],
) -> List[Tuple[str, str]]:
    """Parse metric specifications into (field, stat) pairs.

    Args:
        metric_specs: Metric specifications (e.g. 'f1.mean').

    Returns:
        List of (field, stat) tuples.

    Raises:
        click.ClickException: If a specification is invalid.
    """
    parsed_metrics: List[Tuple[str, str]] = []
    for spec in metric_specs:
        if "." not in spec:
            raise click.ClickException(
                f"Invalid metric spec '{spec}': must be <field>.<stat>"
            )
        parts = spec.rsplit(".", 1)
        field, stat = parts[0], parts[1]
        if stat not in SUPPORTED_STATS:
            raise click.ClickException(
                f"Unknown statistic '{stat}' in '{spec}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_STATS))}"
            )
        parsed_metrics.append((field, stat))
    return parsed_metrics


def _collect_values(
    input_files: Tuple[str, ...],
    unique_fields: List[str],
    filter_expr: Optional[str],
) -> Dict[str, List[float]]:
    """Collect metric values from every input file.

    Args:
        input_files: Input JSON or cache paths.
        unique_fields: Field names to extract.
        filter_expr: Optional filter expression.

    Returns:
        Mapping of field name to collected float values.
    """
    all_values: Dict[str, List[float]] = {field: [] for field in unique_fields}
    for input_path in input_files:
        _collect_from_input(input_path, unique_fields, all_values, filter_expr)
    return all_values


def _collect_from_input(
    input_path: str,
    unique_fields: List[str],
    all_values: Dict[str, List[float]],
    filter_expr: Optional[str],
) -> None:
    """Collect metric values from a single input path.

    Args:
        input_path: Input JSON or cache path.
        unique_fields: Field names to extract.
        all_values: Mapping to append values to.
        filter_expr: Optional filter expression.

    Raises:
        click.ClickException: If the file type is unsupported.
    """
    path_lower = input_path.lower()

    if path_lower.endswith(".db"):
        _collect_from_cache(input_path, unique_fields, all_values, filter_expr)
    elif path_lower.endswith(".json"):
        _collect_from_json(input_path, unique_fields, all_values, filter_expr)
    else:
        raise click.ClickException(
            f"Unsupported file type: {input_path}. " "Use .json or .db files."
        )


def _collect_from_cache(
    input_path: str,
    unique_fields: List[str],
    all_values: Dict[str, List[float]],
    filter_expr: Optional[str],
) -> None:
    """Collect metric values from a workflow cache.

    Args:
        input_path: Cache (.db) path.
        unique_fields: Field names to extract.
        all_values: Mapping to append values to.
        filter_expr: Optional filter expression.

    Raises:
        click.ClickException: If the cache cannot be read.
    """
    try:
        from causaliq_workflow.cache import WorkflowCache
    except ImportError:  # pragma: no cover
        raise click.ClickException(
            "causaliq-workflow required to read .db caches. "
            "Install with: pip install causaliq-workflow"
        )

    try:
        with WorkflowCache(input_path) as cache:
            entries = cache.list_entries()
            resolved_filter, extra_names = _resolve_cache_filter(
                entries, cache, filter_expr
            )
            _fold_cache(
                entries,
                cache,
                resolved_filter,
                extra_names,
                unique_fields,
                all_values,
            )
    except Exception as e:
        raise click.ClickException(f"Failed to read cache '{input_path}': {e}")


def _resolve_cache_filter(
    entries: List[Dict[str, Any]],
    cache: Any,
    filter_expr: Optional[str],
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Pre-resolve random() calls in a cache filter expression.

    Args:
        entries: Cache entry infos to inspect.
        cache: Open workflow cache.
        filter_expr: Filter expression, possibly with random() calls.

    Returns:
        Tuple of (resolved filter expression, extra names).
    """
    if not filter_expr or "random(" not in filter_expr:
        return filter_expr, {}

    from causaliq_core.utils import resolve_random_calls

    metadata = []
    for entry_info in entries:
        flat = _flatten_cache_metadata(cache, entry_info)
        if flat is not None:
            metadata.append(flat)
    return resolve_random_calls(filter_expr, metadata)


def _flatten_cache_metadata(
    cache: Any,
    entry_info: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Flatten one cache entry's metadata for filter resolution.

    Args:
        cache: Open workflow cache.
        entry_info: Entry info from the cache scan.

    Returns:
        Flattened metadata, or None when the entry is missing.
    """
    entry = cache.get(entry_info["matrix_values"])
    if entry is None:
        return None
    return _flatten_metadata(entry.metadata)


def _fold_cache(
    entries: List[Dict[str, Any]],
    cache: Any,
    resolved_filter: Optional[str],
    extra_names: Dict[str, Any],
    unique_fields: List[str],
    all_values: Dict[str, List[float]],
) -> None:
    """Collect metric values from every cache entry.

    Args:
        entries: Cache entry infos to process.
        cache: Open workflow cache.
        resolved_filter: Resolved filter expression.
        extra_names: Extra filter names from random() resolution.
        unique_fields: Field names to extract.
        all_values: Mapping to append values to.
    """
    for entry_info in entries:
        _collect_cache_entry(
            entry_info,
            cache,
            resolved_filter,
            extra_names,
            unique_fields,
            all_values,
        )


def _collect_cache_entry(
    entry_info: Dict[str, Any],
    cache: Any,
    resolved_filter: Optional[str],
    extra_names: Dict[str, Any],
    unique_fields: List[str],
    all_values: Dict[str, List[float]],
) -> None:
    """Collect metric values from a single cache entry.

    Args:
        entry_info: Entry info from the cache scan.
        cache: Open workflow cache.
        resolved_filter: Resolved filter expression.
        extra_names: Extra filter names from random() resolution.
        unique_fields: Field names to extract.
        all_values: Mapping to append values to.
    """
    entry = cache.get(entry_info["matrix_values"])
    if entry is None:  # pragma: no cover
        return

    # Flatten metadata for access
    flat_meta = _flatten_metadata(entry.metadata)

    if not _matches_filter(flat_meta, resolved_filter, extra_names):
        return

    _append_values(flat_meta, unique_fields, all_values)


def _collect_from_json(
    input_path: str,
    unique_fields: List[str],
    all_values: Dict[str, List[float]],
    filter_expr: Optional[str],
) -> None:
    """Collect metric values from a JSON file.

    Args:
        input_path: JSON path.
        unique_fields: Field names to extract.
        all_values: Mapping to append values to.
        filter_expr: Optional filter expression.

    Raises:
        click.ClickException: If the JSON cannot be read.
    """
    try:
        records = _read_json_records(input_path)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON file '{input_path}': {e}")
    except Exception as e:
        raise click.ClickException(f"Failed to read '{input_path}': {e}")

    resolved_filter, extra_names = _resolve_json_filter(records, filter_expr)
    for record in records:
        _collect_record_values(
            record,
            resolved_filter,
            extra_names,
            unique_fields,
            all_values,
        )


def _read_json_records(input_path: str) -> List[Any]:
    """Read a JSON file into a list of records.

    Args:
        input_path: JSON path.

    Returns:
        List of records (a single object is wrapped in a list).

    Raises:
        click.ClickException: If the JSON is not an object or array.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise click.ClickException(
        f"JSON file must contain object or array: {input_path}"
    )


def _resolve_json_filter(
    records: List[Any],
    filter_expr: Optional[str],
) -> Tuple[Optional[str], Dict[str, Any]]:
    """Pre-resolve random() calls in a JSON filter expression.

    Args:
        records: JSON records to inspect.
        filter_expr: Filter expression, possibly with random() calls.

    Returns:
        Tuple of (resolved filter expression, extra names).
    """
    if not filter_expr or "random(" not in filter_expr:
        return filter_expr, {}

    from causaliq_core.utils import resolve_random_calls

    metadata = [_record_search_data(r) for r in records if isinstance(r, dict)]
    return resolve_random_calls(filter_expr, metadata)


def _record_search_data(record: Dict[str, Any]) -> Dict[str, Any]:
    """Return the flattened search data for a JSON record.

    Args:
        record: JSON record.

    Returns:
        Flattened metadata when present, otherwise the record itself.
    """
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        return _flatten_metadata(metadata)
    return record


def _collect_record_values(
    record: Any,
    resolved_filter: Optional[str],
    extra_names: Dict[str, Any],
    unique_fields: List[str],
    all_values: Dict[str, List[float]],
) -> None:
    """Collect metric values from a single JSON record.

    Args:
        record: JSON record.
        resolved_filter: Resolved filter expression.
        extra_names: Extra filter names from random() resolution.
        unique_fields: Field names to extract.
        all_values: Mapping to append values to.
    """
    if not isinstance(record, dict):
        return

    search_data = _record_search_data(record)
    if not _matches_filter(search_data, resolved_filter, extra_names):
        return

    _append_values(search_data, unique_fields, all_values)


def _matches_filter(
    search_data: Dict[str, Any],
    resolved_filter: Optional[str],
    extra_names: Dict[str, Any],
) -> bool:
    """Return True when a record satisfies the resolved filter.

    Args:
        search_data: Flattened data to evaluate.
        resolved_filter: Resolved filter expression.
        extra_names: Extra filter names from random() resolution.

    Returns:
        True when the record should be processed.
    """
    if not resolved_filter:
        return True

    from causaliq_core.utils import evaluate_filter

    try:
        names = {**search_data, **extra_names}
        return bool(evaluate_filter(resolved_filter, names))
    except Exception:
        return False


def _append_values(
    data: Dict[str, Any],
    unique_fields: List[str],
    all_values: Dict[str, List[float]],
) -> None:
    """Append numeric field values from a dict to the collected values.

    Args:
        data: Data to extract values from.
        unique_fields: Field names to extract.
        all_values: Mapping to append values to.
    """
    for field in unique_fields:
        value = _get_nested_value(data, field)
        if value is not None and isinstance(value, (int, float)):
            all_values[field].append(float(value))


def _summarise_values(
    parsed_metrics: List[Tuple[str, str]],
    all_values: Dict[str, List[float]],
) -> Dict[str, Any]:
    """Compute the requested summary statistics.

    Args:
        parsed_metrics: List of (field, stat) tuples.
        all_values: Collected values per field.

    Returns:
        Mapping of '<field>.<stat>' to computed value.
    """
    results: Dict[str, Any] = {}
    for field, stat in parsed_metrics:
        column = f"{field}.{stat}"
        results[column] = _summary_stat(stat, all_values[field])
    return results


def _summary_stat(stat: str, values: List[float]) -> Any:
    """Compute a single summary statistic.

    Args:
        stat: Statistic name ('mean', 'sd' or 'count').
        values: Collected values.

    Returns:
        Computed statistic, or None when unavailable.
    """
    if stat == "count":
        return len(values)
    if stat == "mean":
        return _mean(values)
    if stat == "sd":
        return _stdev(values)
    return None


def _mean(values: List[float]) -> Optional[float]:
    """Return the mean of the values, or None when empty.

    Args:
        values: Collected values.

    Returns:
        Mean value, or None when no values were collected.
    """
    return statistics.mean(values) if values else None


def _stdev(values: List[float]) -> Optional[float]:
    """Return the standard deviation, or None when fewer than two.

    Args:
        values: Collected values.

    Returns:
        Standard deviation, or None when fewer than two values.
    """
    return statistics.stdev(values) if len(values) >= 2 else None


def _write_summary(results: Dict[str, Any], output: str) -> None:
    """Write summary results to the terminal or a CSV file.

    Args:
        results: Mapping of metric name to computed value.
        output: Output path, or '-' for terminal output.
    """
    if output == "-":
        _print_summary_table(results)
    else:
        _write_summary_csv(results, Path(output))


def _write_summary_csv(results: Dict[str, Any], output_path: Path) -> None:
    """Write summary results to a CSV file.

    Args:
        results: Mapping of metric name to computed value.
        output_path: Destination CSV path.

    Raises:
        click.ClickException: If the file cannot be written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            # Header row
            writer.writerow(results.keys())
            # Data row
            writer.writerow(results.values())
        click.echo(f"Summary written to {output_path}")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")
