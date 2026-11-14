"""Writing a summary table in the format named by the output path.

The output extension selects the renderer: ``.csv`` writes the raw table,
``.tex`` writes a LaTeX ``tabular`` fragment and ``.md`` or ``.markdown``
writes a Markdown table. Only the presentation formats apply the
``format`` and ``footer`` parameters; CSV output keeps raw values so that
a ``plot`` step can read the file numerically. A null ``format`` entry
hides its column from the presentation output, but the column remains in
the CSV output.
"""

from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from causaliq_analysis.workflow_action.types import ActionExecutionError

from .columns import _table_labels
from .footer import _footer_cells
from .present import _table_columns, _visible_table
from .render_csv import _write_report
from .render_latex import _latex_lines
from .render_markdown import _markdown_lines

__all__ = [
    "_is_csv_output",
    "_render_table",
    "_write_single_table",
    "_write_summary",
]

# One rendered table row: dimension values and computed column values
_ROW = Tuple[Dict[str, Any], Dict[str, Any]]

# Output extensions rendered as a Markdown table
_MARKDOWN_SUFFIXES = (".md", ".markdown")


def _is_csv_output(output: Any) -> bool:
    """Return True when the output path names a CSV file.

    Args:
        output: Output path of the summarisation.

    Returns:
        True for a ``.csv`` path.

    """
    return str(output).lower().endswith(".csv")


def _write_summary(
    request: Dict[str, Any],
    rows: Sequence[_ROW],
    log_fn: Any,
) -> None:
    """Write the complete table in the format named by the output path.

    Args:
        request: Summarisation request.
        rows: Dimension values and computed values per body row.
        log_fn: Logging callback for progress reporting.

    Raises:
        ActionExecutionError: If the table cannot be written.

    """
    if _is_csv_output(request["output"]):
        _write_report(request, list(rows), log_fn, _labels_for(request, rows))
        return
    _write_presentation(request, rows, log_fn)


def _labels_for(
    request: Dict[str, Any],
    rows: Sequence[_ROW],
) -> List[str]:
    """Return the column labels of a table.

    Args:
        request: Summarisation request.
        rows: Dimension values and computed values per body row.

    Returns:
        Column labels, in column order.

    """
    dimensions = list(rows[0][0]) if rows else []
    return _table_labels(
        dimensions,
        request["parsed_metrics"],
        request.get("headers") or [],
    )


def _write_single_table(
    request: Dict[str, Any],
    group: Dict[str, Any],
    results: Dict[str, Any],
    log_fn: Any,
) -> None:
    """Write a one-row table in a presentation format.

    Args:
        request: Summarisation request.
        group: Dimension values of the row.
        results: Computed column values of the row.
        log_fn: Logging callback for progress reporting.

    Raises:
        ActionExecutionError: If the table cannot be written.

    """
    _write_presentation(request, [(group, results)], log_fn)


def _write_presentation(
    request: Dict[str, Any],
    rows: Sequence[_ROW],
    log_fn: Any,
) -> None:
    """Write a table in the format named by the output path.

    Args:
        request: Summarisation request.
        rows: Dimension values and computed values per body row.
        log_fn: Logging callback for progress reporting.

    Raises:
        ActionExecutionError: If the table cannot be written.

    """
    out_file = _output_file(request)
    lines = _render_table(out_file.suffix.lower(), request, rows)
    try:
        out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        raise ActionExecutionError(f"Failed to write table output: {e}") from e
    if log_fn:
        log_fn(f"Summary written to {out_file}")


def _output_file(request: Dict[str, Any]) -> Path:
    """Return the output file, creating its parent directory.

    Args:
        request: Summarisation request.

    Returns:
        Output file path.

    """
    output_path = request["output"]
    assert output_path is not None  # Validated by the action validator
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    return out_file


def _render_table(
    suffix: str,
    request: Dict[str, Any],
    rows: Sequence[_ROW],
) -> List[str]:
    """Render a table as the lines of a presentation format.

    Args:
        suffix: Output file extension, including the leading dot.
        request: Summarisation request.
        rows: Dimension values and computed values per body row.

    Returns:
        Lines of the table, without trailing newlines.

    """
    dimensions = list(rows[0][0]) if rows else []
    specs = request["parsed_metrics"]
    columns = _table_columns(dimensions, specs, request)
    keys = dimensions + [spec.key for spec in specs]
    footer = _footer_cells(request.get("footer"), columns, keys, rows)
    columns, keys, footer = _visible_table(columns, keys, footer)
    if suffix in _MARKDOWN_SUFFIXES:
        return _markdown_lines(columns, keys, rows, footer)
    return _latex_lines(columns, keys, rows, footer)
