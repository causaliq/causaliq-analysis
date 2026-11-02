"""Summary statistics for summarise metric specifications."""

import statistics
from typing import Any, Dict, List, Tuple

__all__ = ["_compute_stats"]


def _compute_stats(
    parsed_metrics: List[Tuple[str, str]],
    values: Dict[str, List[float]],
) -> Dict[str, Any]:
    """Compute the summary statistics for each metric specification.

    Args:
        parsed_metrics: Parsed (field, stat) specifications.
        values: Collected values per field.

    Returns:
        Mapping of '<field>.<stat>' column names to computed values.

    """
    results: Dict[str, Any] = {}
    for field, stat in parsed_metrics:
        results[f"{field}.{stat}"] = _stat_value(stat, values[field])
    return results


def _stat_value(stat: str, values: List[float]) -> Any:
    """Compute a single summary statistic.

    Args:
        stat: Statistic name ('mean', 'sd' or 'count').
        values: Collected values for the field.

    Returns:
        Computed statistic, or an empty string when unavailable.

    """
    if stat == "count":
        return len(values)
    if stat == "mean":
        return statistics.mean(values) if values else ""
    if len(values) >= 2:
        return statistics.stdev(values)
    return ""
