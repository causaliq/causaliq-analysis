"""
Common validation utilities for causaliq-analysis.

This module contains shared validation functions used across CLI and
workflow_action modules to avoid code duplication.
"""

from typing import Any, FrozenSet, List, Optional, Tuple, TypeVar, Union

import click

T = TypeVar("T")

# Supported summary statistics for metric specifications
SUPPORTED_STATS: FrozenSet[str] = frozenset({"mean", "sd", "count"})


def single_value_callback(
    ctx: click.Context,
    param: click.Option,
    value: Tuple[T, ...],
) -> Optional[T]:
    """Click callback to enforce single-value options.

    Use with ``multiple=True`` options to raise an error if the option
    is specified more than once, preventing silent overwrites.

    Args:
        ctx: Click context.
        param: Click parameter.
        value: Tuple of values (from multiple=True).

    Returns:
        Single value, or None if not provided.

    Raises:
        click.BadParameter: If option specified multiple times.

    Example:
        >>> @click.option("--network", "-n", multiple=True,
        ...               callback=single_value_callback)
        ... def cmd(network): ...
    """
    if not value:
        return None
    if len(value) > 1:
        raise click.BadParameter(
            f"specified multiple times: {', '.join(str(v) for v in value)}. "
            f"Only one value is allowed."
        )
    return value[0]


def parse_sample_size(size_input: Union[str, int]) -> int:
    """Parse sample size from various input formats.

    Args:
        size_input: Sample size as string (e.g., '10k', '100k') or integer

    Returns:
        int: Parsed sample size

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_sample_size("10k")
        10000
        >>> parse_sample_size("1.5k")
        1500
        >>> parse_sample_size("2m")
        2000000
        >>> parse_sample_size(1000)
        1000
    """
    if isinstance(size_input, int):
        return size_input
    if not isinstance(size_input, str):
        raise ValueError(f"Invalid sample size type: {type(size_input)}")
    size_str = str(size_input).strip().lower()
    return _parse_size_string(size_str)


def _parse_size_string(size_str: str) -> int:
    """Parse a sample-size string with an optional k/m suffix.

    Args:
        size_str: Normalised (lowercased, stripped) size string.

    Returns:
        The parsed sample size.

    Raises:
        ValueError: If the format is invalid.
    """
    if size_str.endswith("k"):
        return _parse_scaled_size(size_str, 1000)
    if size_str.endswith("m"):
        return _parse_scaled_size(size_str, 1000000)
    return _parse_plain_size(size_str)


def _parse_scaled_size(size_str: str, multiplier: int) -> int:
    """Return a suffixed size string scaled by a multiplier.

    Args:
        size_str: Normalised size string with a k/m suffix.
        multiplier: Scale factor (1000 or 1000000).

    Returns:
        The parsed sample size.

    Raises:
        ValueError: If the value is not numeric.
    """
    try:
        return int(float(size_str[:-1]) * multiplier)
    except ValueError:
        raise ValueError(f"Invalid sample size format: {size_str}")


def _parse_plain_size(size_str: str) -> int:
    """Return an integer parsed from a plain size string.

    Args:
        size_str: Normalised size string without a suffix.

    Returns:
        The parsed sample size.

    Raises:
        ValueError: If the value is not an integer.
    """
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid sample size format: {size_str}")


def parse_seed_cli(seed_str: str) -> Tuple[int, ...]:
    """Parse seed string to tuple of integers (CLI format).

    CLI format supports single values and hyphen-delimited ranges.

    Args:
        seed_str: Seed string from CLI

    Returns:
        Tuple of seed integers

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_seed_cli("")
        ()
        >>> parse_seed_cli("5")
        (5,)
        >>> parse_seed_cli("0-24")
        (0, 1, 2, ..., 24)
    """
    if not seed_str or seed_str.strip() == "":
        return ()
    seed_str = seed_str.strip()
    _reject_comma(seed_str, "use hyphen for range (e.g., '0-24') not comma")
    try:
        return _parse_seed_expression(seed_str)
    except ValueError as error:
        if "invalid literal" in str(error):
            raise ValueError(f"Invalid seed format: {seed_str}")
        raise


