"""Unit tests for the summarise significance engine."""

import warnings
from typing import Any

import pytest
from scipy.stats import wilcoxon

from causaliq_analysis.workflow_action.actions.summarise import (
    significance_specs,
)
from causaliq_analysis.workflow_action.actions.summarise.significance import (
    SIGNIFICANCE_TESTS,
    SignificanceSpec,
    _default_caption,
    _numeric_value,
    _paired_summary,
    _paired_values,
    _significance_row,
    _significance_rows,
    _significance_stars,
    _statistic_format,
    _statistic_label,
)

_Row = tuple[dict[str, Any], dict[str, Any]]


def _specs(*specs: str) -> list[SignificanceSpec]:
    """Parse significance specifications over a small alias set."""
    return significance_specs._parse_significance_specs(
        list(specs),
        {"fusion", "bnsl", "llm"},
    )


def _test() -> Any:
    """Return the registered Wilcoxon test."""
    return SIGNIFICANCE_TESTS["wilcoxon-signed-rank-2-sided"]


# Test the registered test matches SciPy's paired Wilcoxon result.
def test_wilcoxon_matches_scipy() -> None:
    """The paired test returns SciPy's W statistic and p-value."""
    left = [0.9, 0.8, 0.7, 0.6]
    right = [0.5, 0.6, 0.4, 0.6]
    result = _test().run(left, right)
    # SciPy 1.13 falls back to the asymptotic method for small samples;
    # compare against its own result rather than a fixed p-value.
    expected = wilcoxon(
        [first - second for first, second in zip(left, right)],
        alternative="two-sided",
    )
    assert result is not None
    assert result == pytest.approx((expected.statistic, expected.pvalue))


# Test a one-sample call tests the values against zero.
def test_wilcoxon_one_sample() -> None:
    """A one-sample test matches SciPy on the sample itself."""
    values = [0.4, 0.3, 0.4, 0.3]
    result = _test().run(values, None)
    expected = wilcoxon(values)
    assert result == pytest.approx((expected.statistic, expected.pvalue))


# Test too few non-zero differences cannot produce a test.
def test_wilcoxon_too_few_differences() -> None:
    """Identical samples report no result."""
    assert _test().run([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]) is None


# Test zero differences are dropped from the paired test.
def test_wilcoxon_drops_zero_differences() -> None:
    """A zero difference matches SciPy's default handling."""
    left = [0.5, 0.6, 0.7, 0.8]
    right = [0.5, 0.4, 0.6, 0.7]
    result = _test().run(left, right)
    differences = [first - second for first, second in zip(left, right)]
    # Use the actual floating-point differences so ties are handled the
    # same way as the implementation, whichever SciPy method is selected.
    expected = wilcoxon(differences)
    assert result == pytest.approx((expected.statistic, expected.pvalue))


# Test the significance star thresholds.
@pytest.mark.parametrize(
    "p_value, expected",
    [
        (0.0009, "***"),
        (0.001, "**"),
        (0.009, "**"),
        (0.01, "*"),
        (0.049, "*"),
        (0.05, ""),
        (None, ""),
    ],
)
def test_significance_stars(
    p_value: float | None,
    expected: str,
) -> None:
    """Stars follow the conventional p-value thresholds."""
    assert _significance_stars(p_value) == expected


# Test numeric conversion rejects missing and non-numeric cells.
@pytest.mark.parametrize(
    "value, expected",
    [
        (None, None),
        (True, None),
        ("", None),
        ("not-a-number", None),
        (1, 1.0),
        (0.5, 0.5),
    ],
)
def test_numeric_value(value: Any, expected: float | None) -> None:
    """Only numbers survive the cell conversion."""
    assert _numeric_value(value) == expected


# Test pairing skips rows missing either sample.
def test_paired_values_skips_missing_rows() -> None:
    """A row missing one sample contributes no pair."""
    spec = _specs("wilcoxon-signed-rank-2-sided(fusion, bnsl)")[0]
    rows: list[_Row] = [
        ({"network": "alarm"}, {"fusion": 0.9, "bnsl": 0.5}),
        ({"network": "asia"}, {"fusion": 0.8}),
        ({"network": "sports"}, {"fusion": 0.7, "bnsl": 0.4}),
        ({"network": "water"}, {"bnsl": 0.3}),
    ]
    left, right = _paired_values(spec, rows)
    assert left == [0.9, 0.7]
    assert right == [0.5, 0.4]


# Test a one-sample specification pairs every available value.
def test_paired_values_one_sample() -> None:
    """A one-sample test returns no right-hand sample."""
    spec = _specs("wilcoxon-signed-rank-2-sided(fusion, bnsl)")[0]
    single = SignificanceSpec(
        text=spec.text,
        test=spec.test,
        left="fusion",
        right=None,
        label="fusion vs 0",
    )
    rows: list[_Row] = [
        ({"network": "alarm"}, {"fusion": 0.9, "bnsl": 0.5}),
        ({"network": "asia"}, {"fusion": 0.8, "bnsl": 0.6}),
    ]
    left, right = _paired_values(single, rows)
    assert left == [0.9, 0.8]
    assert right is None


