"""Unit tests for summarise column specifications."""

from typing import Any

import pytest

from causaliq_analysis.workflow_action.actions.summarise.columns import (
    ACTION_STATS,
    ColumnSpec,
    _normalise_list,
    _normalise_optional_list,
    _parse_column_spec,
    _parse_column_specs,
    _table_labels,
    _unique_fields,
)


# Test a plain field-and-statistic specification.
def test_parse_plain_spec() -> None:
    """A '<field>.<stat>' specification names no source cache."""
    spec = _parse_column_spec("f1.mean")
    assert spec == ColumnSpec(text="f1.mean", field="f1", stat="mean")
    assert not spec.is_derived


# Test a specification that names its input cache.
def test_parse_source_spec() -> None:
    """A '[n]' suffix records the one-based input index."""
    spec = _parse_column_spec("f1.mean[2]")
    assert (spec.source, spec.field, spec.stat) == (2, "f1", "mean")


# Test a bare field with a source reports a single value.
def test_parse_bare_field_spec() -> None:
    """A bare '<field>[n]' reports a single value."""
    spec = _parse_column_spec("node_count[1]")
    assert (spec.source, spec.field, spec.stat) == (1, "node_count", "unique")


# Test an argmax specification.
def test_parse_argmax_spec() -> None:
    """An 'argmax' specification records the reported dimension."""
    spec = _parse_column_spec("f1.argmax.pdg_seed")
    assert (spec.field, spec.stat, spec.dimension) == (
        "f1",
        "argmax",
        "pdg_seed",
    )


# Test an argmax element selector.
def test_parse_argmax_element_spec() -> None:
    """An '{n}' suffix records the one-based element of a dimension."""
    spec = _parse_column_spec("f1.argmax.fusion_weights{1}")
    assert (spec.stat, spec.dimension, spec.element) == (
        "argmax",
        "fusion_weights",
        1,
    )


# Test an element selector combines with a source index.
def test_parse_argmax_element_with_source() -> None:
    """An element index and source index are both recorded."""
    spec = _parse_column_spec("f1.argmax.fusion_weights{2}[3]")
    assert (spec.source, spec.element) == (3, 2)
    assert spec.dimension == "fusion_weights"


# Test an alias on a base column.
def test_parse_alias_on_base_column() -> None:
    """An 'as' suffix names the column for later formulas."""
    spec = _parse_column_spec("f1.mean[1] as bnsl")
    assert spec.text == "f1.mean[1]"
    assert spec.source == 1
    assert spec.alias == "bnsl"
    assert spec.key == "bnsl"


# Test an alias on a derived column.
def test_parse_alias_on_formula() -> None:
    """A formula may declare an alias and keep its expression text."""
    spec = _parse_column_spec("fusion - max(bnsl, llm) as gain")
    assert spec.is_derived
    assert spec.formula == "fusion - max(bnsl, llm)"
    assert spec.key == "gain"


# Test a formula without an alias keys on its expression.
def test_formula_without_alias_keys_on_text() -> None:
    """Without an alias a derived column keys on its formula text."""
    assert _parse_column_spec("fusion - 1").key == "fusion - 1"


# Test a formula may reference the aliases declared before it.
def test_formula_references_earlier_alias() -> None:
    """A formula sees the aliases of preceding columns only."""
    specs = _parse_column_specs(
        ["f1.mean[1] as bnsl", "f1.mean[2] as llm", "bnsl + llm as total"]
    )
    assert [spec.key for spec in specs] == ["bnsl", "llm", "total"]


# Test a derived column's alias is available to later formulas.
def test_derived_alias_chains() -> None:
    """A derived column may itself be referenced by a later formula."""
    specs = _parse_column_specs(
        [
            "f1.mean[1] as bnsl",
            "bnsl * 2 as double",
            "round(double + 1, 2) as shifted",
        ]
    )
    assert [spec.key for spec in specs] == ["bnsl", "double", "shifted"]


# Test a formula may not reference a later alias.
def test_formula_rejects_later_alias() -> None:
    """A forward alias reference is rejected."""
    with pytest.raises(ValueError, match="not an alias of an earlier"):
        _parse_column_specs(["bnsl + 1 as total", "f1.mean[1] as bnsl"])


# Test a repeated column key is rejected.
def test_repeated_key_rejected() -> None:
    """Two columns cannot share a name."""
    with pytest.raises(ValueError, match="declared twice"):
        _parse_column_specs(["f1.mean[1]", "f1.mean[1]"])


# Test a repeated alias is rejected.
def test_repeated_alias_rejected() -> None:
    """Two columns cannot share an alias."""
    with pytest.raises(ValueError, match="declared twice"):
        _parse_column_specs(["f1.mean[1] as bnsl", "f1.mean[2] as bnsl"])


