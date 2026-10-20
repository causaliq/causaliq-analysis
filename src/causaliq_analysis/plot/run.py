"""Entry point for generating a chart from workflow results.

``run_plot`` stays thin, delegating kind validation, input reading (a
``summarise`` CSV or a metrics workflow cache), long-form data shaping,
property logging and dispatch to module-level helpers.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pandas import DataFrame, read_csv, to_numeric

from causaliq_analysis.plot.charts import (
    SUPPORTED_KINDS,
    plot_scatter,
    relplot,
)
from causaliq_analysis.plot.properties import parse_properties

__all__ = ["run_plot"]


def run_plot(
    input_path: str,
    output: str,
    kind: str = "line",
    subplot: str = "",
    group: str = "",
    x: str = "",
    y: str = "",
    properties: Optional[Union[str, List[str]]] = None,
    log_fn: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Generate a chart from summarise output or a metrics cache.

    The input is either a ``summarise`` CSV (one row per subplot, x value
    and group combination) or a metrics workflow cache (``.db``) whose
    entries carry a ``metrics`` object. The chart is generated using the
    migrated legacy plotting functions.

    Args:
        input_path: path of the input CSV file or metrics cache.
        output: path of the output chart file (e.g. ``.png`` or ``.jpg``).
        kind: type of plot required, e.g. ``line`` or ``bar``.
        subplot: column name defining the subplot.
        group: column name defining the groups shown in the legend.
        x: column name providing the x-axis values.
        y: column name providing the y-axis values.
        properties: list of chart property strings in
            ``<name>=<value>`` format with Python literal values.
        log_fn: optional callback used to log progress messages.

    Returns:
        Dictionary of metadata describing the chart generated.

    Raises:
        ValueError: If the kind, columns or input file are invalid.
    """
    _validate_kind(kind)
    _log_start(log_fn, kind, input_path, output)
    frame = _load_frame(input_path)
    _require_columns(frame, (subplot, group, x, y))
    data = _build_long_form(frame, subplot, group, x, y)

    props: Dict[str, Any] = parse_properties(properties)
    props["subplot.kind"] = kind
    _log_properties(log_fn, props)
    _ensure_output_dir(output)
    _dispatch(kind, data, props, output)

    return {
        "input": str(input_path),
        "output": str(output),
        "type": kind,
        "columns": {"subplot": subplot, "group": group, "x": x, "y": y},
    }


def _validate_kind(kind: str) -> None:
    """Raise ValueError when the requested kind is unsupported."""
    if kind not in SUPPORTED_KINDS:
        raise ValueError(
            f"Unknown plot type '{kind}'. Supported types are: "
            f"{', '.join(sorted(SUPPORTED_KINDS))}"
        )


def _log_start(
    log_fn: Optional[Callable[[str], None]],
    kind: str,
    input_path: str,
    output: str,
) -> None:
    """Log the start of a plot run when a log function is provided."""
    if log_fn:
        log_fn(f"Plotting {kind} from {input_path} to {output}")


def _load_frame(input_path: str) -> DataFrame:
    """Load the input frame from a CSV file or a metrics cache."""
    if str(input_path).lower().endswith(".db"):
        return _read_metrics_frame(input_path)
    return _read_csv_frame(input_path)


def _read_csv_frame(input_csv: str) -> DataFrame:
    """Read the input CSV and normalise its column names."""
    try:
        frame = read_csv(input_csv)
    except FileNotFoundError:
        raise ValueError(f"Input file not found: {input_csv}")
    frame.columns = [str(col).strip() for col in frame.columns]
    return frame


def _read_metrics_frame(cache_path: str) -> DataFrame:
    """Read a metrics workflow cache into a one-row-per-entry frame.

    Each row combines the entry's matrix values with the metric values
    stored in its ``metrics`` object, so the plotted columns are the
    matrix keys plus the metric names.
    """
    rows = _metrics_rows(cache_path)
    if not rows:
        raise ValueError(f"No metric entries found in cache: {cache_path}")
    return DataFrame(rows)


def _metrics_rows(cache_path: str) -> List[Dict[str, Any]]:
    """Build the flat metric rows held by a metrics workflow cache."""
    from causaliq_workflow.cache import WorkflowCache

    with WorkflowCache(cache_path) as cache:
        return _read_cache_rows(cache)


def _read_cache_rows(cache: Any) -> List[Dict[str, Any]]:
    """Read the metric rows from an open workflow cache."""
    from causaliq_workflow.cache.reporting import build_entry_view

    rows: List[Dict[str, Any]] = []
    for entry_info in cache.list_entries():
        matrix_values = entry_info.get("matrix_values", {})
        entry = cache.get(matrix_values)
        metrics = _entry_metrics(entry)
        if metrics is None:
            continue
        rows.append(build_entry_view(matrix_values, entry.metadata, metrics))
    return rows


def _entry_metrics(entry: Any) -> Optional[Dict[str, Any]]:
    """Return the metric values of a cache entry, or None.

    Entries with no ``metrics`` object, or with the empty placeholder
    object written for a failed run, contribute no metric values.
    """
    if entry is None:
        return None
    metrics = entry.get_object("metrics")
    if metrics is None or metrics.is_empty:
        return None
    parsed = json.loads(metrics.content)
    if not isinstance(parsed, dict):
        return None
    return parsed


def _require_columns(frame: DataFrame, columns: Tuple[str, ...]) -> None:
    """Raise ValueError when required columns are missing."""
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(
            f"Input missing required column(s): {', '.join(missing)}"
        )


def _build_long_form(
    frame: DataFrame, subplot: str, group: str, x: str, y: str
) -> DataFrame:
    """Build the long-form data required by the plotting functions."""
    return DataFrame(
        {
            "subplot": frame[subplot].astype(str).str.strip(),
            "x_val": frame[x],
            "y_var": frame[group].astype(str).str.strip(),
            "y_val": to_numeric(frame[y], errors="coerce"),
        }
    )


def _log_properties(
    log_fn: Optional[Callable[[str], None]], props: Dict[str, Any]
) -> None:
    """Log the parsed properties in sorted order when requested."""
    if log_fn:
        for p in sorted(props):
            log_fn("{} = {}".format(p, props[p]))


def _ensure_output_dir(output: str) -> None:
    """Create the output directory when it does not already exist."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)


def _dispatch(
    kind: str, data: DataFrame, props: Dict[str, Any], output: str
) -> None:
    """Dispatch to the scatter or relational chart builder."""
    if kind == "scatter":
        plot_scatter(data, props, output)
    else:
        relplot(data, props, output)
