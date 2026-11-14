"""Parsing and validating summarise action parameters."""

from typing import Any, Dict, List

from .columns import (
    ColumnSpec,
    _normalise_list,
    _normalise_optional_list,
    _parse_column_specs,
    _unique_fields,
)

__all__ = [
    "_input_files",
    "_require_tabular_output",
    "_summarise_request",
    "_validate_columns",
    "_validate_formats",
]

# Output extensions accepted as a table
_TABLE_EXTENSIONS = (".csv", ".tex", ".md", ".markdown")


def _require_tabular_output(parameters: Dict[str, Any]) -> None:
    """Require a CSV, LaTeX or Markdown output path.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If no output path is given, or it is not a .csv, .tex
            or .md file.

    """
    output_path = parameters.get("output")
    if output_path is None:
        raise ValueError(
            "summarise requires 'output' parameter with a .csv, .tex or "
            ".md file path."
        )
    if not str(output_path).lower().endswith(_TABLE_EXTENSIONS):
        raise ValueError(
            "summarise output must be a .csv, .tex or .md file. "
            f"Got: {output_path}"
        )


def _validate_columns(parameters: Dict[str, Any]) -> None:
    """Validate the metric, headers, format and footer parameters.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If a metric, format or footer entry is invalid.

    """
    specs = _parse_column_specs(_metric_specs(parameters))
    _require_sources(specs, _input_files(parameters))
    _normalise_list(parameters.get("headers"))
    _normalise_list(parameters.get("footer"))
    _validate_formats(parameters.get("format"))


def _validate_formats(value: Any) -> None:
    """Validate declared format specifications, allowing hidden columns.

    A null entry is valid and hides its column from the presentation
    output; every other entry must be a Python format specification. At
    least one column must remain visible.

    Args:
        value: Declared format specifications, or None.

    Raises:
        ValueError: If a non-null format specification is invalid, or every
            entry is null.

    """
    formats = _normalise_optional_list(value)
    for format_spec in formats:
        if format_spec is not None:
            _require_format_spec(format_spec)
    if formats and all(format_spec is None for format_spec in formats):
        raise ValueError("'format' must leave at least one visible column")


def _require_sources(
    specs: List[ColumnSpec],
    input_files: List[str],
) -> None:
    """Require every source index to name a declared input file.

    Args:
        specs: Parsed column specifications.
        input_files: Input cache paths, in declared order.

    Raises:
        ValueError: If a specification names an input that was not given.

    """
    available = len(input_files)
    for spec in specs:
        source = spec.source
        if source is None or source <= available:
            continue
        raise ValueError(
            f"Invalid metric spec '{spec.text}': names input file "
            f"{source}, but {available} input file(s) were given"
        )


def _require_format_spec(format_spec: str) -> None:
    """Require a Python format specification.

    Args:
        format_spec: Format specification to validate.

    Raises:
        ValueError: If neither a number nor a text value can be formatted
            with it.

    """
    probes = (0.0, 0, "")
    if any(_is_format_spec(format_spec, value) for value in probes):
        return
    raise ValueError(
        f"Invalid format spec '{format_spec}': use a Python format "
        "specification such as '.3f', '+.3f' or '>3d'"
    )


def _is_format_spec(format_spec: str, value: Any) -> bool:
    """Return True when a format specification accepts a value.

    Args:
        format_spec: Format specification to try.
        value: Value to format with it.

    Returns:
        True when the value formats without error.

    """
    try:
        format(value, format_spec)
    except (TypeError, ValueError):
        return False
    return True


def _summarise_request(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Build the summarisation request from action parameters.

    Args:
        parameters: Action parameter values.

    Returns:
        Request holding the parsed columns, filter, output path, inputs
        and presentation parameters.

    Raises:
        ValueError: If the metric parameter is not a non-empty string or
            list, or a specification is invalid.

    """
    metric_specs = _metric_specs(parameters)
    specs = _parse_column_specs(metric_specs)
    return {
        "metric_specs": metric_specs,
        "parsed_metrics": specs,
        "unique_fields": _unique_fields(specs),
        "argmax_fields": [
            spec.field or "" for spec in specs if spec.stat == "argmax"
        ],
        "qualified_sources": {
            spec.source for spec in specs if spec.source is not None
        },
        "headers": _normalise_list(parameters.get("headers")),
        "format": _normalise_optional_list(parameters.get("format")),
        "footer": _normalise_list(parameters.get("footer")),
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


def _metric_specs(parameters: Dict[str, Any]) -> List[str]:
    """Return the metric specifications as a non-empty list.

    Args:
        parameters: Action parameter values.

    Returns:
        Metric specifications in column order.

    Raises:
        ValueError: If the parameter is not a non-empty string or list.

    """
    metric_specs = parameters.get("metric", [])
    if isinstance(metric_specs, str):
        metric_specs = [metric_specs]
    if not isinstance(metric_specs, list):
        raise ValueError(
            f"'metric' must be a string or list, got "
            f"{type(metric_specs).__name__}"
        )
    if not metric_specs:
        raise ValueError(
            "At least one metric specification required "
            "(e.g., ['f1.mean', 'shd.sd'])"
        )
    return metric_specs
