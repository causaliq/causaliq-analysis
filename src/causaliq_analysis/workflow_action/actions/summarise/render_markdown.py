"""Rendering a summary table as a GitHub-flavoured Markdown table.

The output mirrors the LaTeX renderer: the header row and its alignment
row, the body rows and, when the request declares one, a footer row.
Escaping differs from LaTeX because a pipe separates the cells and a
leading angle bracket would open an HTML tag.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .present import TableColumn, _format_cell

__all__ = ["_markdown_escape", "_markdown_lines"]

# One rendered table row: dimension values and computed column values
_ROW = Tuple[Dict[str, Any], Dict[str, Any]]

_ALIGN_MARKERS = {"left": ":---", "right": "---:", "center": ":---:"}

_ESCAPE_MAP = {
    "\\": r"\\",
    "|": r"\|",
    "<": "&lt;",
    "\n": "<br>",
}


def _markdown_escape(text: str) -> str:
    """Escape text for use in a Markdown table cell.

    Args:
        text: Text to escape.

    Returns:
        Escaped text.

    """
    return "".join(_ESCAPE_MAP.get(character, character) for character in text)


def _markdown_lines(
    columns: Sequence[TableColumn],
    keys: Sequence[str],
    rows: Sequence[_ROW],
    footer: Optional[Sequence[str]],
) -> List[str]:
    """Render a table as the lines of a Markdown table.

    Args:
        columns: Presentation columns in table order.
        keys: Value keys of the columns in table order.
        rows: Dimension values and computed values per body row.
        footer: Display cells of the footer row, or None for no footer.

    Returns:
        Lines of the Markdown table, without trailing newlines.

    """
    lines = [_markdown_row(_labels(columns)), _alignment_row(columns)]
    lines.extend(
        _body_row(columns, keys, group, results) for group, results in rows
    )
    if footer is not None:
        lines.append(_markdown_row(list(footer)))
    return lines


def _labels(columns: Sequence[TableColumn]) -> List[str]:
    """Return the header texts of the columns.

    Args:
        columns: Presentation columns in table order.

    Returns:
        Column labels in table order.

    """
    return [column.label for column in columns]


def _alignment_row(columns: Sequence[TableColumn]) -> str:
    """Return the alignment row of the table.

    Args:
        columns: Presentation columns in table order.

    Returns:
        Alignment row line.

    """
    markers = [_ALIGN_MARKERS.get(column.align, ":---") for column in columns]
    return "| " + " | ".join(markers) + " |"


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
        Markdown row line.

    """
    merged = {**group, **results}
    cells = [
        _format_cell(merged.get(key, ""), column.format_spec)
        for column, key in zip(columns, keys)
    ]
    return _markdown_row(cells)


def _markdown_row(cells: Sequence[str]) -> str:
    """Render one row of escaped cells.

    Args:
        cells: Cell texts in table order.

    Returns:
        Markdown row line.

    """
    return "| " + " | ".join(_markdown_escape(cell) for cell in cells) + " |"
