"""Unit tests for summarise presentation columns and formatting."""

from typing import Any

import pytest

from causaliq_analysis.workflow_action.actions.summarise.columns import (
    _parse_column_specs,
)
from causaliq_analysis.workflow_action.actions.summarise.present import (
    TableColumn,
    _align_for_spec,
    _format_cell,
    _table_columns,
)


# Test a missing value is shown as an empty cell.
@pytest.mark.parametrize("value", [None, ""])
def test_format_cell_missing(value: Any) -> None:
    """A missing value formats as an empty cell."""
    assert _format_cell(value, ".3f") == ""


# Test format specifications are applied to the cell value.
@pytest.mark.parametrize(
    "value, spec, expected",
    [
        (0.804, ".3f", "0.804"),
        (0.062, "+.3f", "+0.062"),
        (37.0, ">3d", " 37"),
        ("alarm", "<18s", "alarm             "),
        (37, ">3d", " 37"),
    ],
)
def test_format_cell_applies_spec(
    value: Any,
    spec: str,
    expected: str,
) -> None:
    """Valid specifications render the expected text."""
    assert _format_cell(value, spec) == expected


# Test an unformatted cell shows the plain value.
@pytest.mark.parametrize(
    "value, expected",
    [(0.75, "0.75"), (37.0, "37"), ("asia", "asia")],
)
def test_format_cell_plain(value: Any, expected: str) -> None:
    """Without a format, the cell holds the plain value."""
    assert _format_cell(value, "") == expected


# Test an unusable specification falls back to the plain value.
def test_format_cell_falls_back() -> None:
    """A specification that cannot format the value is ignored."""
    assert _format_cell(37, "<18s") == "37"
    assert _format_cell(37.5, "3d") == "37.5"


# Test the alignment implied by a format specification.
@pytest.mark.parametrize(
    "spec, align",
    [
        (".3f", "right"),
        (">3d", "right"),
        ("3d", "right"),
        ("<18s", "left"),
        ("^10s", "center"),
        ("", "left"),
    ],
)
def test_align_for_spec(spec: str, align: str) -> None:
    """The format type and alignment flag decide the column alignment."""
    assert _align_for_spec(spec) == align


# Test table columns combine dimensions and metric columns.
def test_table_columns_build() -> None:
    """Dimension columns align left; metric columns follow their format."""
    specs = _parse_column_specs(["node_count[1]", "f1.mean[1]"])
    request = {
        "headers": ["Network", "Nodes", "BNSL"],
        "format": ["<18s", ">3d", ".3f"],
    }
    columns = _table_columns(["network"], specs, request)
    assert columns == [
        TableColumn("Network", "left", "<18s"),
        TableColumn("Nodes", "right", ">3d"),
        TableColumn("BNSL", "right", ".3f"),
    ]


# Test columns default to the specification text and no format.
def test_table_columns_defaults() -> None:
    """Without headers or formats the labels are the specifications."""
    specs = _parse_column_specs(["f1.mean"])
    columns = _table_columns([], specs, {})
    assert columns == [TableColumn("f1.mean", "left", "")]


# Test a format list of the wrong length is rejected.
def test_table_columns_format_length() -> None:
    """Formats must have one entry per column."""
    specs = _parse_column_specs(["f1.mean"])
    with pytest.raises(ValueError, match="'format' must have 2 entries"):
        _table_columns(["network"], specs, {"format": [".3f"]})
