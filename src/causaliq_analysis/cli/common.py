"""Shared helpers for the causaliq-analysis command-line interface.

These helpers are used by more than one command module: metadata
flattening and nested-value lookup support the ``summarise`` command,
and the summary table formats its terminal output.
"""

from typing import Any, Dict

import click

__all__ = [
    "_flatten_metadata",
    "_get_nested_value",
    "_print_summary_table",
]


def _flatten_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten nested metadata for field access.

    Flattens provider/action structure to simple field names.
    E.g., {'causaliq-analysis': {'eval': {'f1': 0.9}}} becomes {'f1': 0.9}.

    Args:
        metadata: Nested metadata keyed by provider then action.

    Returns:
        Flat dictionary with simple and qualified field names.
    """
    flat: Dict[str, Any] = {}
    for provider_name, provider_data in metadata.items():
        _flatten_provider(provider_name, provider_data, flat)
    return flat


def _flatten_provider(
    provider_name: str,
    provider_data: Any,
    flat: Dict[str, Any],
) -> None:
    """Flatten one provider's metadata section into a flat dictionary.

    Args:
        provider_name: Provider key in the nested metadata.
        provider_data: Provider metadata section.
        flat: Flat dictionary, updated in place.
    """
    if not isinstance(provider_data, dict):
        flat[provider_name] = provider_data
        return

    for action_name, action_data in provider_data.items():
        _flatten_action(provider_name, action_name, action_data, flat)


def _flatten_action(
    provider_name: str,
    action_name: str,
    action_data: Any,
    flat: Dict[str, Any],
) -> None:
    """Flatten one action's metadata section into a flat dictionary.

    Args:
        provider_name: Provider key in the nested metadata.
        action_name: Action key in the nested metadata.
        action_data: Action metadata section.
        flat: Flat dictionary, updated in place.
    """
    qual_key = f"{provider_name}.{action_name}"
    if not isinstance(action_data, dict):
        flat[qual_key] = action_data
        return

    for key, value in action_data.items():
        _flatten_field(qual_key, key, value, flat)


def _flatten_field(
    qual_key: str,
    key: str,
    value: Any,
    flat: Dict[str, Any],
) -> None:
    """Store a single metadata field under simple and qualified keys.

    Args:
        qual_key: Qualified provider.action prefix.
        key: Field name within the action metadata.
        value: Field value.
        flat: Flat dictionary, updated in place.
    """
    if key not in flat:
        flat[key] = value
    flat[f"{qual_key}.{key}"] = value


def _get_nested_value(data: Dict[str, Any], field: str) -> Any:
    """Get value from dict using dotted path notation.

    Args:
        data: Dictionary to search.
        field: Field name, optionally with dots for nested access.

    Returns:
        Value if found, None otherwise.
    """
    # First try direct key lookup
    if field in data:
        return data[field]

    # Try dotted path traversal
    parts = field.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _format_summary_value(value: Any) -> str:
    """Format a single summary value for terminal display.

    Args:
        value: Computed metric value.

    Returns:
        Display string for the value.
    """
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _print_summary_table(results: Dict[str, Any]) -> None:
    """Print summary results as a formatted table to terminal.

    Args:
        results: Dictionary of metric names to computed values.
    """
    if not results:
        click.echo("No results to display.")
        return

    headers = list(results.keys())
    values = [_format_summary_value(v) for v in results.values()]

    # Calculate column widths
    widths = [max(len(h), len(v)) for h, v in zip(headers, values)]

    # Build format string
    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    value_line = "  ".join(v.ljust(w) for v, w in zip(values, widths))
    separator = "  ".join("-" * w for w in widths)

    click.echo(header_line)
    click.echo(separator)
    click.echo(value_line)
