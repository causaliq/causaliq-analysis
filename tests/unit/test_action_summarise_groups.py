"""Unit tests for summarise report grouping."""

from types import SimpleNamespace

import pytest

from causaliq_analysis.workflow_action.actions.summarise.groups import (
    _expand_groups,
    _group_matches,
    _report_groups,
)
from causaliq_analysis.workflow_action.types import ActionExecutionError


# Test groups expand in matrix order.
def test_expand_groups_matrix_order() -> None:
    """Each matrix combination becomes one group."""
    groups = _expand_groups({"network": ["asia", "alarm"], "seed": [0, 1]})
    assert groups == [
        {"network": "asia", "seed": 0},
        {"network": "asia", "seed": 1},
        {"network": "alarm", "seed": 0},
        {"network": "alarm", "seed": 1},
    ]


# Test range values are rejected for grouping.
def test_expand_groups_rejects_range_value() -> None:
    """Range syntax cannot be grouped."""
    with pytest.raises(ActionExecutionError, match="range value"):
        _expand_groups({"seed": ["0-2"]})


# Test a scalar dimension value forms a single group.
def test_expand_groups_scalar_value() -> None:
    """A non-list dimension value forms a single group."""
    assert _expand_groups({"network": "asia"}) == [{"network": "asia"}]


# Test an explicit matrix defines the report groups.
def test_report_groups_uses_matrix() -> None:
    """An explicit matrix defines the groups."""
    context = SimpleNamespace(matrix={"network": ["asia"]})
    groups, dimensions = _report_groups(context)
    assert groups == [{"network": "asia"}]
    assert dimensions == ["network"]


# Test job matrix values fall back to a single group.
def test_report_groups_uses_matrix_values() -> None:
    """Without a matrix the job values form one group."""
    context = SimpleNamespace(matrix={}, matrix_values={"network": "asia"})
    groups, dimensions = _report_groups(context)
    assert groups == [{"network": "asia"}]
    assert dimensions == ["network"]


# Test an unconstrained run reports one ungrouped row.
def test_report_groups_without_context() -> None:
    """A missing context reports one ungrouped row."""
    assert _report_groups(None) == ([{}], [])


# Test matching ignores absent and null dimensions.
def test_group_matches_wildcards() -> None:
    """Absent dimensions and null values match any group."""
    assert _group_matches({"seed": 1}, {"network": "asia"}, ["network"])
    assert _group_matches({"network": None}, {"network": "asia"}, ["network"])
    assert _group_matches({"network": "asia"}, {"network": None}, ["network"])


# Test matching compares numeric suffixes case-insensitively.
def test_group_matches_size_suffix() -> None:
    """Numeric suffixes compare case-insensitively."""
    assert _group_matches({"size": "10k"}, {"size": "10K"}, ["size"])
    assert not _group_matches({"size": "1K"}, {"size": "10K"}, ["size"])


# Test boolean dimension values compare as text.
def test_group_matches_boolean() -> None:
    """Boolean values compare using their text form."""
    assert _group_matches({"flag": True}, {"flag": True}, ["flag"])
    assert not _group_matches({"flag": True}, {"flag": False}, ["flag"])
