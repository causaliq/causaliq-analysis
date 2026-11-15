"""Parsing and validating summarise action parameters."""

from typing import Any, Dict, List, Optional

from .columns import (
    ColumnSpec,
    _normalise_list,
    _normalise_optional_list,
    _parse_column_specs,
    _unique_fields,
)
from .significance import SignificanceSpec
from .significance_specs import _parse_significance_specs

__all__ = [
    "_input_files",
    "_require_tabular_output",
    "_summarise_request",
    "_validate_columns",
    "_validate_formats",
    "_validate_significance",
]

# Output extensions accepted as a table
_TABLE_EXTENSIONS = (".csv", ".tex", ".md", ".markdown")

# Number of columns in a significance table
_SIGNIFICANCE_COLUMNS = 4


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


def _validate_significance(parameters: Dict[str, Any]) -> None:
    """Validate the significance parameter and its presentation columns.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If a test specification, alias, header, format or
            caption is invalid, or the significance table cannot be
            rendered.
    """
    raw = _normalise_list(parameters.get("significance"))
    if not raw:
        return
    specs = _parse_column_specs(_metric_specs(parameters))
    aliases = {spec.alias for spec in specs if spec.alias}
    _parse_significance_specs(raw, aliases)
    _require_significance_input(parameters)
    _validate_significance_format(parameters.get("format"))
    _validate_significance_headers(
        parameters.get("headers"),
        parameters.get("format"),
    )
    _require_no_significance_footer(parameters.get("footer"))
    _validate_caption(parameters.get("caption"))


def _require_significance_input(parameters: Dict[str, Any]) -> None:
    """Require input caches for a significance table.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If no input cache was given.
    """
    if not _input_files(parameters):
        raise ValueError(
            "significance requires 'input' cache files and a workflow "
            "matrix"
        )


def _validate_significance_format(value: Any) -> None:
    """Validate the format specifications of a significance table.

    Args:
        value: Declared format specifications, or None.

    Raises:
        ValueError: If the format count does not match the four
            significance columns, or a specification is invalid.
    """
    formats = _normalise_optional_list(value)
    if formats and len(formats) != _SIGNIFICANCE_COLUMNS:
        raise ValueError(
            f"'format' must have {_SIGNIFICANCE_COLUMNS} entries "
            f"(one per significance column), got {len(formats)}"
        )
    _validate_formats(value)


def _validate_significance_headers(
    headers: Any,
    formats: Any,
) -> None:
    """Validate the headers of a significance table.

    Args:
        headers: Declared column headers, or None.
        formats: Declared format specifications, or None.

    Raises:
        ValueError: If the header count does not match the visible
            significance columns.
    """
    values = _normalise_list(headers)
    if not values:
        return
    visible = _visible_column_count(_normalise_optional_list(formats))
    if len(values) != visible:
        raise ValueError(
            f"'headers' must have {visible} entries (one per visible "
            f"significance column), got {len(values)}"
        )


def _visible_column_count(formats: List[Optional[str]]) -> int:
    """Return the number of visible significance columns.

    Args:
        formats: Declared format specifications, empty when unformatted.

    Returns:
        Number of columns that are not hidden.
    """
    if not formats:
        return _SIGNIFICANCE_COLUMNS
    return sum(1 for format_spec in formats if format_spec is not None)


def _require_no_significance_footer(footer: Any) -> None:
    """Reject a footer on a significance table.

    Args:
        footer: Declared footer cells, or None.

    Raises:
        ValueError: If a footer was declared.
    """
    if _normalise_list(footer):
        raise ValueError(
            "'footer' is not supported with significance tests; "
            "use 'caption' for a heading"
        )


def _validate_caption(value: Any) -> None:
    """Require the caption to be a string or absent.

    Args:
        value: Declared caption, or None.

    Raises:
        ValueError: If the caption is not a string.
    """
    if value is None or isinstance(value, str):
        return
    raise ValueError(f"'caption' must be a string, got {type(value).__name__}")


def _significance_request(
    parameters: Dict[str, Any],
    specs: List[ColumnSpec],
) -> List[SignificanceSpec]:
    """Return the parsed significance specifications.

    Args:
        parameters: Action parameter values.
        specs: Parsed metric column specifications.

    Returns:
        Parsed significance specifications, empty when absent.
    """
    raw = _normalise_list(parameters.get("significance"))
    if not raw:
        return []
    aliases = {spec.alias for spec in specs if spec.alias}
    return _parse_significance_specs(raw, aliases)


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
    significance = _significance_request(parameters, specs)
    return {
        "metric_specs": metric_specs,
        "parsed_metrics": specs,
        "significance": significance,
        "caption": parameters.get("caption"),
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