# Test a result row holds the label, statistic, p-value and stars.
def test_significance_row() -> None:
    """A result row reports the paired test of two aliases."""
    spec = _specs(
        "wilcoxon-signed-rank-2-sided(fusion, bnsl) as Fusion vs BNSL"
    )[0]
    rows: list[_Row] = [
        ({"network": "alarm"}, {"fusion": 0.9, "bnsl": 0.5}),
        ({"network": "asia"}, {"fusion": 0.8, "bnsl": 0.6}),
        ({"network": "sports"}, {"fusion": 0.7, "bnsl": 0.4}),
        ({"network": "water"}, {"fusion": 0.6, "bnsl": 0.6}),
    ]
    result = _significance_row(spec, rows)
    expected = wilcoxon([0.9 - 0.5, 0.8 - 0.6, 0.7 - 0.4, 0.6 - 0.6])
    assert result["comparison"] == "Fusion vs BNSL"
    assert result["statistic"] == pytest.approx(expected.statistic)
    assert result["p_value"] == pytest.approx(expected.pvalue)
    assert result["significance"] == ""


# Test one result row is produced per declared test.
def test_significance_rows() -> None:
    """The table holds one row per test in declaration order."""
    specs = _specs(
        "wilcoxon-signed-rank-2-sided(fusion, bnsl) as first",
        "wilcoxon-signed-rank-2-sided(fusion, llm) as second",
    )
    rows: list[_Row] = [
        ({"network": "alarm"}, {"fusion": 0.9, "bnsl": 0.5, "llm": 0.4}),
        ({"network": "asia"}, {"fusion": 0.8, "bnsl": 0.6, "llm": 0.5}),
    ]
    result = _significance_rows(specs, rows)
    assert [row[1]["comparison"] for row in result] == ["first", "second"]
    assert all(group == {} for group, _ in result)


# Test the default caption names the shared test.
def test_default_caption() -> None:
    """The caption matches the research heading."""
    specs = _specs("wilcoxon-signed-rank-2-sided(fusion, bnsl)")
    assert _default_caption(specs) == (
        "STATISTICAL TESTS (Wilcoxon signed-rank, two-sided)"
    )


# Test the statistic label and format come from the test metadata.
def test_statistic_label_and_format() -> None:
    """The result table uses the test's statistic symbol and format."""
    specs = _specs("wilcoxon-signed-rank-2-sided(fusion, bnsl)")
    assert _statistic_label(specs) == "W"
    assert _statistic_format(specs) == ".1f"


# Test the registry exposes the full test metadata.
def test_registry_metadata() -> None:
    """The registered test carries its name, title, arity and callable."""
    test = _test()
    assert test.name == "wilcoxon-signed-rank-2-sided"
    assert test.title == "Wilcoxon signed-rank, two-sided"
    assert test.statistic_label == "W"
    assert test.arity == 2
    assert callable(test.run)


# Test the Spearman test and detailed paired summary.
def test_spearman_and_paired_summary() -> None:
    """Spearman matches SciPy and the summary counts wins and losses."""
    test = SIGNIFICANCE_TESTS["spearman-2-sided"]
    left = [0.1, 0.4, 0.35, 0.8, 0.9]
    right = [0.2, 0.3, 0.5, 0.7, 1.0]
    result = test.run(left, right)
    from scipy.stats import spearmanr

    expected = spearmanr(left, right)
    assert result == pytest.approx((expected.statistic, expected.pvalue))

    spec = _specs("wilcoxon-signed-rank-2-sided(fusion, bnsl) as comparison")[
        0
    ]
    rows: list[_Row] = [
        ({"network": "a"}, {"fusion": 0.9, "bnsl": 0.5}),
        ({"network": "b"}, {"fusion": 0.4, "bnsl": 0.6}),
        ({"network": "c"}, {"fusion": 0.7, "bnsl": 0.7}),
    ]
    row = _significance_row(spec, rows)
    assert row["wins"] == 1
    assert row["losses"] == 1
    assert row["mean_delta"] == pytest.approx((0.4 - 0.2 + 0.0) / 3)


# Test the paired summary empty and one-sample branches.
def test_paired_summary_empty_and_one_sample() -> None:
    """Empty samples and one-sample summaries are handled."""
    assert _paired_summary([], None) == ("", "", "")
    assert _paired_summary([1.0, -1.0], None) == (1, 1, 0.0)


# Test Spearman refuses samples that cannot produce a correlation.
def test_spearman_requires_enough_values() -> None:
    """Short or missing samples and constant ranks report no result."""
    test = SIGNIFICANCE_TESTS["spearman-2-sided"]
    assert test.run([1.0, 2.0], [1.0, 2.0]) is None
    assert test.run([1.0, 2.0, 3.0], None) is None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert test.run([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


# Test the registry exposes the Spearman metadata.
def test_spearman_registry_metadata() -> None:
    """The Spearman test carries its name, symbol and arity."""
    test = SIGNIFICANCE_TESTS["spearman-2-sided"]
    assert test.title == "Spearman rank correlation, two-sided"
    assert test.statistic_label == "rho"
    assert test.arity == 2


# Test entries mode cannot compute significance tests.
def test_entries_mode_rejects_significance() -> None:
    """A single entry set cannot provide paired rows."""
    from causaliq_analysis.workflow_action.actions.summarise.execution import (
        _summarise_entries,
    )
    from causaliq_analysis.workflow_action.types import ActionExecutionError

    with pytest.raises(ActionExecutionError, match="requires 'input'"):
        _summarise_entries({"significance": [object()]}, None, None)
