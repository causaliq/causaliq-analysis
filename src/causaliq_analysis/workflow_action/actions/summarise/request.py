"""Parsing and validating summarise action parameters."""

from typing import Any, Dict, List, Tuple

from causaliq_analysis.validation import SUPPORTED_STATS
from causaliq_analysis.workflow_action.types import ActionExecutionError

__all__ = [
    "_input_files",
    "_parse_metric_specs",
    "_require_csv_output",
    "_summarise_request",
]


def _require_csv_output(parameters: Dict[str, Any]) -> None:
    """Require a CSV output path.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If no output path is given, or it is not a CSV file.

    """
    output_path = parameters.get("output")
    if output_path is None:
        raise ValueError(
            "summarise requires 'output' parameter with .csv file path."
        )
    if not str(output_path).lower().endswith(".csv"):
        raise ValueError(
            "summarise output must be a CSV file (.csv). "
            f"Got: {output_path}"
        )


def _summarise_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the summarisation request from action parameters.

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding metric specs, filter, output path and inputs.

    """
    metric_specs = parameters.get("metric", [])
    if isinstance(metric_specs, str):
        metric_specs = [metric_specs]
    if not metric_specs:  # pragma: no cover
        raise ActionExecutionError(
            "summarise requires 'metric' parameter with at least one "
            "metric specification (e.g., ['f1.mean', 'shd.sd'])"
        )
    parsed_metrics = _parse_metric_specs(metric_specs)
    return {
        "metric_specs": metric_specs,
        "parsed_metrics": parsed_metrics,
        "unique_fields": list(dict.fromkeys(f for f, _ in parsed_metrics)),
        "filter": parameters.get("filter"),
        "output": parameters.get("output"),
        "input_files": _input_files(parameters),
        "aggregation_entries": parameters.get("_aggregation_entries"),
        "is_aggregation": parameters.get("_aggregation_entries") is not None,
    }


def _input_files(parameters: Dict[str, Any]) -> List[str]:
    """Return the input cache paths as a list.

    Args:
        parameters: Action parameter values.

    Returns:
        Input paths, empty when none are provided.

    """
    input_raw = parameters.get("input", []) or []
    return [input_raw] if isinstance(input_raw, str) else list(input_raw)


def _parse_metric_specs(metric_specs: List[str]) -> List[Tuple[str, str]]:
    """Parse '<field>.<stat>' metric specifications.

    Args:
        metric_specs: Metric specifications to parse.

    Returns:
        List of (field, stat) tuples.

    Raises:
        ActionExecutionError: If a specification is invalid.

    """
    parsed: List[Tuple[str, str]] = []
    for spec in metric_specs:
        parsed.append(_parse_one_spec(spec))
    return parsed


def _parse_one_spec(spec: str) -> Tuple[str, str]:
    """Parse a single metric specification.

    Args:
        spec: Metric specification (e.g. 'f1.mean').

    Returns:
        Tuple of (field, stat).

    Raises:
        ActionExecutionError: If the specification is invalid.

    """
    if "," in spec:  # pragma: no cover
        raise ActionExecutionError(
            f"Invalid metric spec '{spec}': contains comma. "
            "Use YAML list syntax: metric: [f1.mean, shd.sd]"
        )
    if "." not in spec:  # pragma: no cover
        raise ActionExecutionError(
            f"Invalid metric spec '{spec}': must be <field>.<stat>"
        )
    field, stat = spec.rsplit(".", 1)
    if stat not in SUPPORTED_STATS:  # pragma: no cover
        raise ActionExecutionError(
            f"Unknown statistic '{stat}' in '{spec}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_STATS))}"
        )
    return field, stat
