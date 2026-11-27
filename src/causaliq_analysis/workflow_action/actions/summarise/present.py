"""Presentation columns shared by the table renderers.

A presentation column pairs the label shown in a header with the format
specification applied to its cells. The format specification is a Python
format-spec string (``.3f``, ``+.3f``, ``>3d``), and its type also decides
the column alignment, so LaTeX and Markdown tables cannot drift apart.

A null format specification hides its column from the rendered table.
Declared headers label only the visible columns, while a hidden column
keeps its default alias or specification text. The hidden column stays in
the model so that CSV output can still name and write every column.
"""

from dataclasses import dataclass, replace
from typing import Any, Sequence

from .columns import ColumnSpec, _default_labels

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
    request: dict[str, Any],
) -> list[TableColumn]:
    """Build the presentation columns of a table.

    A null format specification hides the column from the rendered table.
    Declared headers label only the visible columns; a hidden column keeps
    its default alias or specification text. Hidden columns are retained
    in the result so that CSV output can still name every column, and
    ``_visible_table`` removes them before presentation rendering.

    Attributes:
        dimensions: Grouping dimension names, in matrix order.
        specs: Column specifications in table order.
        request: Summarisation request holding the declared headers and
            format specifications.

    Returns:
        Presentation columns in table order.

    Raises:
        ValueError: If the headers or formats do not match the expected
            column count, or every column would be hidden.

    """
    labels = _default_labels(dimensions, specs)
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
    _apply_headers(columns, request.get("headers") or [])
    return columns


def _table_column(
    label: str,
    format_spec: str | None,
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


def _apply_headers(
    columns: list[TableColumn],
    headers: Sequence[str],
) -> None:
    """Label the visible columns with the declared headers.

    Args:
        columns: Presentation columns in table order, updated in place.
        headers: Declared labels, one per visible column, or empty when
            the default labels are used.

    Raises:
        ValueError: If the headers do not match the visible column count.

    """
    if not headers:
        return
    visible = [
        index for index, column in enumerate(columns) if not column.hidden
    ]
    if len(headers) != len(visible):
        raise ValueError(
            f"'headers' must have {len(visible)} entries (one per "
            f"visible table column), got {len(headers)}"
        )
    for index, header in zip(visible, headers):
        columns[index] = replace(columns[index], label=header)


def _visible_table(
    columns: Sequence[TableColumn],
    keys: Sequence[str],
) -> tuple[list[TableColumn], list[str]]:
    """Return the table columns and keys with hidden columns removed.

    Args:
        columns: Presentation columns in table order.
        keys: Value keys of the columns in table order.

    Returns:
        Tuple of the visible columns and their value keys.

    """
    indices = [
        index for index, column in enumerate(columns) if not column.hidden
    ]
    return (
        [columns[index] for index in indices],
        [keys[index] for index in indices],
    )


def _format_specs(
    count: int,
    declared: Sequence[str | None],
) -> list[str | None]:
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
