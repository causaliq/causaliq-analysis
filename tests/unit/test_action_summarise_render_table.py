"""Unit tests for the summarise table renderers and dispatch."""

from typing import Any, Dict, List, Tuple

import pytest

from causaliq_analysis.workflow_action.actions.summarise import (
    render_latex,
    render_markdown,
)
from causaliq_analysis.workflow_action.actions.summarise.columns import (
    _parse_column_specs,
)
from causaliq_analysis.workflow_action.actions.summarise.footer import (
    _footer_cells,
)
from causaliq_analysis.workflow_action.actions.summarise.present import (
    _table_columns,
)
from causaliq_analysis.workflow_action.actions.summarise.render import (
    _is_csv_output,
    _render_table,
    _write_single_table,
    _write_summary,
)
from causaliq_analysis.workflow_action.types import ActionExecutionError

_ROW = Tuple[Dict[str, Any], Dict[str, Any]]

_KEYS = ["network", "f1.mean[1]", "f1.mean[2]"]


def _request(**overrides: Any) -> Dict[str, Any]:
    """Build a presentation request over two metrics."""
    request: Dict[str, Any] = {
        "parsed_metrics": _parse_column_specs(["f1.mean[1]", "f1.mean[2]"]),
        "headers": ["Network", "BNSL", "LLM"],
        "format": ["", ".3f", "+.3f"],
        "footer": ["AVERAGE", "mean", "mean"],
        "output": None,
    }
    request.update(overrides)
    return request


def _rows() -> List[_ROW]:
    """Build two body rows for the renderers."""
    return [
        ({"network": "alarm"}, {"f1.mean[1]": 0.804, "f1.mean[2]": 0.653}),
        ({"network": "asia"}, {"f1.mean[1]": 0.75, "f1.mean[2]": 0.843}),
    ]


def _columns(request: Dict[str, Any]) -> List[Any]:
    """Build the presentation columns of a request."""
    return _table_columns(["network"], request["parsed_metrics"], request)


# Test the output extension identifies a CSV path.
@pytest.mark.parametrize(
    "output, expected",
    [("a.csv", True), ("A.CSV", True), ("a.md", False), ("a.tex", False)],
)
def test_is_csv_output(output: str, expected: bool) -> None:
    """Only a .csv path is a CSV output."""
    assert _is_csv_output(output) is expected


# Test the Markdown table holds a header, alignment and body rows.
def test_markdown_table_lines() -> None:
    """The Markdown renderer emits pipes, alignment and a footer."""
    lines = _render_table(".md", _request(), _rows())
    assert lines[0] == "| Network | BNSL | LLM |"
    assert lines[1] == "| :--- | ---: | ---: |"
    assert lines[2] == "| alarm | 0.804 | +0.653 |"
    assert lines[-1] == "| AVERAGE | 0.777 | +0.748 |"


# Test the LaTeX table is a tabular fragment with rules.
def test_latex_table_lines() -> None:
    """The LaTeX renderer emits a tabular, rules and a footer."""
    lines = _render_table(".tex", _request(), _rows())
    assert lines[0] == r"\begin{tabular}{lrr}"
    assert lines[1] == r"Network & BNSL & LLM \\"
    assert lines[2] == r"\hline"
    assert lines[3] == r"alarm & 0.804 & +0.653 \\"
    assert lines[-3] == r"\hline"
    assert lines[-2] == r"AVERAGE & 0.777 & +0.748 \\"
    assert lines[-1] == r"\end{tabular}"


# Test LaTeX markup in a header is escaped.
def test_latex_escapes_header() -> None:
    """A header holding markup characters is escaped."""
    request = _request(headers=["Network", "F1_best", "F>best"])
    lines = _render_table(".tex", request, _rows())
    assert r"F1\_best" in lines[1]
    assert r"F\textgreater{}best" in lines[1]


# Test a pipe in a Markdown cell is escaped.
def test_markdown_escapes_pipe() -> None:
    """A pipe inside a cell does not split the row."""
    request = _request(headers=["Network", "a|b", "LLM"])
    lines = _render_table(".md", request, _rows())
    assert "a\\|b" in lines[0]


# Test a footer statistic is computed over the column's row values.
def test_footer_statistic() -> None:
    """A statistic footer cell summarises the column."""
    footer = ["AVERAGE", "mean", "count"]
    cells = _footer_cells(footer, _columns(_request()), _KEYS, _rows())
    assert cells is not None
    assert cells[0] == "AVERAGE"
    assert cells[1] == "0.777"
    assert cells[2] == "+2.000"


