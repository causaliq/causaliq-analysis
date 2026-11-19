"""Summary statistics for summarise column specifications.

Values are collected per source cache and per field, so a column can name
the input cache that supplies it. A column without a source index draws
on every input cache, which keeps the original union behaviour.
"""

import json
import statistics
from typing import Any, Dict, List, Optional, Tuple

from causaliq_analysis.workflow_action.types import ActionExecutionError

from .columns import ColumnSpec
from .formula import _evaluate_formula

__all__ = ["_compute_stats", "_stat_value"]

# Collected values per (one-based source index, field, where predicate)
Values = Dict[Tuple[int, str, Optional[str]], List[Any]]

# Winning entry per (one-based source index, field, where predicate): its
# value and the matrix values of the entry holding it
Argmax = Dict[Tuple[int, str, Optional[str]], Tuple[float, Dict[str, Any]]]


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
        return _argmax_dimension(
            argmax,
            spec.source,
            field,
            spec.dimension,
            spec.element,
            spec.where,
        )
    collected = _field_values(values, spec.source, field, spec.where)
    if spec.stat in {"bin", "pct"}:
        return _bin_value(collected, spec.bounds, spec.stat == "pct")
    if spec.stat == "unique":
        return _unique_value(collected, spec.text)
    return _stat_value(spec.stat or "", collected)


def _field_values(
    values: Values,
    source: Optional[int],
    field: str,
    where: Optional[str],
) -> List[Any]:
    """Return the values collected for a field and predicate.

    Args:
        values: Collected values per source, field and predicate.
        source: One-based source index, or None for every input cache.
        field: Metric field name.
        where: Entry predicate, or None for entries that carry no
            predicate.

    Returns:
        Collected values in collection order.

    """
    if source is not None:
        return list(values.get((source, field, where), []))
    collected: List[Any] = []
    for (_, name, clause), field_values in values.items():
        if name == field and clause == where:
            collected.extend(field_values)
    return collected


def _numeric_values(values: List[Any]) -> List[float]:
    """Return the numeric values of a collected field.

    Text values are ignored so that a text-only field does not turn a
    numeric statistic into an error. Numeric strings are converted, which
    keeps values loaded from CSV-like metadata comparable.

    Args:
        values: Collected values for a field.

    Returns:
        Numeric values in collection order.

    """
    numbers: List[float] = []
    for value in values:
        if isinstance(value, bool) or value is None or value == "":
            continue
        if isinstance(value, (int, float)):
            numbers.append(float(value))
            continue
        try:
            numbers.append(float(value))
        except (TypeError, ValueError):
            continue
    return numbers


def _bin_value(
    values: List[Any],
    bounds: Optional[Tuple[float, float]],
    percentage: bool,
) -> Any:
    """Return the count or percentage of values inside a half-open bin.

    The bin is ``low <= value < high``; an infinite upper bound includes
    every value at or above the lower bound. A percentage of an empty
    collection is an empty cell rather than a division by zero.

    Args:
        values: Collected values for the field.
        bounds: Lower and upper bound of the bin, or None.
        percentage: Whether to return a percentage instead of a count.

    Returns:
        Count of values in the bin, or their percentage (0-100).

    """
    if bounds is None:  # pragma: no cover - parsing guarantees bounds
        return ""
    low, high = bounds
    numbers = _numeric_values(values)
    count = sum(1 for value in numbers if low <= value < high)
    if not percentage:
        return count
    if not numbers:
        return ""
    return 100.0 * count / len(numbers)


def _unique_value(values: List[Any], spec: str) -> Any:
    """Return the single raw value of a field.

    Args:
        values: Collected values for the field.
        spec: Column specification, used in the error message.

    Returns:
        The single value, or an empty string when nothing was collected.

    Raises:
        ActionExecutionError: If the field holds conflicting values.

    """
    distinct = _distinct_values(values)
    if not distinct:
        return ""
    if len(distinct) > 1:
        raise ActionExecutionError(
            f"Column '{spec}' reports a single value, but the field holds "
            f"{len(distinct)} distinct values: {distinct}"
        )
    value = distinct[0]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _distinct_values(values: List[Any]) -> List[Any]:
    """Return distinct values in first-seen order.

    Values are compared by equality while retaining their original type, so
    a text field can report a string and a numeric field can report a
    number.

    Args:
        values: Collected values for a field.

    Returns:
        Distinct values in collection order.

    """
    distinct: List[Any] = []
    for value in values:
        if value is None or value == "":
            continue
        if not any(value == seen for seen in distinct):
            distinct.append(value)
    return distinct


