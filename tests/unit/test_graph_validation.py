"""Unit tests for graph averaging parameter validation."""

import pytest

from causaliq_analysis.graph import _validate_average_params, average


# Validation with valid parameters passes without error
def test_valid_params():
    _validate_average_params(sample_size=1000, pdag=True, seeds=(0, 1, 2))
    _validate_average_params(sample_size=10000, pdag=False, seeds=())


# Validation raises TypeError for non-integer sample_size
def test_invalid_sample_size_type():
    with pytest.raises(TypeError, match="sample_size must be an integer"):
        _validate_average_params(sample_size="1000", pdag=True, seeds=())


# Validation raises ValueError for negative sample_size
def test_invalid_sample_size_value():
    with pytest.raises(ValueError, match="sample_size must be positive"):
        _validate_average_params(sample_size=-1000, pdag=True, seeds=())


# Validation raises TypeError for non-boolean pdag
def test_invalid_pdag_type():
    with pytest.raises(TypeError, match="pdag must be a boolean"):
        _validate_average_params(sample_size=1000, pdag="true", seeds=())


# Validation raises TypeError for non-tuple seeds
def test_invalid_seeds_type():
    with pytest.raises(TypeError, match="seeds must be a tuple"):
        _validate_average_params(sample_size=1000, pdag=True, seeds=[0, 1])


# Validation raises TypeError for non-integer seed elements
def test_invalid_seed_element_type():
    with pytest.raises(TypeError, match="all seeds must be integers"):
        _validate_average_params(sample_size=1000, pdag=True, seeds=(0, "1"))


# Validation raises ValueError for negative seeds
def test_negative_seed():
    with pytest.raises(ValueError, match="all seeds must be non-negative"):
        _validate_average_params(sample_size=1000, pdag=True, seeds=(0, -1))


# Average raises TypeError when traces is not a dictionary
def test_invalid_traces_type():
    with pytest.raises(TypeError, match="traces must be a dictionary"):
        average(traces="not_a_dict", sample_size=1000, pdag=False, seeds=())


# Average raises TypeError when trace values are not Trace objects
def test_invalid_trace_values():
    with pytest.raises(
        TypeError, match="all values in traces must be Trace objects"
    ):
        average(
            traces={"key": "not_a_trace"},
            sample_size=1000,
            pdag=False,
            seeds=(),
        )
