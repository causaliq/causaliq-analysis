"""Summary statistics for summarise metric specifications."""

import statistics
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["_compute_stats"]


def _compute_stats(
    parsed_metrics: List[Tuple[str, str, Optional[str]]],
    values: Dict[str, List[float]],
    argmax: Dict[str, Tuple[float, Dict[str, Any]]],
) -> Dict[str, Any]:
    """Compute the summary statistics for each metric specification.

    Args:
        parsed_metrics: Parsed (field, stat, dimension) specifications.
        values: Collected values per field.
        argmax: Winning entry per field: its maximum value and the entry's
            matrix values.

    Returns:
        Mapping of column names to computed values.

    """
    results: Dict[str, Any] = {}
    for field, stat, dimension in parsed_metrics:
        if stat == "argmax":
            column = f"{field}.argmax.{dimension}"
            results[column] = _argmax_dimension(argmax, field, dimension)
            continue
        results[f"{field}.{stat}"] = _stat_value(stat, values[field])
    return results


def _argmax_dimension(
    argmax: Dict[str, Tuple[float, Dict[str, Any]]],
    field: str,
    dimension: Optional[str],
) -> Any:
    """Return the dimension value of the entry holding a field's maximum.

    Args:
        argmax: Winning entry per field.
        field: Field whose maximum was tracked.
        dimension: Matrix dimension to report.

    Returns:
        The winning entry's matrix value for the dimension, or an empty
        string when the field has no numeric value in the group.

    """
    winner = argmax.get(field)
    if winner is None or dimension is None:
        return ""
    return winner[1].get(dimension, "")


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