def _argmax_dimension(
    argmax: Argmax,
    source: Optional[int],
    field: str,
    dimension: Optional[str],
    element: Optional[int] = None,
    where: Optional[str] = None,
) -> Any:
    """Return the dimension value of the entry holding a field's maximum.

    Args:
        argmax: Winning entry per source, field and predicate.
        source: One-based source index, or None for every input cache.
        field: Metric field name.
        dimension: Matrix dimension to report.
        element: One-based element of a list-valued dimension to report,
            or None to report the whole value.
        where: Entry predicate, or None for entries that carry no
            predicate.

    Returns:
        The winning entry's matrix value for the dimension, or an empty
        string when the field has no numeric value. When ``element`` names
        one element of a list-valued dimension, its value is returned, or
        an empty string when the list is too short.

    """
    winner = _argmax_winner(argmax, source, field, where)
    if winner is None or dimension is None:
        return ""
    value = winner[1].get(dimension, "")
    if element is None:
        return value
    return _element_value(value, element)


def _element_value(value: Any, element: int) -> Any:
    """Return one element of a matrix dimension value.

    Args:
        value: Matrix dimension value: a list, a JSON list string or a
            scalar.
        element: One-based element index.

    Returns:
        The selected element, or an empty string when the value holds too
        few elements.

    """
    items = _dimension_items(value)
    if element > len(items):
        return ""
    return items[element - 1]


def _dimension_items(value: Any) -> List[Any]:
    """Return a matrix dimension value as a list of elements.

    A missing value has no elements, a list or JSON list string yields its
    elements, and any other value is a single element.

    Args:
        value: Matrix dimension value.

    Returns:
        Elements of the value.

    """
    if value is None or value == "":
        return []
    parsed = _parsed_sequence(value)
    return parsed if parsed is not None else [value]


def _parsed_sequence(value: Any) -> Optional[List[Any]]:
    """Return the elements of a list or list-like string.

    Args:
        value: Matrix dimension value.

    Returns:
        The elements when the value is a list or tuple, or a string of a
        JSON list; otherwise None.

    """
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str) and value.strip().startswith("["):
        return _parsed_json_list(value)
    return None


def _parsed_json_list(value: str) -> Optional[List[Any]]:
    """Return the elements of a JSON list string.

    Args:
        value: Text that starts like a JSON list.

    Returns:
        The parsed list, or None when the text is not a JSON list.

    """
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, list) else None


def _argmax_winner(
    argmax: Argmax,
    source: Optional[int],
    field: str,
    where: Optional[str] = None,
) -> Optional[Tuple[float, Dict[str, Any]]]:
    """Return the entry holding a field's maximum value.

    Args:
        argmax: Winning entry per source, field and predicate.
        source: One-based source index, or None for every input cache.
        field: Metric field name.
        where: Entry predicate, or None for entries that carry no
            predicate.

    Returns:
        The winning value and its matrix values, or None when the field
        has no numeric value.

    """
    if source is not None:
        return argmax.get((source, field, where))
    winners = [
        winner
        for (_, name, clause), winner in argmax.items()
        if name == field and clause == where
    ]
    return max(winners, key=lambda item: item[0]) if winners else None


def _stat_value(stat: str, values: List[Any]) -> Any:
    """Compute a single summary statistic.

    Args:
        stat: Statistic name ('mean', 'sd', 'count', 'min', 'max',
            'median' or 'sum').
        values: Collected values for the field.

    Returns:
        Computed statistic, or an empty string when unavailable.

    """
    if stat == "count":
        return len(_numeric_values(values))
    numbers = _numeric_values(values)
    if not numbers:
        return ""
    if stat == "mean":
        return statistics.mean(numbers)
    if stat == "sum":
        return sum(numbers)
    if stat == "min":
        return min(numbers)
    if stat == "max":
        return max(numbers)
    if stat == "median":
        return statistics.median(numbers)
    if len(numbers) >= 2:
        return statistics.stdev(numbers)
    return ""
