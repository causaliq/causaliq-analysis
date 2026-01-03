"""
Tests for shared validation utilities.
"""

import pytest

from causaliq_analysis.validation import (
    parse_sample_size,
    parse_seeds_cli,
    parse_seeds_workflow,
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

    with pytest.raises(ValueError, match="Invalid seeds format"):
        parse_seeds_cli("invalid")

    with pytest.raises(ValueError, match="Invalid seeds format"):
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


def test_parse_seeds_workflow_invalid():
    """Test invalid seed formats."""
    with pytest.raises(ValueError, match="Invalid seeds format"):
        parse_seeds_workflow("invalid,format")

    with pytest.raises(ValueError, match="Invalid seeds type"):
        parse_seeds_workflow(123)  # not a valid type

    with pytest.raises(ValueError, match="Invalid seeds type"):
        parse_seeds_workflow({"invalid": "dict"})
