"""
Tests for shared validation utilities.
"""

import pytest

from causaliq_analysis.validation import (
    SUPPORTED_STATS,
    parse_sample_size,
    parse_seeds_cli,
    parse_seeds_workflow,
    require_one_of,
    require_param,
    validate_filter_expression,
    validate_metric_specs,
)


# Test sample size parsing
def test_parse_sample_size_integers():
    """Test parsing integer sample sizes."""
    assert parse_sample_size(1000) == 1000
    assert parse_sample_size(0) == 0


def test_parse_sample_size_k_suffix():
    """Test parsing sample sizes with 'k' suffix."""
    assert parse_sample_size("10k") == 10000
    assert parse_sample_size("1.5k") == 1500
    assert parse_sample_size("0.5K") == 500  # case insensitive


def test_parse_sample_size_m_suffix():
    """Test parsing sample sizes with 'm' suffix."""
    assert parse_sample_size("1m") == 1000000
    assert parse_sample_size("2.5m") == 2500000
    assert parse_sample_size("0.001M") == 1000  # case insensitive


def test_parse_sample_size_plain_strings():
    """Test parsing plain string integers."""
    assert parse_sample_size("1000") == 1000
    assert parse_sample_size("  500  ") == 500  # whitespace handling


def test_parse_sample_size_invalid():
    """Test invalid sample size formats."""
    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size("invalid")

    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size("10x")

    with pytest.raises(ValueError, match="Invalid sample size type"):
        parse_sample_size(None)

    with pytest.raises(ValueError, match="Invalid sample size type"):
        parse_sample_size([])


def test_parse_sample_size_invalid_k_suffix():
    """Test invalid sample sizes with 'k' suffix causing ValueError."""
    # These should trigger the ValueError exception on lines 44-45
    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size("invalid.k")

    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size("abc.k")

    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size(".k")


def test_parse_sample_size_invalid_m_suffix():
    """Test invalid sample sizes with 'm' suffix causing ValueError."""
    # These should trigger the ValueError exception on lines 49-50
    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size("invalid.m")

    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size("xyz.m")

    with pytest.raises(ValueError, match="Invalid sample size format"):
        parse_sample_size(".m")


# Test CLI seeds parsing
def test_parse_seeds_cli_empty():
    """Test parsing empty seeds string."""
    assert parse_seeds_cli("") == ()
    assert parse_seeds_cli("   ") == ()


def test_parse_seeds_cli_single():
    """Test parsing single seed."""
    assert parse_seeds_cli("5") == (5,)
    assert parse_seeds_cli("  10  ") == (10,)


def test_parse_seeds_cli_range():
    """Test parsing seed ranges."""
    assert parse_seeds_cli("0,2") == (0, 1, 2)
    assert parse_seeds_cli("5,7") == (5, 6, 7)
    assert parse_seeds_cli("3,3") == (3,)  # single element range


def test_parse_seeds_cli_invalid_range():
    """Test invalid seed ranges."""
    with pytest.raises(ValueError, match="Invalid range"):
        parse_seeds_cli("5,2")  # start > end


def test_parse_seeds_cli_invalid_format():
    """Test invalid seed formats."""
    with pytest.raises(ValueError, match="Seeds should be either"):
        parse_seeds_cli("1,2,3")  # more than 2 values

    with pytest.raises(ValueError, match="Invalid seed format"):
        parse_seeds_cli("invalid")

    with pytest.raises(ValueError, match="Invalid seed format"):
        parse_seeds_cli("1,invalid")


# Test workflow seeds parsing
def test_parse_seeds_workflow_empty():
    """Test parsing empty seeds."""
    assert parse_seeds_workflow("") == ()
    assert parse_seeds_workflow(None) == ()
    assert parse_seeds_workflow("   ") == ()


def test_parse_seeds_workflow_tuple():
    """Test parsing tuple seeds."""
    assert parse_seeds_workflow((1, 2, 3)) == (1, 2, 3)


def test_parse_seeds_workflow_list():
    """Test parsing list seeds."""
    assert parse_seeds_workflow([1, 2, 3]) == (1, 2, 3)


def test_parse_seeds_workflow_string():
    """Test parsing string seeds."""
    assert parse_seeds_workflow("1,2,3") == (1, 2, 3)
    assert parse_seeds_workflow("  5  ") == (5,)
    assert parse_seeds_workflow("10,20,30") == (10, 20, 30)


# Test workflow seeds parsing single integer.
def test_parse_seeds_workflow_single_int():
    """Test parsing single integer seed (from YAML matrix)."""
    assert parse_seeds_workflow(0) == (0,)
    assert parse_seeds_workflow(5) == (5,)
    assert parse_seeds_workflow(123) == (123,)