# Test a footer that does not match the table is rejected.
def test_footer_length_mismatch() -> None:
    """A footer must have one entry per column."""
    with pytest.raises(ActionExecutionError, match="must have 3 entries"):
        _footer_cells(["AVERAGE"], _columns(_request()), _KEYS, _rows())


# Test no footer is rendered when none is declared.
def test_footer_absent() -> None:
    """An empty footer parameter produces no footer row."""
    assert _footer_cells([], _columns(_request()), _KEYS, _rows()) is None


# Test a blank footer cell stays blank.
def test_footer_blank_cell() -> None:
    """An empty footer entry renders an empty cell."""
    cells = _footer_cells(["", "", ""], _columns(_request()), _KEYS, _rows())
    assert cells == ["", "", ""]


# Test a footer over text values reports an empty cell for statistics.
def test_footer_text_column() -> None:
    """A statistic over a text column has no value to report."""
    footer = ["mean", "mean", "mean"]
    cells = _footer_cells(footer, _columns(_request()), _KEYS, _rows())
    assert cells is not None
    assert cells[0] == ""


# Test the Markdown renderer omits the footer rule.
def test_markdown_without_footer() -> None:
    """Without a footer the Markdown table ends with the last body row."""
    request = _request(footer=[])
    rows = _rows()
    lines = render_markdown._markdown_lines(
        _columns(request), _KEYS, rows, None
    )
    assert lines[-1] == "| asia | 0.750 | +0.843 |"


# Test the LaTeX renderer closes the tabular without a footer.
def test_latex_without_footer() -> None:
    """Without a footer the tabular closes after the last body row."""
    request = _request(footer=[])
    rows = _rows()
    lines = render_latex._latex_lines(_columns(request), _KEYS, rows, None)
    assert lines[-2] == r"asia & 0.750 & +0.843 \\"
    assert lines[-1] == r"\end{tabular}"


# Test a CSV output is delegated to the CSV report writer.
def test_write_summary_csv(tmp_path: Any) -> None:
    """A .csv output writes raw values through the CSV renderer."""
    output = tmp_path / "summary.csv"
    _write_summary(_request(output=str(output)), _rows(), None)
    first = output.read_text(encoding="utf-8").splitlines()[0]
    assert first == "Network,BNSL,LLM"


# Test a Markdown output is written to the file.
def test_write_summary_markdown(tmp_path: Any) -> None:
    """A .md output writes the Markdown table."""
    output = tmp_path / "summary.md"
    _write_summary(_request(output=str(output)), _rows(), None)
    text = output.read_text(encoding="utf-8")
    assert text.startswith("| Network | BNSL | LLM |")
    assert text.endswith("| AVERAGE | 0.777 | +0.748 |\n")


# Test a `.markdown` output uses the Markdown renderer.
def test_write_summary_markdown_long_suffix(tmp_path: Any) -> None:
    """A .markdown output writes a Markdown table."""
    output = tmp_path / "summary.markdown"
    _write_summary(_request(output=str(output)), _rows(), None)
    assert output.read_text(encoding="utf-8").startswith("| Network")


# Test a single-row table is written for the entries mode.
def test_write_single_table(tmp_path: Any) -> None:
    """A one-row table is written without a grouping dimension."""
    output = tmp_path / "summary.md"
    request = _request(output=str(output), headers=[], format=[], footer=[])
    results = {"f1.mean[1]": 0.9}
    _write_single_table(request, {"network": "asia"}, results, None)
    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "| network | f1.mean[1] | f1.mean[2] |"
    assert lines[2] == "| asia | 0.9 |  |"


# Test a write failure is reported as an action error.
def test_write_summary_reports_failure(tmp_path: Any) -> None:
    """An unwritable destination raises ActionExecutionError."""
    with pytest.raises(ActionExecutionError, match="Failed to write table"):
        _write_summary(_request(output=str(tmp_path)), _rows(), None)


# Test the renderer logs the file it wrote.
def test_write_summary_logs(tmp_path: Any) -> None:
    """A successful write reports the output path."""
    messages: List[str] = []
    output = tmp_path / "summary.md"
    _write_summary(_request(output=str(output)), _rows(), messages.append)
    assert messages == [f"Summary written to {output}"]
