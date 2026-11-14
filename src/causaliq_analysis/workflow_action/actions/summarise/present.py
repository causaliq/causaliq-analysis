"""Presentation columns shared by the table renderers.

A presentation column pairs the label shown in a header with the format
specification applied to its cells. The format specification is a Python
format-spec string (``.3f``, ``+.3f``, ``>3d``), and its type also decides
the column alignment, so LaTeX and Markdown tables cannot drift apart.

A null format specification hides its column from the rendered table. The
hidden column stays in the presentation model so that the declared
headers, footer cells and value keys remain aligned with the full table.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .columns import ColumnSpec, _table_labels

__all__ = [
    "TableColumn",
    "_align_for_spec",
    "_format_cell",
    "_table_columns",
    "_visible_table",
]

# Format-spec type characters that denote a numeric column
_NUMERIC_TYPES = frozenset("dfeEgG%")


@dataclass(frozen=True)
class TableColumn:
    """One rendered column of a summarise table.

    Attributes:
        label: Header text.
        align: Cell alignment: 'left', 'right' or 'center'.
        format_spec: Python format-spec string, empty when unformatted.
        hidden: Whether the column is omitted from the rendered table.

    """

    label: str
    align: str
    format_spec: str
    hidden: bool = False


def _table_columns(
    dimensions: Sequence[str],
    specs: Sequence[ColumnSpec],
    request: Dict[str, Any],
) -> List[TableColumn]:
    """Build the presentation columns of a table.

    A null format specification hides the column from the rendered table.
    Hidden columns are retained in the result so that the declared
    headers, footer cells and value keys stay aligned with the full
    column order; ``_visible_table`` removes them before rendering.

    Attributes:
        dimensions: Grouping dimension names, in matrix order.
        specs: Column specifications in table order.
        request: Summarisation request holding the declared headers and
            format specifications.

    Returns:
        Presentation columns in table order.

    Raises:
        ValueError: If the headers or formats do not match the table's
            column count, or every column would be hidden.

    """
    labels = _table_labels(dimensions, specs, request.get("headers") or [])
    formats = _format_specs(len(labels), request.get("format") or [])
    count = len(dimensions)
    columns = [
        _table_column(labels[index], formats[index], measure=False)
        for index in range(count)
    ]
    columns.extend(
        _table_column(labels[count + offset], formats[count + offset], True)
        for offset in range(len(specs))
    )
    _require_visible(columns)
    return columns


def _table_column(
    label: str,
    format_spec: Optional[str],
    measure: bool,
) -> TableColumn:
    """Build one presentation column.

    Args:
        label: Header text of the column.
        format_spec: Python format-spec string, or None to hide the column.
        measure: Whether the column is a metric column; metric columns take
            their alignment from the format specification, while grouping
            dimensions align left.

    Returns:
        Presentation column for the label and format.

    """
    if format_spec is None:
        return TableColumn(label, "left", "", hidden=True)
    align = _align_for_spec(format_spec) if measure else "left"
    return TableColumn(label, align, format_spec)


def _require_visible(columns: Sequence[TableColumn]) -> None:
    """Require at least one column to remain visible.

    Args:
        columns: Presentation columns in table order.

    Raises:
        ValueError: If every column is hidden.

    """
    if columns and all(column.hidden for column in columns):
        raise ValueError("'format' must leave at least one visible column")


def _visible_table(
    columns: Sequence[TableColumn],
    keys: Sequence[str],
    footer: Optional[Sequence[str]],
) -> Tuple[List[TableColumn], List[str], Optional[List[str]]]:
    """Return the table with its hidden columns removed.

    Args:
        columns: Presentation columns in table order.
        keys: Value keys of the columns in table order.
        footer: Display cells of the footer row, or None for no footer.

    Returns:
        Tuple of the visible columns, their value keys and the matching
        footer cells. A missing footer stays None.

    """
    indices = [
        index for index, column in enumerate(columns) if not column.hidden
    ]
    visible_columns = [columns[index] for index in indices]
    visible_keys = [keys[index] for index in indices]
    visible_footer = (
        None if footer is None else [footer[index] for index in indices]
    )
    return visible_columns, visible_keys, visible_footer


def _format_specs(
    count: int,
    declared: Sequence[Optional[str]],
) -> List[Optional[str]]:
    """Return one format specification per table column.

    Args:
        count: Number of table columns.
        declared: Declared format specifications, empty when unformatted.
            A null entry hides its column.

    Returns:
        One format specification per column, empty when unformatted and
        null when the column is hidden.

    Raises:
        ValueError: If the formats do not match the column count.

    """
    if not declared:
        return [""] * count
    if len(declared) != count:
        raise ValueError(
            f"'format' must have {count} entries (one per table column), "
            f"got {len(declared)}"
        )
    return list(declared)


def _align_for_spec(format_spec: str) -> str:
    """Return the alignment implied by a format specification.

    Args:
        format_spec: Python format-spec string.

    Returns:
        'left', 'right' or 'center'.

    """
    if "<" in format_spec:
        return "left"
    if "^" in format_spec:
        return "center"
    if ">" in format_spec or format_spec[-1:] in _NUMERIC_TYPES:
        return "right"
    return "left"


def _format_cell(value: Any, format_spec: str) -> str:
    """Format one cell for display.

    Args:
        value: Cell value; an empty string or None denotes a missing value.
        format_spec: Python format-spec string, empty when unformatted.

    Returns:
        Display text for the cell, empty for a missing value.

    """
    if value is None or value == "":
        return ""
    if not format_spec:
        return _plain_text(value)
    try:
        return format(_coerce_value(value, format_spec), format_spec)
    except (TypeError, ValueError):
        return _plain_text(value)


def _coerce_value(value: Any, format_spec: str) -> Any:
    """Coerce an integral float to int for an integer format.

    Args:
        value: Cell value to format.
        format_spec: Python format-spec string.

    Returns:
        Value suitable for the format specification.

    """
    if format_spec.endswith("d") and isinstance(value, float):
        if value.is_integer():
            return int(value)
    return value


def _plain_text(value: Any) -> str:
    """Return the unformatted display text of a value.

    Args:
        value: Cell value.

    Returns:
        Text for the value, with integral floats shown as integers.

    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
