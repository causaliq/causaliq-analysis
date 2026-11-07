"""Summary statistics for summarise column specifications.

Values are collected per source cache and per field, so a column can name
the input cache that supplies it. A column without a source index draws
on every input cache, which keeps the original union behaviour.
"""

import statistics
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.workflow_action.types import ActionExecutionError

from .columns import ColumnSpec
from .formula import _evaluate_formula

__all__ = ["_compute_stats", "_stat_value"]

# Collected values per (one-based source index, field)
Values = Dict[Tuple[int, str], List[float]]

# Winning entry per (one-based source index, field): its value and the
# matrix values of the entry holding it
Argmax = Dict[Tuple[int, str], Tuple[float, Dict[str, Any]]]


def _compute_stats(
    specs: List[ColumnSpec],
    values: Values,
    argmax: Argmax,
) -> Dict[str, Any]:
    """Compute the value of every column of a table row.

    Columns are computed in table order so that a derived column can use
    the values of the columns before it, which are collected under their
    aliases.

    Args:
        specs: Column specifications in table order.
        values: Collected values per source and field.
        argmax: Winning entry per source and field.

    Returns:
        Mapping of column key to computed value.

    """
    results: Dict[str, Any] = {}
    named: Dict[str, Any] = {}
    for spec in specs:
        value = _column_value(spec, values, argmax, named)
        results[spec.key] = value
        if spec.alias:
            named[spec.alias] = value
    return results


def _column_value(
    spec: ColumnSpec,
    values: Values,
    argmax: Argmax,
    named: Dict[str, Any],
) -> Any:
    """Compute the value of one column.

    Args:
        spec: Column specification.
        values: Collected values per source and field.
        argmax: Winning entry per source and field.
        named: Values of the preceding columns, keyed by alias.

    Returns:
        Computed value, or an empty string when it is not computable.

    Raises:
        ActionExecutionError: If a 'unique' column spans conflicting
            values.

    """
    if spec.is_derived:
        return _evaluate_formula(spec.formula or "", named)
    field = spec.field or ""
    if spec.stat == "argmax":
        return _argmax_dimension(argmax, spec.source, field, spec.dimension)
    collected = _field_values(values, spec.source, field)
    if spec.stat == "unique":
        return _unique_value(collected, spec.text)
    return _stat_value(spec.stat or "", collected)


def _field_values(
    values: Values,
    source: Optional[int],
    field: str,
) -> List[float]:
    """Return the values collected for a field.

    Args:
        values: Collected values per source and field.
        source: One-based source index, or None for every input cache.
        field: Metric field name.

    Returns:
        Collected values in collection order.

    """
    if source is not None:
        return list(values.get((source, field), []))
    collected: List[float] = []
    for (_, name), field_values in values.items():
        if name == field:
            collected.extend(field_values)
    return collected


def _unique_value(values: List[float], spec: str) -> Any:
    """Return the single value of a field.

    Args:
        values: Collected values for the field.
        spec: Column specification, used in the error message.

    Returns:
        The single value, or an empty string when nothing was collected.

    Raises:
        ActionExecutionError: If the field holds conflicting values.

    """
    distinct = sorted(set(values))
    if not distinct:
        return ""
    if len(distinct) > 1:
        raise ActionExecutionError(
            f"Column '{spec}' reports a single value, but the field holds "
            f"{len(distinct)} distinct values: {distinct}"
        )
    value = distinct[0]
    return int(value) if float(value).is_integer() else value


def _argmax_dimension(
    argmax: Argmax,
    source: Optional[int],
    field: str,
    dimension: Optional[str],
) -> Any:
    """Return the dimension value of the entry holding a field's maximum.

    Args:
        argmax: Winning entry per source and field.
        source: One-based source index, or None for every input cache.
        field: Metric field name.
        dimension: Matrix dimension to report.

    Returns:
        The winning entry's matrix value for the dimension, or an empty
        string when the field has no numeric value.

    """
    winner = _argmax_winner(argmax, source, field)
    if winner is None or dimension is None:
        return ""
    return winner[1].get(dimension, "")


def _argmax_winner(
    argmax: Argmax,
    source: Optional[int],
    field: str,
) -> Optional[Tuple[float, Dict[str, Any]]]:
    """Return the entry holding a field's maximum value.

    Args:
        argmax: Winning entry per source and field.
        source: One-based source index, or None for every input cache.
        field: Metric field name.

    Returns:
        The winning value and its matrix values, or None when the field
        has no numeric value.

    """
    if source is not None:
        return argmax.get((source, field))
    winners = [winner for (_, name), winner in argmax.items() if name == field]
    return max(winners, key=lambda item: item[0]) if winners else None


def _stat_value(stat: str, values: List[float]) -> Any:
    """Compute a single summary statistic.

    Args:
        stat: Statistic name ('mean', 'sd', 'count', 'min', 'max' or
            'median').
        values: Collected values for the field.

    Returns:
        Computed statistic, or an empty string when unavailable.

    """
    if stat == "count":
        return len(values)
    if not values:
        return ""
    if stat == "mean":
        return statistics.mean(values)
    if stat == "min":
        return min(values)
    if stat == "max":
        return max(values)
    if stat == "median":
        return statistics.median(values)
    if len(values) >= 2:
        return statistics.stdev(values)
    return ""
