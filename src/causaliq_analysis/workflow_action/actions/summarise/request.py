"""Parsing and validating summarise action parameters."""

from typing import Any

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

# Output extension accepted as a metrics workflow cache
_CACHE_EXTENSION = ".db"

# Presentation parameters that do not apply to a metrics cache
_CACHE_UNSUPPORTED = (
    "headers",
    "format",
    "footer",
    "significance",
    "significance_detail",
    "caption",
)

# Number of columns in a standard significance table
_SIGNIFICANCE_COLUMNS = 4

# Number of columns in a detailed paired-comparison table
_DETAIL_COLUMNS = 6


def _require_tabular_output(parameters: dict[str, Any]) -> None:
    """Require a table or metrics-cache output path.

    A missing path is valid at execution time because the workflow
    executor removes ``output`` before invoking an action that writes to
    a cache. A ``.db`` path selects metrics-cache output, which does not
    support the table presentation parameters.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If the output is not a table or cache path, or a
            cache output declares presentation parameters.

    """
    output_path = parameters.get("output")
    if output_path is None:
        return
    lowered = str(output_path).lower()
    if lowered.endswith(_CACHE_EXTENSION):
        _require_cache_options(parameters)
        return
    if not lowered.endswith(_TABLE_EXTENSIONS):
        raise ValueError(
            "summarise output must be a .csv, .tex, .md or .db file. "
            f"Got: {output_path}"
        )


def _require_cache_options(parameters: dict[str, Any]) -> None:
    """Reject table presentation options on a metrics-cache output.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If a table-only option is present.

    """
    invalid = [name for name in _CACHE_UNSUPPORTED if parameters.get(name)]
    if invalid:
        raise ValueError(
            "summarise metrics-cache output does not support: "
            + ", ".join(sorted(invalid))
        )


def _validate_columns(parameters: dict[str, Any]) -> None:
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
    specs: list[ColumnSpec],
    input_files: list[str],
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


def _validate_significance(parameters: dict[str, Any]) -> None:
    """Validate the significance parameter and its presentation columns.

    Args:
        parameters: Action parameter values.

    Raises:
        ValueError: If a test specification, alias, header, format or
            caption is invalid, or the significance table cannot be
            rendered.
    """
    raw = _normalise_list(parameters.get("significance"))
    detail = _significance_detail(parameters)
    if detail and not raw:
        raise ValueError("'significance_detail' requires 'significance' tests")
    if not raw:
        return
    specs = _parse_column_specs(_metric_specs(parameters))
    aliases = {spec.alias for spec in specs if spec.alias}
    _parse_significance_specs(raw, aliases)
    _require_significance_input(parameters)
    _validate_significance_format(parameters.get("format"), detail)
    _validate_significance_headers(
        parameters.get("headers"),
        parameters.get("format"),
        detail,
    )
    _require_no_significance_footer(parameters.get("footer"))
    _validate_caption(parameters.get("caption"))


def _significance_detail(parameters: dict[str, Any]) -> bool:
    """Return the validated detailed-comparison flag.

    Args:
        parameters: Action parameter values.

    Returns:
        True when the detailed paired-comparison columns are requested.

    Raises:
        ValueError: If the flag is not a boolean.
    """
    value = parameters.get("significance_detail", False)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError(
            f"'significance_detail' must be a boolean, got "
            f"{type(value).__name__}"
        )
    return value


def _require_significance_input(parameters: dict[str, Any]) -> None:
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


def _validate_significance_format(value: Any, detail: bool = False) -> None:
    """Validate the format specifications of a significance table.

    Args:
        value: Declared format specifications, or None.
        detail: Whether the detailed comparison columns are requested.

    Raises:
        ValueError: If the format count does not match the significance
            columns, or a specification is invalid.
    """
    count = _significance_column_count(detail)
    formats = _normalise_optional_list(value)
    if formats and len(formats) != count:
        raise ValueError(
            f"'format' must have {count} entries "
            f"(one per significance column), got {len(formats)}"
        )
    _validate_formats(value)


def _validate_significance_headers(
    headers: Any,
    formats: Any,
    detail: bool = False,
) -> None:
    """Validate the headers of a significance table.

    Args:
        headers: Declared column headers, or None.
        formats: Declared format specifications, or None.
        detail: Whether the detailed comparison columns are requested.

    Raises:
        ValueError: If the header count does not match the visible
            significance columns.
    """
    values = _normalise_list(headers)
    if not values:
        return
    visible = _visible_column_count(_normalise_optional_list(formats), detail)
    if len(values) != visible:
        raise ValueError(
            f"'headers' must have {visible} entries (one per visible "
            f"significance column), got {len(values)}"
        )


def _significance_column_count(detail: bool) -> int:
    """Return the number of columns in a significance table.

    Args:
        detail: Whether the detailed comparison columns are requested.

    Returns:
        The column count.
    """
    return _DETAIL_COLUMNS if detail else _SIGNIFICANCE_COLUMNS


def _visible_column_count(
    formats: list[str | None],
    detail: bool = False,
) -> int:
    """Return the number of visible significance columns.

    Args:
        formats: Declared format specifications, empty when unformatted.
        detail: Whether the detailed comparison columns are requested.

    Returns:
        Number of columns that are not hidden.
    """
    if not formats:
        return _significance_column_count(detail)
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
    parameters: dict[str, Any],
    specs: list[ColumnSpec],
) -> list[SignificanceSpec]:
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


def _summarise_request(parameters: dict[str, Any]) -> dict[str, Any]:
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
        "significance_detail": _significance_detail(parameters),
        "caption": parameters.get("caption"),
        "unique_fields": _unique_fields(specs),
        "where_clauses": sorted({spec.where for spec in specs if spec.where}),
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
        "is_cache_output": _is_cache_output(parameters.get("output")),
        "input_files": _input_files(parameters),
        "aggregation_entries": parameters.get("_aggregation_entries"),
        "is_aggregation": parameters.get("_aggregation_entries") is not None,
    }


def _is_cache_output(output: Any) -> bool:
    """Return True when the output path names a metrics workflow cache.

    Args:
        output: Output path, if any.

    Returns:
        True for a ``.db`` output path.

    """
    return output is not None and str(output).lower().endswith(
        _CACHE_EXTENSION
    )


def _input_files(parameters: dict[str, Any]) -> list[str]:
    """Return the input cache paths as a list.

    Args:
        parameters: Action parameter values.

    Returns:
        Input paths, empty when none are provided.

    """
    input_raw = parameters.get("input", []) or []
    return [input_raw] if isinstance(input_raw, str) else list(input_raw)


def _metric_specs(parameters: dict[str, Any]) -> list[str]:
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