def _reject_comma(seed_str: str, hint: str) -> None:
    """Raise when a seed string contains a comma.

    Args:
        seed_str: Seed string to check.
        hint: Guidance appended to the error message.

    Raises:
        ValueError: If the seed string contains a comma.
    """
    if "," in seed_str:
        raise ValueError(f"Invalid seed format '{seed_str}': {hint}")


def _parse_seed_expression(seed_str: str) -> Tuple[int, ...]:
    """Parse a seed string into a tuple of ints, supporting ranges.

    Args:
        seed_str: Seed string such as "5" or "0-24".

    Returns:
        Tuple of seed integers.

    Raises:
        ValueError: If the format is invalid.
    """
    if "-" in seed_str:
        return _parse_seed_range(seed_str)
    return (int(seed_str),)


def _parse_seed_range(seed_str: str) -> Tuple[int, ...]:
    """Parse a start-end seed range into an inclusive tuple.

    Args:
        seed_str: Range string such as "0-24".

    Returns:
        Tuple covering the inclusive range.

    Raises:
        ValueError: If the range is malformed or empty.
    """
    parts = seed_str.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid range format '{seed_str}': use 'start-end'")
    start, end = int(parts[0].strip()), int(parts[1].strip())
    if start > end:
        raise ValueError(f"Invalid range: start ({start}) > end ({end})")
    return tuple(range(start, end + 1))


def parse_seed_workflow(seed_input: Any) -> Tuple[int, ...]:
    """Parse seed from various input formats (workflow format).

    Workflow format supports:
    - Single integer: 5 → (5,)
    - YAML list: [0, 1, 2] → (0, 1, 2)
    - Range string: "0-24" → (0, 1, ..., 24)

    Args:
        seed_input: Seed as int, list, tuple, or range string

    Returns:
        Tuple of seed integers

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_seed_workflow(5)
        (5,)
        >>> parse_seed_workflow([0, 1, 2])
        (0, 1, 2)
        >>> parse_seed_workflow("0-24")
        (0, 1, 2, ..., 24)
    """
    if seed_input is None:
        return ()
    if isinstance(seed_input, tuple):
        return seed_input
    if isinstance(seed_input, list):
        return tuple(seed_input)
    if isinstance(seed_input, int):
        return (seed_input,)
    if isinstance(seed_input, str):
        return _parse_seed_string(seed_input)
    raise ValueError(f"Invalid seed type: {type(seed_input)}")


def _parse_seed_string(seed_str: str) -> Tuple[int, ...]:
    """Parse a workflow seed string into a tuple of ints.

    Args:
        seed_str: Seed string such as "5" or "0-24".

    Returns:
        Tuple of seed integers.

    Raises:
        ValueError: If the format is invalid.
    """
    seed_str = seed_str.strip()
    if not seed_str:
        return ()
    _reject_comma(
        seed_str,
        "contains comma. Use YAML list syntax: seed: [0, 1, 2] "
        "or range: seed: 0-24",
    )
    try:
        return _parse_seed_expression(seed_str)
    except ValueError as error:
        if "invalid literal" in str(error):
            raise ValueError(f"Invalid seed format: {seed_str}")
        raise


def validate_filter_expression(filter_expr: Optional[str]) -> None:
    """Validate filter expression syntax.

    Checks that the filter expression has valid Python syntax without
    evaluating it against actual data. This catches syntax errors early.

    Args:
        filter_expr: Filter expression string, or None (no-op).

    Raises:
        ValueError: If filter syntax is invalid.

    Examples:
        >>> validate_filter_expression("network == 'asia'")  # Valid
        >>> validate_filter_expression("x > 5 and y < 10")   # Valid
        >>> validate_filter_expression("x ==")  # Raises ValueError
    """
    if filter_expr is None or filter_expr.strip() == "":
        return

    try:
        from causaliq_core.utils import FilterSyntaxError, validate_filter

        validate_filter(filter_expr)
    except FilterSyntaxError as e:
        raise ValueError(f"Invalid filter expression: {e}")


