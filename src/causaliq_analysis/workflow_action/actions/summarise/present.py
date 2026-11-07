"""Presentation columns shared by the table renderers.

A presentation column pairs the label shown in a header with the format
specification applied to its cells. The format specification is a Python
format-spec string (``.3f``, ``+.3f``, ``>3d``), and its type also decides
the column alignment, so LaTeX and Markdown tables cannot drift apart.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence

from .columns import ColumnSpec, _table_labels

__all__ = [
    "TableColumn",
    "_align_for_spec",
    "_format_cell",
    "_table_columns",
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

    """

    label: str
    align: str
    format_spec: str


def _table_columns(
    dimensions: Sequence[str],
    specs: Sequence[ColumnSpec],
    request: Dict[str, Any],
) -> List[TableColumn]:
    """Build the presentation columns of a table.

    Attributes:
        dimensions: Grouping dimension names, in matrix order.
        specs: Column specifications in table order.
        request: Summarisation request holding the declared headers and
            format specifications.

    Returns:
        Presentation columns in table order.

    Raises:
        ValueError: If the headers or formats do not match the table's
            column count.

    """
    labels = _table_labels(dimensions, specs, request.get("headers") or [])
    formats = _format_specs(len(labels), request.get("format") or [])
    columns = [
        TableColumn(labels[index], "left", formats[index])
        for index in range(len(dimensions))
    ]
    for offset in range(len(specs)):
        index = len(dimensions) + offset
        columns.append(
            TableColumn(
                labels[index],
                _align_for_spec(formats[index]),
                formats[index],
            )
        )
    return columns


def _format_specs(count: int, declared: Sequence[str]) -> List[str]:
    """Return one format specification per table column.

    Args:
        count: Number of table columns.
        declared: Declared format specifications, empty when unformatted.

    Returns:
        One format specification per column, empty when unformatted.

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