# Test an alias may not shadow a formula function.
def test_alias_may_not_shadow_function() -> None:
    """A function name is reserved and cannot be an alias."""
    with pytest.raises(ValueError, match="formula function name"):
        _parse_column_specs(["f1.mean[1] as max"])


# Test invalid specifications are rejected with a clear message.
@pytest.mark.parametrize(
    "spec, message",
    [
        ("f1_without_stat", "must be <field>.<stat>"),
        ("f1.mode", "Unknown statistic 'mode'"),
        ("f1.mean,shd.sd", "contains comma"),
        ("f1.mean[0]", "one-based"),
        ("f1.argmax.fusion_weights{0}", "element index is one-based"),
        ("f1.mean{1}", "only valid for an argmax"),
        ("f1.argmax.fusion_weights[2]{1}", "before the source"),
        ("power(bnsl, 2)", "Unknown formula function 'power'"),
    ],
)
def test_parse_invalid_spec(spec: str, message: str) -> None:
    """Invalid specifications raise a ValueError naming the problem."""
    with pytest.raises(ValueError, match=message):
        _parse_column_spec(spec)


# Test formula detection distinguishes expressions from metric specs.
@pytest.mark.parametrize(
    "spec, derived",
    [
        ("f1.mean", False),
        ("f1.argmax.seed[1]", False),
        ("node_count[1]", False),
        ("fusion - llm", True),
        ("bnsl + 1", True),
        ("-fusion", True),
        ("round(fusion, 2)", True),
    ],
)
def test_formula_detection(spec: str, derived: bool) -> None:
    """An operator or a function call marks a specification as a formula."""
    assert _parse_column_spec(spec).is_derived is derived


# Test the action vocabulary extends the shared statistics.
def test_action_stats_include_unique() -> None:
    """The action accepts 'unique' as well as the shared statistics."""
    assert "unique" in ACTION_STATS
    assert "mean" in ACTION_STATS


# Test referenced fields are de-duplicated in column order.
def test_unique_fields_dedupes() -> None:
    """Fields are collected once, in first-referenced order."""
    specs = _parse_column_specs(["f1.mean", "shd.sd", "f1.max"])
    assert _unique_fields(specs) == ["f1", "shd"]


# Test list parameters normalise to a list of strings.
@pytest.mark.parametrize(
    "value, expected",
    [(None, []), ("a", ["a"]), (["a", 1], ["a", "1"]), (("a",), ["a"])],
)
def test_normalise_list(value: Any, expected: list) -> None:
    """A missing value is empty, a string is one entry, lists are mapped."""
    assert _normalise_list(value) == expected


# Test an unsupported list parameter type is rejected.
def test_normalise_list_rejects_number() -> None:
    """A numeric parameter value is rejected."""
    with pytest.raises(ValueError, match="expected a string or list"):
        _normalise_list(3)


# Test optional list parameters preserve null entries.
@pytest.mark.parametrize(
    "value, expected",
    [
        (None, []),
        (".3f", [".3f"]),
        ([".3f", None], [".3f", None]),
        ((1, None), ["1", None]),
    ],
)
def test_normalise_optional_list(value: Any, expected: list) -> None:
    """A null entry is preserved; other entries become text."""
    assert _normalise_optional_list(value) == expected


# Test an unsupported optional list type is rejected.
def test_normalise_optional_list_rejects_number() -> None:
    """A numeric optional parameter value is rejected."""
    with pytest.raises(ValueError, match="expected a string or list"):
        _normalise_optional_list(3)


# Test labels default to the dimensions then each column's key.
def test_table_labels_default() -> None:
    """Without headers the labels are the dimensions and column keys."""
    specs = _parse_column_specs(["f1.mean[1] as bnsl", "f1.max"])
    assert _table_labels(["network"], specs, []) == [
        "network",
        "bnsl",
        "f1.max",
    ]


# Test declared headers replace every label.
def test_table_labels_declared() -> None:
    """Declared headers label every column of the table."""
    specs = _parse_column_specs(["f1.mean[1] as bnsl"])
    labels = _table_labels(["network"], specs, ["Network", "BNSL $F_1$"])
    assert labels == ["Network", "BNSL $F_1$"]


# Test a header list of the wrong length is rejected.
def test_table_labels_wrong_length() -> None:
    """Headers must have one entry per column."""
    specs = _parse_column_specs(["f1.mean"])
    with pytest.raises(ValueError, match="must have 2 entries"):
        _table_labels(["network"], specs, ["Network"])
