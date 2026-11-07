"""Rendering a summary table as a LaTeX ``tabular`` fragment.

The fragment holds the header row, a rule, the body rows and, when the
request declares one, a rule and a footer row, so a paper can
``\\input`` the file inside its own ``table`` float. Header and footer
text is escaped, because a table header commonly holds characters that
are LaTeX markup (``_``, ``%``, ``>``).
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .present import TableColumn, _format_cell

__all__ = ["_latex_escape", "_latex_lines"]

# One rendered table row: dimension values and computed column values
_ROW = Tuple[Dict[str, Any], Dict[str, Any]]

_ALIGN_CODES = {"left": "l", "right": "r", "center": "c"}

_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "<": r"\textless{}",
    ">": r"\textgreater{}",
}


def _latex_escape(text: str) -> str:
    """Escape text for use in a LaTeX table cell.

    Args:
        text: Text to escape.

    Returns:
        Escaped text.

    """
    return "".join(_ESCAPE_MAP.get(character, character) for character in text)


def _latex_lines(
    columns: Sequence[TableColumn],
    keys: Sequence[str],
    rows: Sequence[_ROW],
    footer: Optional[Sequence[str]],
) -> List[str]:
    """Render a table as the lines of a LaTeX ``tabular`` fragment.

    Args:
        columns: Presentation columns in table order.
        keys: Value keys of the columns in table order.
        rows: Dimension values and computed values per body row.
        footer: Display cells of the footer row, or None for no footer.

    Returns:
        Lines of the tabular fragment, without trailing newlines.

    """
    lines = [_latex_begin(columns), _latex_row(_labels(columns))]
    lines.append(r"\hline")
    lines.extend(
        _body_row(columns, keys, group, results) for group, results in rows
    )
    if footer is not None:
        lines.append(r"\hline")
        lines.append(_latex_row(list(footer)))
    lines.append(r"\end{tabular}")
    return lines


def _latex_begin(columns: Sequence[TableColumn]) -> str:
    """Return the tabular environment opening line.

    Args:
        columns: Presentation columns in table order.

    Returns:
        ``\\begin{tabular}`` line with one alignment code per column.

    """
    alignment = "".join(
        _ALIGN_CODES.get(column.align, "l") for column in columns
    )
    return f"\\begin{{tabular}}{{{alignment}}}"


def _labels(columns: Sequence[TableColumn]) -> List[str]:
    """Return the header texts of the columns.

    Args:
        columns: Presentation columns in table order.

    Returns:
        Column labels in table order.

    """
    return [column.label for column in columns]


def _body_row(
    columns: Sequence[TableColumn],
    keys: Sequence[str],
    group: Dict[str, Any],
    results: Dict[str, Any],
) -> str:
    """Render one body row.

    Args:
        columns: Presentation columns in table order.
        keys: Value keys of the columns in table order.
        group: Dimension values of the row.
        results: Computed column values of the row.

    Returns:
        LaTeX row line.

    """
    merged = {**group, **results}
    cells = [
        _format_cell(merged.get(key, ""), column.format_spec)
        for column, key in zip(columns, keys)
    ]
    return _latex_row(cells)


def _latex_row(cells: Sequence[str]) -> str:
    """Render one row of escaped cells.

    Args:
        cells: Cell texts in table order.

    Returns:
        LaTeX row line, terminated by the row-break command.

    """
    return " & ".join(_latex_escape(cell) for cell in cells) + r" \\"