def validate_metric_specs(
    metric_specs: Union[str, List[str]],
    supported_stats: Optional[FrozenSet[str]] = None,
) -> List[Tuple[str, str]]:
    """Validate and parse metric specifications.

    Each metric spec must be in the format '<field>.<stat>' where stat
    is one of the supported statistics (mean, sd, count).

    Args:
        metric_specs: List of metric specifications (e.g., ['f1.mean']).
        supported_stats: Set of valid stat names. Defaults to SUPPORTED_STATS.

    Returns:
        List of (field, stat) tuples.

    Raises:
        ValueError: If specs are empty, not a list, or any spec is invalid.

    Examples:
        >>> validate_metric_specs(['f1.mean', 'shd.sd'])
        [('f1', 'mean'), ('shd', 'sd')]
        >>> validate_metric_specs(['invalid'])  # Raises ValueError
    """
    if supported_stats is None:
        supported_stats = SUPPORTED_STATS
    specs = _normalise_metric_specs(metric_specs)
    return [_parse_metric_spec(spec, supported_stats) for spec in specs]


def _normalise_metric_specs(metric_specs: Union[str, List[str]]) -> List[str]:
    """Normalise metric specifications to a non-empty list of strings.

    Args:
        metric_specs: A single spec string or a list of spec strings.

    Returns:
        List of metric specification strings.

    Raises:
        ValueError: If the value is not a string/list or the list is empty.
    """
    if isinstance(metric_specs, str):
        return [metric_specs]
    if not isinstance(metric_specs, list):
        raise ValueError(
            f"'metric' must be a string or list, "
            f"got {type(metric_specs).__name__}"
        )
    if not metric_specs:
        raise ValueError(
            "At least one metric specification required "
            "(e.g., ['f1.mean', 'shd.sd'])"
        )
    return metric_specs


def _parse_metric_spec(
    spec: str,
    supported_stats: FrozenSet[str],
) -> Tuple[str, str]:
    """Validate and parse one '<field>.<stat>' metric specification.

    Args:
        spec: Metric specification string.
        supported_stats: Set of valid statistic names.

    Returns:
        Tuple of (field, stat).

    Raises:
        ValueError: If the specification is invalid.
    """
    if "," in spec:
        raise ValueError(
            f"Invalid metric spec '{spec}': contains comma. "
            "Use YAML list syntax instead: metric: [f1.mean, shd.sd]"
        )
    if "." not in spec:
        raise ValueError(
            f"Invalid metric spec '{spec}': must be <field>.<stat>"
        )
    field, stat = spec.rsplit(".", 1)
    if stat not in supported_stats:
        raise ValueError(
            f"Unknown statistic '{stat}' in '{spec}'. "
            f"Supported: {', '.join(sorted(supported_stats))}"
        )
    return field, stat


def require_param(
    parameters: dict,
    param_name: str,
    action_name: str,
) -> Any:
    """Require a parameter to be present.

    Args:
        parameters: Parameter dictionary.
        param_name: Name of required parameter.
        action_name: Action name for error message.

    Returns:
        The parameter value.

    Raises:
        ValueError: If parameter is missing.
    """
    if param_name not in parameters or parameters[param_name] is None:
        raise ValueError(f"'{action_name}' requires '{param_name}' parameter")
    return parameters[param_name]


def require_one_of(
    parameters: dict,
    param_names: List[str],
    action_name: str,
) -> str:
    """Require at least one of the specified parameters.

    Args:
        parameters: Parameter dictionary.
        param_names: List of parameter names (at least one required).
        action_name: Action name for error message.

    Returns:
        Name of the first present parameter.

    Raises:
        ValueError: If none of the parameters are present.
    """
    for name in param_names:
        if name in parameters and parameters[name] is not None:
            return name

    names_str = "', '".join(param_names)
    raise ValueError(f"'{action_name}' requires one of: '{names_str}'")
