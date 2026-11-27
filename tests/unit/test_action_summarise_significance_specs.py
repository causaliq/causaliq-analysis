"""Unit tests for summarise significance specifications."""

from typing import Set

import pytest

from causaliq_analysis.workflow_action.actions.summarise import (
    significance_specs,
)
from causaliq_analysis.workflow_action.actions.summarise.significance import (
    SIGNIFICANCE_TESTS,
    SignificanceSpec,
    _default_caption,
    _statistic_format,
    _statistic_label,
)

_parse_significance_spec = significance_specs._parse_significance_spec
_parse_significance_specs = significance_specs._parse_significance_specs
_require_single_test = significance_specs._require_single_test

_ALIASES: Set[str] = {"bnsl", "fusion", "llm"}


# Test a full specification keeps its label and operands.
def test_parse_full_spec() -> None:
    """A labelled specification parses into a SignificanceSpec."""
    spec = _parse_significance_spec(
        "wilcoxon-signed-rank-2-sided(fusion, bnsl) as Fusion vs BNSL",
        _ALIASES,
    )
    assert spec.test.name == "wilcoxon-signed-rank-2-sided"
    assert spec.left == "fusion"
    assert spec.right == "bnsl"
    assert spec.label == "Fusion vs BNSL"
    assert spec.text == "wilcoxon-signed-rank-2-sided(fusion, bnsl)"


# Test a matching pair of surrounding quotes is removed.
def test_parse_quoted_label() -> None:
    """Quotes around a label are not part of the comparison text."""
    spec = _parse_significance_spec(
        'wilcoxon-signed-rank-2-sided(fusion, bnsl) as "Fusion vs BNSL"',
        _ALIASES,
    )
    assert spec.label == "Fusion vs BNSL"


# Test a specification without a label derives one from its operands.
def test_parse_default_label() -> None:
    """The default label joins the operand aliases."""
    spec = _parse_significance_spec(
        "wilcoxon-signed-rank-2-sided(fusion, bnsl)",
        _ALIASES,
    )
    assert spec.label == "fusion vs bnsl"


# Test an unknown test name is rejected.
def test_unknown_test() -> None:
    """A test name absent from the registry is rejected."""
    with pytest.raises(ValueError, match="Unknown significance test"):
        _parse_significance_spec(
            "wilcoxon-unknown(fusion, bnsl)",
            _ALIASES,
        )


# Test the argument count must match the test arity.
def test_wrong_arity() -> None:
    """A paired test requires two arguments."""
    with pytest.raises(ValueError, match="takes 2 argument"):
        _parse_significance_spec(
            "wilcoxon-signed-rank-2-sided(fusion)",
            _ALIASES,
        )


# Test an unknown alias is rejected.
def test_unknown_alias() -> None:
    """An operand must name a metric alias."""
    with pytest.raises(ValueError, match="Unknown column 'missing'"):
        _parse_significance_spec(
            "wilcoxon-signed-rank-2-sided(fusion, missing)",
            _ALIASES,
        )


# Test a missing argument is rejected.
def test_missing_argument() -> None:
    """An empty argument is rejected."""
    with pytest.raises(ValueError, match="missing an argument"):
        _parse_significance_spec(
            "wilcoxon-signed-rank-2-sided(fusion,)",
            _ALIASES,
        )


# Test a malformed specification is rejected.
def test_malformed_spec() -> None:
    """A specification without parentheses is rejected."""
    with pytest.raises(ValueError, match="Invalid significance spec"):
        _parse_significance_spec("wilcoxon-signed-rank-2-sided", _ALIASES)


# Test repeated comparison labels are rejected.
def test_duplicate_labels() -> None:
    """Two result rows may not share a comparison label."""
    specs = [
        "wilcoxon-signed-rank-2-sided(fusion, bnsl) as same",
        "wilcoxon-signed-rank-2-sided(fusion, llm) as same",
    ]
    with pytest.raises(ValueError, match="declared twice"):
        _parse_significance_specs(specs, _ALIASES)


# Test the parsed specifications preserve declaration order.
def test_parse_order() -> None:
    """Specifications are returned in declaration order."""
    specs = _parse_significance_specs(
        [
            "wilcoxon-signed-rank-2-sided(fusion, bnsl) as first",
            "wilcoxon-signed-rank-2-sided(fusion, llm) as second",
        ],
        _ALIASES,
    )
    assert [spec.label for spec in specs] == ["first", "second"]


def _fake_spec(name: str, label: str) -> SignificanceSpec:
    """Build a specification around a renamed copy of the Wilcoxon test."""
    from dataclasses import replace

    test = replace(
        SIGNIFICANCE_TESTS["wilcoxon-signed-rank-2-sided"],
        name=name,
        title=f"title {name}",
        statistic_label=name.upper(),
        format_spec=".2f" if name == "first" else ".3f",
    )
    return SignificanceSpec(
        text=name,
        test=test,
        left="fusion",
        right="bnsl",
        label=label,
    )


# Test a table may not mix different significance tests.
def test_mixed_tests_rejected() -> None:
    """Every row of one table must use the same test."""
    with pytest.raises(ValueError, match="must use the same test"):
        _require_single_test(
            [_fake_spec("first", "a"), _fake_spec("second", "b")]
        )


# Test a mixed-test caption falls back to the generic title.
def test_default_caption_mixed_tests() -> None:
    """A table of mixed tests uses the generic caption."""
    specs: list[SignificanceSpec] = [
        _fake_spec("first", "a"),
        _fake_spec("second", "b"),
    ]
    assert _default_caption(specs) == "STATISTICAL TESTS"


# Test a mixed-test statistic label falls back to a generic label.
def test_statistic_label_mixed_tests() -> None:
    """A table of mixed tests uses a generic statistic header."""
    specs: list[SignificanceSpec] = [
        _fake_spec("first", "a"),
        _fake_spec("second", "b"),
    ]
    assert _statistic_label(specs) == "Statistic"


# Test a mixed-test statistic format falls back to a generic format.
def test_statistic_format_mixed_tests() -> None:
    """A table of mixed tests uses a generic statistic format."""
    specs: list[SignificanceSpec] = [
        _fake_spec("first", "a"),
        _fake_spec("second", "b"),
    ]
    assert _statistic_format(specs) == ".4g"
