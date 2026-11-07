"""Unit tests for summarise derived-column formulas."""

import pytest

from causaliq_analysis.workflow_action.actions.summarise.formula import (
    _evaluate_formula,
    _validate_formula,
)
from causaliq_analysis.workflow_action.types import ActionExecutionError

_VALUES = {"bnsl": 0.804, "llm": 0.653, "fusion": 0.866}


# Test the worked example computes fusion minus the best baseline.
def test_best_of_formula() -> None:
    """Fusion minus the best baseline is 0.062 for the sample values."""
    result = _evaluate_formula("fusion - max(bnsl, llm)", _VALUES)
    assert result == pytest.approx(0.062)


# Test the supported operators, literals and functions.
@pytest.mark.parametrize(
    "formula, expected",
    [
        ("bnsl + llm", 1.457),
        ("fusion * 2", 1.732),
        ("fusion / bnsl", 1.0771144278606965),
        ("min(bnsl, llm, fusion)", 0.653),
        ("abs(llm - fusion)", 0.213),
        ("round(fusion, 2)", 0.87),
        ("round(fusion)", 1.0),
        ("-fusion", -0.866),
        ("+fusion", 0.866),
        ("fusion - 1", -0.134),
        ("2 * 3", 6.0),
    ],
)
def test_formula_values(formula: str, expected: float) -> None:
    """Each supported construct computes its numeric value."""
    assert _evaluate_formula(formula, _VALUES) == pytest.approx(expected)


# Test a formula over an empty column yields an empty cell.
@pytest.mark.parametrize(
    "formula",
    ["bnsl - llm", "abs(bnsl)", "round(bnsl, 2)", "-bnsl", "bnsl + 1"],
)
def test_empty_value_propagates(formula: str) -> None:
    """An empty operand makes the derived cell empty."""
    assert _evaluate_formula(formula, {"bnsl": "", "llm": 0.5}) == ""


# Test min and max ignore empty columns.
def test_extremes_ignore_empty() -> None:
    """min and max summarise the columns that hold a value."""
    values = {"bnsl": "", "llm": 0.5}
    assert _evaluate_formula("max(bnsl, llm)", values) == pytest.approx(0.5)
    assert _evaluate_formula("min(bnsl, llm)", values) == pytest.approx(0.5)


# Test min and max over only empty columns are empty.
def test_extremes_all_empty() -> None:
    """min and max with no numeric column report an empty cell."""
    values = {"bnsl": "", "llm": ""}
    assert _evaluate_formula("max(bnsl, llm)", values) == ""
    assert _evaluate_formula("min(bnsl, llm)", values) == ""


# Test division by zero yields an empty cell.
def test_division_by_zero() -> None:
    """A zero divisor reports an empty cell rather than failing."""
    assert _evaluate_formula("bnsl / llm", {"bnsl": 1.0, "llm": 0.0}) == ""


# Test a non-numeric column is treated as empty.
def test_non_numeric_column_is_empty() -> None:
    """A text value contributes no number to a formula."""
    assert _evaluate_formula("bnsl + 1", {"bnsl": "n/a"}) == ""


# Test a column without a value fails at evaluation.
def test_missing_value_reported() -> None:
    """An alias without a value is reported as an action error."""
    with pytest.raises(ActionExecutionError, match="unknown column 'llm'"):
        _evaluate_formula("bnsl - llm", {"bnsl": 1.0})


# Test invalid formulas are rejected with a clear message.
@pytest.mark.parametrize(
    "formula, message",
    [
        ("bnsl -", "Invalid formula"),
        ("bnsl == llm", "Unsupported element"),
        ("'a'", "Unsupported literal"),
        ("True", "Unsupported literal"),
        ("power(bnsl, 2)", "Unknown formula function 'power'"),
        ("max(bnsl=1)", "positional"),
        ("max.foo(bnsl)", "positional"),
        ("abs()", "at least 1 argument"),
        ("abs(bnsl, llm)", "at most 1 argument"),
        ("round(bnsl, llm)", "whole number of digits"),
        ("round(bnsl, -1)", "whole number of digits"),
    ],
)
def test_invalid_formulas(formula: str, message: str) -> None:
    """Unsupported constructs are rejected with a clear message."""
    with pytest.raises(ValueError, match=message):
        _validate_formula(formula)


# Test a formula may only reference earlier column aliases.
def test_unknown_alias_at_validation() -> None:
    """A name that is not an earlier alias is rejected."""
    with pytest.raises(ValueError, match="not an alias of an earlier"):
        _validate_formula("fusion - best", {"fusion"})


# Test a valid formula passes validation against its aliases.
def test_valid_formula_passes() -> None:
    """The worked example validates against the aliases it uses."""
    _validate_formula("fusion - max(bnsl, llm)", {"bnsl", "llm", "fusion"})
