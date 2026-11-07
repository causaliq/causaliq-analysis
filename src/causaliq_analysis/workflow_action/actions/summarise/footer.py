"""Footer rows for the presentation table renderers.

A footer entry is a blank cell, a statistic name computed over the
column's row values, or literal text. A derived column is summarised from
its computed cells, which is what a reader expects from an average row:
the footer of a difference column is the mean of the differences, not the
difference of the means.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from causaliq_analysis.validation import SUPPORTED_STATS
from causaliq_analysis.workflow_action.types import ActionExecutionError

from .present import TableColumn, _format_cell
from .stats import _stat_value

__all__ = ["_footer_cells"]

# One rendered table row: dimension values and computed column values
_ROW = Tuple[Dict[str, Any], Dict[str, Any]]


def _footer_cells(
    specs: Optional[Sequence[str]],
    columns: Sequence[TableColumn],
    keys: Sequence[str],
    rows: Sequence[_ROW],
) -> Optional[List[str]]:
    """Build the display cells of the footer row.

    Args:
        specs: Declared footer entries, or None for no footer.
        columns: Presentation columns in table order.
        keys: Value keys of the columns in table order.
        rows: Dimension values and computed values per body row.

    Returns:
        One display cell per column, or None when the request declares no
        footer.

    Raises:
        ActionExecutionError: If the footer does not match the table's
            column count.

    """
    if not specs:
        return None
    if len(specs) != len(columns):
        raise ActionExecutionError(
            f"'footer' must have {len(columns)} entries (one per table "
            f"column), got {len(specs)}"
        )
    return [
        _footer_cell(specs[index], columns[index], keys[index], rows)
        for index in range(len(columns))
    ]


def _footer_cell(
    spec: str,
    column: TableColumn,
    key: str,
    rows: Sequence[_ROW],
) -> str:
    """Return the display text of one footer cell.

    Args:
        spec: Declared footer entry: blank, a statistic name or text.
        column: Presentation column of the cell.
        key: Value key of the column.
        rows: Dimension values and computed values per body row.

    Returns:
        Display text of the footer cell.

    """
    if spec == "":
        return ""
    if spec not in SUPPORTED_STATS:
        return spec
    values = _column_values(key, rows)
    return _format_cell(_stat_value(spec, values), column.format_spec)


def _column_values(key: str, rows: Sequence[_ROW]) -> List[float]:
    """Return the numeric values of one column across the body rows.

    Args:
        key: Value key of the column.
        rows: Dimension values and computed values per body row.

    Returns:
        Numeric values in body order, omitting missing cells.

    """
    values: List[float] = []
    for group, results in rows:
        value = {**group, **results}.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values.append(float(value))
    return values
