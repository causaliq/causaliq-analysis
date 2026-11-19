"""Rendering significance test results as a table.

The significance table has four columns: the comparison label, the test
statistic, its p-value and the significance stars. ``headers`` and
``format`` apply exactly as they do to a metric table, so a caller can
rename the columns, format the statistic and p-value, or hide a column.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from causaliq_analysis.workflow_action.types import ActionExecutionError

from .present import (
    TableColumn,
    _apply_headers,
    _format_specs,
    _require_visible,
    _table_column,
    _visible_table,
)
from .render import _is_csv_output, _output_file
from .render_csv import _write_report
from .render_latex import _latex_lines
from .render_markdown import _markdown_lines
from .significance import (
    SignificanceSpec,
    _default_caption,
    _statistic_format,
    _statistic_label,
)

__all__ = ["_write_significance"]

# One rendered table row: grouping values and computed column values
_ROW = Tuple[Dict[str, Any], Dict[str, Any]]

# Value keys of the standard significance columns
_KEYS = ["comparison", "statistic", "p_value", "significance"]

# Value keys of the detailed paired-comparison columns
_DETAIL_KEYS = [
    "comparison",
    "wins",
    "losses",
    "mean_delta",
    "statistic",
    "p_value",
]

# Output extensions rendered as a Markdown table
_MARKDOWN_SUFFIXES = (".md", ".markdown")


def _write_significance(
    request: Dict[str, Any],
    rows: Sequence[_ROW],
    log_fn: Any,
) -> None:
    """Write the significance table named by the output path.

    Args:
        request: Summarisation request holding the output path, headers,
            format, caption and parsed significance specifications.
        rows: Significance result rows.
        log_fn: Logging callback for progress reporting.

    Raises:
        ActionExecutionError: If the table cannot be written.
    """
    if _is_csv_output(request["output"]):
        _write_report(
            request,
            list(rows),
            log_fn,
            _csv_labels(request),
            _table_keys(request),
        )
        return
    out_file = _output_file(request)
    lines = _significance_lines(out_file.suffix.lower(), request, rows)
    try:
        out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        raise ActionExecutionError(
            f"Failed to write significance table: {e}"
        ) from e
    if log_fn:
        log_fn(f"Significance table written to {out_file}")


def _significance_lines(
    suffix: str,
    request: Dict[str, Any],
    rows: Sequence[_ROW],
) -> List[str]:
    """Render the significance table as lines of a presentation format.

    Args:
        suffix: Output file extension, including the leading dot.
        request: Summarisation request.
        rows: Significance result rows.

    Returns:
        Lines of the table, without trailing newlines.
    """
    columns = _columns(request)
    visible, keys = _visible_table(columns, _table_keys(request))
    if suffix in _MARKDOWN_SUFFIXES:
        table = _markdown_lines(visible, keys, rows, None)
    else:
        table = _latex_lines(visible, keys, rows, None)
    return _caption_lines(suffix, request) + table


def _columns(request: Dict[str, Any]) -> List[TableColumn]:
    """Build the four presentation columns of a significance table.

    Args:
        request: Summarisation request.

    Returns:
        Presentation columns in table order.

    Raises:
        ValueError: If the headers or formats do not match the column
            count, or every column would be hidden.
    """
    specs: Sequence[SignificanceSpec] = request["significance"]
    detail = _is_detail(request)
    labels = (
        [
            "Comparison",
            "Wins",
            "Losses",
            "Mean delta",
            _statistic_label(specs),
            "p",
        ]
        if detail
        else [
            "Comparison",
            _statistic_label(specs),
            "p",
            "Significance",
        ]
    )
    formats = _declared_formats(request, specs)
    columns = [
        _table_column(label, format_spec, measure=True)
        for label, format_spec in zip(labels, formats)
    ]
    _require_visible(columns)
    _apply_headers(columns, request.get("headers") or [])
    return columns


def _is_detail(request: Dict[str, Any]) -> bool:
    """Return whether the detailed comparison columns are requested."""
    return bool(request.get("significance_detail"))


def _table_keys(request: Dict[str, Any]) -> List[str]:
    """Return the value keys of the significance table."""
    return list(_DETAIL_KEYS if _is_detail(request) else _KEYS)


def _declared_formats(
    request: Dict[str, Any],
    specs: Sequence[SignificanceSpec],
) -> List[Optional[str]]:
    """Return the format specification of every significance column.

    Args:
        request: Summarisation request.
        specs: Parsed significance specifications.

    Returns:
        One format specification per declared column.

    Raises:
        ValueError: If the declared formats do not match the column count.
    """
    declared = request.get("format") or []
    if declared:
        return _format_specs(len(_table_keys(request)), declared)
    if _is_detail(request):
        return ["", "d", "d", "+.3f", _statistic_format(specs), ".4f"]
    return ["", _statistic_format(specs), ".4f", ""]


def _csv_labels(request: Dict[str, Any]) -> List[str]:
    """Return the CSV labels, including hidden columns.

    Args:
        request: Summarisation request.

    Returns:
        Column labels in table order.
    """
    return [column.label for column in _columns(request)]


def _caption_lines(
    suffix: str,
    request: Dict[str, Any],
) -> List[str]:
    """Return the caption lines of a significance table.

    Args:
        suffix: Output file extension, including the leading dot.
        request: Summarisation request.

    Returns:
        Caption lines, or an empty list when the caption is suppressed.
    """
    specs: Sequence[SignificanceSpec] = request["significance"]
    declared = request.get("caption")
    caption = _default_caption(specs) if declared is None else str(declared)
    if not caption:
        return []
    if suffix in _MARKDOWN_SUFFIXES:
        return [f"## {caption}", ""]
    return [f"% {caption}"]