def test_parse_seeds_workflow_invalid():
    """Test invalid seed formats."""
    with pytest.raises(ValueError, match="Invalid seed format"):
        parse_seeds_workflow("invalid,format")

    with pytest.raises(ValueError, match="Invalid seed type"):
        parse_seeds_workflow({"invalid": "dict"})


# Test SUPPORTED_STATS constant.
def test_supported_stats_constant():
    """SUPPORTED_STATS contains expected statistics."""
    assert SUPPORTED_STATS == frozenset({"mean", "sd", "count"})


# Test validate_filter_expression accepts valid expressions.
def test_validate_filter_expression_valid():
    """Valid filter expressions pass without error."""
    validate_filter_expression("network == 'asia'")
    validate_filter_expression("x > 5 and y < 10")
    validate_filter_expression("sample_size >= 1000")
    validate_filter_expression("algorithm in ['pc', 'fci']")


# Test validate_filter_expression accepts None and empty.
def test_validate_filter_expression_none_empty():
    """None and empty filter expressions pass without error."""
    validate_filter_expression(None)
    validate_filter_expression("")
    validate_filter_expression("   ")


# Test validate_filter_expression rejects invalid syntax.
def test_validate_filter_expression_invalid_syntax():
    """Invalid filter syntax raises ValueError."""
    with pytest.raises(ValueError, match="Invalid filter expression"):
        validate_filter_expression("x ==")  # incomplete

    with pytest.raises(ValueError, match="Invalid filter expression"):
        validate_filter_expression("x &&& y")  # invalid operator


# Test validate_metric_specs parses valid specs.
def test_validate_metric_specs_valid():
    """Valid metric specs are parsed correctly."""
    result = validate_metric_specs(["f1.mean", "shd.sd", "precision.count"])
    assert result == [("f1", "mean"), ("shd", "sd"), ("precision", "count")]


# Test validate_metric_specs rejects empty list.
def test_validate_metric_specs_empty():
    """Empty metric specs raise ValueError."""
    with pytest.raises(ValueError, match="At least one metric"):
        validate_metric_specs([])


# Test validate_metric_specs rejects missing dot.
def test_validate_metric_specs_no_dot():
    """Metric spec without dot raises ValueError."""
    with pytest.raises(ValueError, match="must be <field>.<stat>"):
        validate_metric_specs(["f1mean"])


# Test validate_metric_specs rejects unknown stat.
def test_validate_metric_specs_unknown_stat():
    """Metric spec with unknown statistic raises ValueError."""
    with pytest.raises(ValueError, match="Unknown statistic 'median'"):
        validate_metric_specs(["f1.median"])


# Test validate_metric_specs handles nested field names.
def test_validate_metric_specs_nested_field():
    """Metric specs with nested fields are parsed correctly."""
    result = validate_metric_specs(["metrics.f1.mean"])
    assert result == [("metrics.f1", "mean")]


# Test validate_metric_specs with custom supported_stats.
def test_validate_metric_specs_custom_stats():
    """Custom supported_stats override is respected."""
    custom = frozenset({"median", "mode"})
    result = validate_metric_specs(["f1.median"], supported_stats=custom)
    assert result == [("f1", "median")]


# Test require_param returns value when present.
def test_require_param_present():
    """require_param returns value when parameter is present."""
    params = {"input": "/path/to/file", "output": "/out"}
    result = require_param(params, "input", "test_action")
    assert result == "/path/to/file"


# Test require_param raises when missing.
def test_require_param_missing():
    """require_param raises ValueError when parameter is missing."""
    params = {"output": "/out"}
    with pytest.raises(ValueError, match="'test_action' requires 'input'"):
        require_param(params, "input", "test_action")


# Test require_param raises when None.
def test_require_param_none():
    """require_param raises ValueError when parameter is None."""
    params = {"input": None}
    with pytest.raises(ValueError, match="'test_action' requires 'input'"):
        require_param(params, "input", "test_action")


# Test require_one_of returns first present param name.
def test_require_one_of_first_present():
    """require_one_of returns name of first present parameter."""
    params = {"traces": "/path", "network": "asia"}
    result = require_one_of(params, ["traces", "network"], "migrate")
    assert result == "traces"


# Test require_one_of returns second if first missing.
def test_require_one_of_second_present():
    """require_one_of returns second param if first is missing."""
    params = {"network": "asia"}
    result = require_one_of(params, ["traces", "network"], "migrate")
    assert result == "network"


# Test require_one_of raises when all missing.
def test_require_one_of_all_missing():
    """require_one_of raises ValueError when all parameters are missing."""
    params = {"other": "value"}
    with pytest.raises(ValueError, match="requires one of"):
        require_one_of(params, ["traces", "network"], "migrate")


# Test require_one_of raises when all None.
def test_require_one_of_all_none():
    """require_one_of raises ValueError when all parameters are None."""
    params = {"traces": None, "network": None}
    with pytest.raises(ValueError, match="requires one of"):
        require_one_of(params, ["traces", "network"], "migrate")
