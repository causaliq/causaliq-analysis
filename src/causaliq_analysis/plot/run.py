"""Entry point for generating a chart from a summarise CSV output.

``run_plot`` stays thin, delegating kind validation, CSV reading,
long-form data shaping, property logging and dispatch to module-level
helpers.
"""

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
    input_csv: str,
    output: str,
    kind: str = "line",
    subplot: str = "",
    group: str = "",
    x: str = "",
    y: str = "",
    properties: Optional[Union[str, List[str]]] = None,
    log_fn: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Generate a chart from a ``summarise`` CSV output.

    The input CSV contains one row per subplot, x value and group
    combination (as produced by the ``summarise`` action). The chart is
    generated using the migrated legacy plotting functions.

    Args:
        input_csv: path of the input CSV file.
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
    _log_start(log_fn, kind, input_csv, output)
    frame = _read_frame(input_csv)
    _require_columns(frame, (subplot, group, x, y))
    data = _build_long_form(frame, subplot, group, x, y)

    props: Dict[str, Any] = parse_properties(properties)
    props["subplot.kind"] = kind
    _log_properties(log_fn, props)
    _ensure_output_dir(output)
    _dispatch(kind, data, props, output)

    return {
        "input": str(input_csv),
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
    input_csv: str,
    output: str,
) -> None:
    """Log the start of a plot run when a log function is provided."""
    if log_fn:
        log_fn(f"Plotting {kind} from {input_csv} to {output}")


def _read_frame(input_csv: str) -> DataFrame:
    """Read the input CSV and normalise its column names."""
    try:
        frame = read_csv(input_csv)
    except FileNotFoundError:
        raise ValueError(f"Input file not found: {input_csv}")
    frame.columns = [str(col).strip() for col in frame.columns]
    return frame


def _require_columns(frame: DataFrame, columns: Tuple[str, ...]) -> None:
    """Raise ValueError when required columns are missing."""
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(
            f"Input CSV missing required column(s): {', '.join(missing)}"
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
