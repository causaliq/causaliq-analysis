"""Unit tests for summarise request parsing and validation."""

import pytest

from causaliq_analysis.workflow_action.actions.summarise.request import (
    _require_tabular_output,
    _summarise_request,
    _validate_columns,
)


# Test the accepted output extensions.
@pytest.mark.parametrize(
    "output",
    ["summary.csv", "summary.tex", "summary.md", "SUMMARY.MARKDOWN"],
)
def test_require_tabular_output_accepts(output: str) -> None:
    """CSV, LaTeX and Markdown paths are accepted."""
    _require_tabular_output({"output": output})


# Test a non-table output extension is rejected.
def test_require_tabular_output_rejects_db() -> None:
    """A cache path is not a table output."""
    with pytest.raises(ValueError, match="must be a .csv, .tex or .md"):
        _require_tabular_output({"output": "summary.db"})


# Test a missing output path is rejected.
def test_require_tabular_output_requires_output() -> None:
    """The output parameter is required."""
    with pytest.raises(ValueError, match="requires 'output'"):
        _require_tabular_output({})


# Test a valid column parameter set passes validation.
def test_validate_columns_accepts_table_parameters() -> None:
    """Metric, headers, formats and footer of one column are accepted."""
    _validate_columns(
        {
            "metric": ["f1.mean"],
            "input": ["a.db"],
            "headers": ["F1"],
            "format": [".3f"],
            "footer": ["mean"],
        }
    )


# Test a header parameter of the wrong type is rejected.
def test_validate_columns_rejects_header_type() -> None:
    """Headers must be a string or a list."""
    with pytest.raises(ValueError, match="expected a string or list"):
        _validate_columns({"metric": ["f1.mean"], "headers": 3})


# Test an unusable format specification is rejected.
def test_validate_columns_rejects_format() -> None:
    """A format specification Python cannot apply is rejected."""
    with pytest.raises(ValueError, match="Invalid format spec"):
        _validate_columns({"metric": ["f1.mean"], "format": ["i3"]})


# Test the request records the parsed columns and presentation values.
def test_summarise_request_fields() -> None:
    """The request carries the columns, sources and presentation values."""
    request = _summarise_request(
        {
            "metric": [
                "f1.mean[1] as bnsl",
                "f1.argmax.seed",
                "bnsl - 1 as gain",
            ],
            "input": ["a.db"],
            "headers": ["F1", "Best", "Delta"],
            "format": [".3f", "d", "+.3f"],
            "footer": ["mean", "", "mean"],
            "output": "summary.md",
        }
    )

    assert request["metric_specs"][0] == "f1.mean[1] as bnsl"
    assert request["parsed_metrics"][0].key == "bnsl"
    assert request["unique_fields"] == ["f1"]
    assert request["argmax_fields"] == ["f1"]
    assert request["qualified_sources"] == {1}
    assert request["headers"] == ["F1", "Best", "Delta"]
    assert request["format"] == [".3f", "d", "+.3f"]
    assert request["footer"] == ["mean", "", "mean"]
    assert request["input_files"] == ["a.db"]
    assert request["is_aggregation"] is False


# Test an absent optional parameter becomes an empty list.
def test_summarise_request_defaults() -> None:
    """Presentation parameters default to empty lists."""
    request = _summarise_request({"metric": "f1.mean", "output": "a.csv"})
    assert request["metric_specs"] == ["f1.mean"]
    assert request["headers"] == []
    assert request["format"] == []
    assert request["footer"] == []
    assert request["qualified_sources"] == set()
