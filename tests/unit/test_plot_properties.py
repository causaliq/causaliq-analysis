"""Unit tests for the plot property parser."""

import pytest

from causaliq_analysis.plot import parse_properties


# Parse properties converts scalar values to correct types.
def test_parse_properties_scalars():
    """Test parse_properties converts scalars to their types."""
    props = parse_properties(
        [
            "subplot.aspect=1.05",
            "figure.subplots_top=0.9",
            "subplot.grid=True",
            "legend.outside=False",
        ]
    )
    assert props["subplot.aspect"] == 1.05
    assert props["figure.subplots_top"] == 0.9
    assert props["subplot.grid"] is True
    assert props["legend.outside"] is False


# Parse properties converts blank values to empty strings.
def test_parse_properties_blank_value():
    """Test parse_properties handles blank and no-value properties."""
    props = parse_properties(["figure.title=", "subplot.kind"])
    assert props["figure.title"] == ""
    assert props["subplot.kind"] == ""


# Parse properties converts the not symbol to None.
def test_parse_properties_not_symbol():
    """Test parse_properties converts the not symbol to None."""
    props = parse_properties(["yaxis.range=¬"])
    assert props["yaxis.range"] is None


# Parse properties converts tuples, lists and dicts.
def test_parse_properties_collections():
    """Test parse_properties handles tuples, lists and dicts."""
    props = parse_properties(
        [
            "yaxis.range=(0,1.05)",
            "xaxis.ticks=[10,100,1000]",
            "palette=['#66bd63','#d73027']",
            "legend.labels={'a': 'A', 'b': 'B'}",
        ]
    )
    assert props["yaxis.range"] == (0, 1.05)
    assert props["xaxis.ticks"] == [10, 100, 1000]
    assert props["palette"] == ["#66bd63", "#d73027"]
    assert props["legend.labels"] == {"a": "A", "b": "B"}


# Parse properties converts Python literal scalar types.
def test_parse_properties_literal_scalars():
    """Test parse_properties parses Python literal scalar values."""
    props = parse_properties(
        [
            "int.property=22",
            "float.propety=0.23",
            "string.property='string value'",
            "bool.property=True",
            "none.property=None",
        ]
    )
    assert props["int.property"] == 22
    assert props["float.propety"] == 0.23
    assert props["string.property"] == "string value"
    assert props["bool.property"] is True
    assert props["none.property"] is None


# Parse properties converts Python literal collection types.
def test_parse_properties_literal_collections():
    """Test parse_properties parses tuple, list, dict and set literals."""
    props = parse_properties(
        [
            "tuple.property=(2, 'dad')",
            "list.property=['a', 1, 2.3]",
            "dict.property={'key1': 1, 'key2': 'me'}",
            "set.property={1, 'two'}",
        ]
    )
    assert props["tuple.property"] == (2, "dad")
    assert props["list.property"] == ["a", 1, 2.3]
    assert props["dict.property"] == {"key1": 1, "key2": "me"}
    assert props["set.property"] == {1, "two"}


# Parse properties keeps bare strings which are not Python literals.
def test_parse_properties_bare_strings():
    """Test parse_properties keeps bare values as strings."""
    props = parse_properties(
        ["subplot.grid_colour=lightgray", "xaxis.label=Sample size"]
    )
    assert props["subplot.grid_colour"] == "lightgray"
    assert props["xaxis.label"] == "Sample size"


# Parse properties coerces unquoted collections via legacy fallback.
def test_parse_properties_unquoted_collections():
    """Test unquoted tuples, lists and dicts fall back to legacy parsing."""
    props = parse_properties(
        [
            "yaxis.range=(low,high)",
            "palette=[#66bd63,#d73027]",
            "legend.labels={a,A,b,B}",
        ]
    )
    assert props["yaxis.range"] == ("low", "high")
    assert props["palette"] == ["#66bd63", "#d73027"]
    assert props["legend.labels"] == {"a": "A", "b": "B"}


# Parse properties handles separators inside quoted values.
def test_parse_properties_separators_in_values():
    """Test parse_properties tolerates separators inside values."""
    props = parse_properties(
        [
            "string.property='a=b'",
            "dict.property={'key1': 'b:c'}",
            "xaxis.label=a=b",
        ]
    )
    assert props["string.property"] == "a=b"
    assert props["dict.property"] == {"key1": "b:c"}
    assert props["xaxis.label"] == "a=b"


# Parse properties accepts a single string input.
def test_parse_properties_string_input():
    """Test parse_properties accepts a single property string."""
    props = parse_properties("subplot.aspect=2.0")
    assert props["subplot.aspect"] == 2.0


# Parse properties returns an empty dict for None input.
def test_parse_properties_none():
    """Test parse_properties returns an empty dict for None input."""
    assert parse_properties(None) == {}


# Parse properties raises ValueError for malformed strings.
def test_parse_properties_malformed():
    """Test parse_properties raises ValueError for bad property names."""
    with pytest.raises(ValueError, match="Malformed plot property"):
        parse_properties(["=1.05"])


# Parse properties rejects the legacy colon separator.
def test_parse_properties_legacy_separator():
    """Test parse_properties raises ValueError for the colon format."""
    with pytest.raises(ValueError, match="legacy ':' separator"):
        parse_properties(["xaxis.label:Sample size"])
