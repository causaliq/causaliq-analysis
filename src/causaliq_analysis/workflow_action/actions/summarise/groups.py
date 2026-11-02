"""Grouping helpers for report-mode summarisation."""

import itertools
import re
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = ["_expand_groups", "_group_matches", "_report_groups"]

_RANGE_PATTERN = re.compile(r"^\d+-\d+$")
_SIZE_PATTERN = re.compile(r"^\d+[kKmMgGtT]?$")


def _report_groups(
    context: Optional[Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Return the group keys and grouping dimensions for a report run.

    An explicit workflow matrix defines the groups. Without one, the job's
    matrix values define a single group; an unconstrained run reports a
    single row.

    Args:
        context: Workflow context, if any.

    Returns:
        Tuple of (group matrix values, grouping dimension names).

    """
    matrix = getattr(context, "matrix", None)
    if isinstance(matrix, dict) and matrix:
        return _expand_groups(matrix), list(matrix)
    values = getattr(context, "matrix_values", None)
    if isinstance(values, dict) and values:
        return [dict(values)], list(values)
    return [{}], []


def _expand_groups(matrix: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Expand a workflow matrix into one group per combination.

    Args:
        matrix: Matrix mapping dimensions to their values.

    Returns:
        Group matrix values in matrix expansion order.

    Raises:
        ActionExecutionError: If a dimension uses range syntax, which is
            not expanded for grouping.

    """
    dimensions = list(matrix)
    value_lists = [
        _dimension_values(dimension, matrix[dimension])
        for dimension in dimensions
    ]
    return [
        dict(zip(dimensions, combination))
        for combination in itertools.product(*value_lists)
    ]


def _dimension_values(dimension: str, values: Any) -> List[Any]:
    """Return a matrix dimension's values as a list.

    Args:
        dimension: Dimension name, used in the error message.
        values: Declared dimension values.

    Returns:
        The dimension's values.

    Raises:
        ActionExecutionError: If a value uses range syntax.

    """
    declared = [values] if isinstance(values, str) else list(values)
    for value in declared:
        if isinstance(value, str) and _RANGE_PATTERN.match(value):
            raise ActionExecutionError(
                f"summarise cannot group by range value '{value}' in "
                f"dimension '{dimension}'; list the values explicitly"
            )
    return declared


def _group_matches(
    entry_values: Dict[str, Any],
    group_values: Dict[str, Any],
    dimensions: List[str],
) -> bool:
    """Return True when an entry belongs to a group.

    Mirrors workflow matrix matching: a missing entry dimension or a None
    value on either side is a wildcard, and numeric suffixes compare
    case-insensitively (so '10K' matches '10k').

    Args:
        entry_values: Matrix values carried by the cache entry.
        group_values: Matrix values of the group.
        dimensions: Grouping dimension names.

    Returns:
        True when the entry matches every dimension.

    """
    for dimension in dimensions:
        if dimension not in entry_values:
            continue
        target = group_values.get(dimension)
        entry_value = entry_values[dimension]
        if target is None or entry_value is None:
            continue
        if _canonical(entry_value) != _canonical(target):
            return False
    return True


def _canonical(value: Any) -> str:
    """Return a canonical comparison key for a matrix value.

    Args:
        value: Matrix value to canonicalise.

    Returns:
        Canonical text for the value.

    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and _SIZE_PATTERN.match(value):
        return value.lower()
    return str(value)
